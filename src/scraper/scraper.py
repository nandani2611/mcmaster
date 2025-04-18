import logging
import os
import time
import traceback
import json

from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
import undetected_chromedriver as uc
from datetime import datetime, timezone, timedelta

from src.scraper.config import SiteConfig, ScraperConfig
from src.database.database import MongoDBClient
from src.scraper.exceptions import AccessRestrictedError

# Create logs directory if it doesn't exist
log_dir = "src/logs"
os.makedirs(log_dir, exist_ok=True)

# Generate timestamp for the log filename
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
log_filename = f"mcmaster_scraper_{timestamp}.log"

# Path to the skip list JSON file
SKIP_LIST_FILE = "src/config/skip_list.json"

# Initialize the skip list from the JSON file or create a default one
def load_skip_list():
    try:
        if os.path.exists(SKIP_LIST_FILE):
            with open(SKIP_LIST_FILE, 'r') as f:
                return json.load(f)
        else:
            # Default list of items to skip
            default_list = ['', 'Socket Head Screws', 'Rounded Head Screws', 'Hex Head Screws', 
                'Flat Head Screws', 'Tapping Screws', 'Shoulder Screws', 'Set Screws', 
                'Wood Screws', 'Thumb Screws', 'Carriage Bolts', '12-Point Screws', 
                'Captive Panel Screws', 'Drywall Screws', 'Fastener Assortments', 'Studs', 
                'Square Head Screws', 'Elevator Bolts', 'Hanger Bolts', 'T-Bolts', 
                'Plow Bolts', 'Pentagon Head Screws', 'Hold-Down Bolts', 'Jack Screws', 
                'Joint Clamps for Wood', 'Binding Barrels and Screws', 'Threaded Rods', 
                'Standoffs', 'Standoff Caps', 'Single-End Studs', 'Thread Adapters', 
                'Rivet Nuts', 'Weld Nuts', 'Anchors', 'Spring Plungers', 'Captive Pins', 
                'Screw Nails', 'Nails', 'Anchor Toggles', 'Rivets', 'Antislip Fluid', 
                'Tapping Screw Installation Tools', 'Hanger Bolt Driver Bits', 
                'Anchor Installation Tools', 'Magnets', 'Setup Studs', 'T-Slot Bolts', 
                'Drill Bushing Lock Screws']
            # Save default list to file
            with open(SKIP_LIST_FILE, 'w') as f:
                json.dump(default_list, f, indent=2)
            return default_list
    except Exception as e:
        logging.error(f"Error loading skip list: {str(e)}")
        return []

# Save updated skip list to JSON file
def save_skip_list(skip_list):
    try:
        with open(SKIP_LIST_FILE, 'w') as f:
            json.dump(skip_list, f, indent=2)
        logging.info(f"Updated skip list saved with {len(skip_list)} items")
    except Exception as e:
        logging.error(f"Error saving skip list: {str(e)}")

# Initialize the things_to_skip list
things_to_skip = load_skip_list()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(log_dir, log_filename)),
        logging.StreamHandler()
    ],
)

cred_email = os.getenv("CRED_EMAIL")
cred_pass = os.getenv("CRED_PASS")
db_name = os.getenv("DB_NAME")
collection_name = os.getenv("COLLECTION_NAME")

# Initialize MongoDB client
db_client = MongoDBClient(db_name=db_name, collection_name=collection_name)


class McMasterScraper:
    def __init__(self):
        self.base_url = SiteConfig.BASE_URL
        self.setup_driver()
        self.products = []

    def setup_driver(self):
        """Setup Chrome driver with appropriate options"""
        chrome_options = ScraperConfig.get_chrome_options()
        service = Service(ChromeDriverManager().install())
        self.driver = uc.Chrome(service=service, options=chrome_options)
        self.wait = WebDriverWait(self.driver, 60)

    def load_site(self):
        self.driver.get(self.base_url)
        time.sleep(5)  # Allow page to load completely

    def login_to_site(self):
        login_btn = self.wait.until(
            EC.visibility_of_element_located((By.ID, "LoginUsrCtrlWebPart_LoginLnk"))
        )
        login_btn.click()

        email_field_ele = self.wait.until(
            EC.visibility_of_element_located((By.ID, "Email"))
        )
        password_field_ele = self.wait.until(
            EC.visibility_of_element_located((By.ID, "Password"))
        )

        email_field_ele.send_keys(cred_email)
        password_field_ele.send_keys(cred_pass)

        submit_btn = self.wait.until(
            EC.visibility_of_element_located(
                (By.XPATH, ".//input[starts-with(@class, 'FormButton_primaryButton')]")
            )
        )

        submit_btn.click()

        # wait... to let login be successful
        time.sleep(5)
    
    def wait_for_page_to_load(self):
        self.wait.until(
            EC.visibility_of_element_located((By.ID, "MainContent"))
        )

    def open_new_tab(self, url):
        """
        Opens a new tab with the given URL.

        :param url: The URL to open in the new tab.
        """
        # Open a new tab using JavaScript (more reliable than switch_to.new_window)
        self.driver.execute_script(f"window.open('{url}');")

        # Switch to the newly opened tab
        self.driver.switch_to.window(self.driver.window_handles[-1])

    def close_current_tab(self):
        """
        Closes the current tab and switches back to the first tab (if available).
        """
        # Close the current tab
        self.driver.close()

        # If there are other tabs open, switch back to the first tab
        if len(self.driver.window_handles) > 0:
            self.driver.switch_to.window(self.driver.window_handles[0])

    def reinit(self, url=None):
        """
        Close current Chrome instance and initialize fresh with given URL.
        If no URL is provided, uses the base_url.
        """
        # Close current driver if it exists
        if hasattr(self, "driver"):
            try:
                self.driver.quit()
            except:
                pass  # Handle case where driver might already be closed

        # Reinitialize the driver with fresh settings
        self.setup_driver()

        # Load the specified URL or default to base_url
        target_url = url if url else self.base_url
        self.driver.get(target_url)
        time.sleep(5)  # Allow page to load completely
    
    def access_restricted(self):
        """
        Check if access to the current page is restricted by verifying the presence of 
        a data protection element.

        Returns:
            bool: 
                - True if the data protection element is visible (access not restricted)
                - False if the element is not found (access likely restricted)
                
        Note:
            Uses a 2-second wait timeout to check for the element's visibility.
        """
        try:
            WebDriverWait(self.driver, 2).until(
                EC.visibility_of_element_located((By.ID, "ProdDatProtectionWebPart_MainContentCntnr"))
            )
            return True
        except Exception:
            return False
    
    def extract_data_from_table_ele(self, table):
        try:
            # ---------------------------
            # 1) Extract Dimension (Property A)
            # ---------------------------
            dimension_value = None
            try:
                # Get all rows under <tbody>
                tbody = table.find_element(By.TAG_NAME, "tbody")
                rows = tbody.find_elements(By.TAG_NAME, "tr")
            except NoSuchElementException:
                return []

            # If there's at least one row, assume the first <th> is the dimension
            if rows:
                try:
                    first_th = rows[0].find_element(By.TAG_NAME, 'th')
                    dimension_value = first_th.text.strip().replace('\n', '_')
                except NoSuchElementException:
                    # Fallback: if no <th> in first row, just use first row text
                    dimension_value = rows[0].text.strip().replace('\n', '_')

            # ---------------------------
            # 2) Extract Column Headers from <thead>
            # ---------------------------
            headers = []
            try:
                thead = table.find_element(By.TAG_NAME, 'thead')
                header_cells = thead.find_elements(By.TAG_NAME, 'td')
                for h in header_cells:
                    txt = h.text.strip().replace('\n', '_')
                    if txt:
                        headers.append(txt)
            except NoSuchElementException:
                # If no <thead> or no <td> in thead, leave headers empty
                pass
            headers.insert(-1, "serial_nu")

            # ---------------------------
            # 3) Parse the Table Rows
            # ---------------------------
            data = []
            current_property_b = None  # This will store "Black-Oxide Alloy Steel", etc.

            for row in rows:
                # Attempt to read a <th> in this row
                # If it is NOT the dimension text, treat it as the "Property B"
                try:
                    th = row.find_element(By.TAG_NAME, 'th')
                    th_text = th.text.strip().replace('\n', '_')
                    # Check if this <th> is a new "Property B" (and not the dimension)
                    if th_text and th_text != dimension_value:
                        current_property_b = th_text
                except NoSuchElementException:
                    # No <th> in this row, so we rely on current_property_b as-is
                    pass

                # Collect <td> cells from this row
                cells = row.find_elements(By.TAG_NAME, 'td')
                if cells:
                    
                    # Build a dictionary for this row
                    row_data = {
                        'Property A': dimension_value,        # e.g. "2-56"
                        'Property B': current_property_b,     # e.g. "Black-Oxide Alloy Steel"
                    }
                    # Match each cell to a header if possible
                    for i, cell in enumerate(cells):
                        cell_text = cell.text.strip().replace('\n', '_')
                        if i < len(headers):
                            row_data[headers[i]] = cell_text
                        else:
                            # If there are more <td> cells than headers, store them differently or ignore
                            pass

                    data.append(row_data)

            return data

        except NoSuchElementException as e:
            error_trace = traceback.format_exc()
            logging.error(f"Error: Element not found - {e}\nStack Trace:\n{error_trace}")
            return []
    
    def product_section_scrape_data(self, product_link, product_page_container, subcat_name1='', subcat_name2='', subcat_name3='', category_name=''):
        """
        Takes in div of product section from product page, scraps the data out of it (including tables and everything.)
        """
        global things_to_skip
        
        # Extract basic product info
        product_title = product_page_container.find_element(By.TAG_NAME, "h3").text
        img_links = list({
            img.get_attribute("src").strip()
            for img in product_page_container.find_elements(By.TAG_NAME, "img")
            if img.get_attribute("src")
        })
        product_desc = None
        try:
            product_desc = product_page_container.find_element(By.CLASS_NAME, "CpyCntnr").text.strip()
        except:
            pass
        
        ist_time = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
        ist_timestamp = ist_time.strftime("%Y-%m-%d %H:%M:%S %p IST")

        # Initialize product data structure
        product_data = {
            "category": category_name,
            "subcategory_1": subcat_name1,
            "subcategory_2":subcat_name2,
            "subcategory_3":subcat_name3,
            "title": product_title,
            "link": product_link,
            "timestamp": ist_timestamp,
            "images": img_links,
            "description": product_desc,
            "data": []
        }

        # Process all tables - with improved error handling
        try:
            # Try with a shorter timeout first to quickly determine if tables exist
            table_elements = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.TAG_NAME, "table"))
            )
            
            total_tables = len(table_elements)
            logging.info(f"Processing product: {product_title}")
            logging.info(f"Found {total_tables} tables to extract")

            for table_idx, table_e in enumerate(table_elements, 1):
                try:
                    table_data = self.extract_data_from_table_ele(table_e)
                    product_data["data"].append(table_data)
                    logging.info(f"  Extracted table {table_idx}/{total_tables}")
                except Exception as e:
                    error_trace = traceback.format_exc()
                    logging.error(f"  Failed to extract table {table_idx}: {str(e)}\nStack Trace:\n{error_trace}")
                    product_data["data"].append({"error": f"Extraction failed: {str(e)}"})
                    continue
        
        except TimeoutException:
            # No tables found
            logging.warning(f"No tables found for product: {product_title}")
            product_data["data"].append({"info": "No table data found on this page"})
        
        except Exception as e:
            error_trace = traceback.format_exc()
            logging.error(f"Error processing tables: {str(e)}\nStack Trace:\n{error_trace}")
            product_data["data"].append({"error": f"Table extraction failed: {str(e)}"})

        # Store in database
        logging.info("Saving product data to database...")
        db_client.insert_document(product_data)
        logging.info(f"Successfully saved: {product_title}")
        
        # Add the product title to the things_to_skip list
        if product_title and product_title not in things_to_skip:
            things_to_skip.append(product_title)
            save_skip_list(things_to_skip)
            logging.info(f"Added '{product_title}' to skip list")


    def handle_product_page(self, product_link, subcat_name1='', subcat_name2='', category_name='', subcat_name3='', title=''):
        """
        Processes a product page by:
        1. Scrolling to load all content
        2. Extracting product metadata (title, images, description)
        3. Extracting data from all tables
        4. Storing the complete product data in the database
        
        Args:
            product_link (str): The URL of the product page being scraped
        """
        # Wait for and scroll to the main content container
        wait = WebDriverWait(self.driver, 60)
        product_link = self.driver.current_url
        element = wait.until(EC.presence_of_element_located((By.ID, "ProdPageContent")))
        self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", element)
        time.sleep(2)  # Allow content to load after scrolling

        # Locate #PageCntnr
        try:
            page_container = self.driver.find_element(By.ID, "PageCntnr")
            sections = page_container.find_elements(By.TAG_NAME, "section")
            logging.info(f"Found {len(sections)} sections to process")
        except:
            logging.error(f"Failed to locate #PageCntnr")
            return
            
        # locate all section tags inside #PageCntnr
        for sec in sections:
            section_class = sec.get_attribute("class").strip()
            if section_class == 'ap':
                continue
            else:
                self.product_section_scrape_data(product_link, sec, subcat_name1, subcat_name2, subcat_name3, category_name)
    
    def handle_types_index_page(self, subcat_name1="", subcat_name2="", category_name="", subcat_name3=''):
        """Handles scraping of product type index pages, processing each type group and its products"""
        global things_to_skip
        
        try:
            types_containers = self.wait.until(
                EC.visibility_of_all_elements_located((By.CLASS_NAME, "GroupPrsnttn"))
            )
            
            logging.info(f"Found {len(types_containers)} type groups to process")

            for group_idx, types_cntr in enumerate(types_containers, 1):
                try:
                    type_group_name = types_cntr.find_element(By.TAG_NAME, "h3").text
                    type_elements = types_cntr.find_elements(By.TAG_NAME, "a")
                    
                    logging.info(f"Processing group {group_idx}/{len(types_containers)}: {type_group_name}")
                    logging.info(f"  Contains {len(type_elements)} products")

                    for product_idx, type_e in enumerate(type_elements, 1):
                        try:
                            # Extract product data
                            link = type_e.get_attribute("href")
                            title = type_e.find_element(By.CLASS_NAME, "ke").text
                            logging.info(f"--- Product title : {title} ---")
                            
                            # Skip if this product title is in our skip list
                            if title in things_to_skip:
                                logging.info(f"    Skipping {title} - found in skip list")
                                continue
                            
                            # Optional fields
                            image = self._get_optional_element_attribute(type_e, By.TAG_NAME, "img", "src")
                            description = self._get_optional_element_text(type_e, By.CLASS_NAME, "PrsnttnCpy")

                            logging.info(f"  Product {product_idx}/{len(type_elements)}: {title}")
                            logging.info(f"    Link: {link}")
                            if image: logging.info(f"    Image: {image}")
                            if description: logging.info(f"    Description: {description[:50]}...")

                            # Check if product exists in DB
                            if db_client.find_document({"link": link}):
                                logging.info("    [Already scraped - skipping]")
                                
                                # Add to skip list if not already there
                                if title not in things_to_skip:
                                    things_to_skip.append(title)
                                    save_skip_list(things_to_skip)
                                    logging.info(f"    Added '{title}' to skip list (found in DB)")
                                    
                                continue

                            # Process product page
                            self.open_new_tab(link)
                            self.driver.switch_to.window(self.driver.window_handles[-1])

                            if self.access_restricted():
                                raise AccessRestrictedError("Could not access the resource: access has been restricted by site.")
                            
                            self.handle_product_page(link, subcat_name1, subcat_name2, category_name, subcat_name3, title)
                            
                            self.close_current_tab()
                            self.driver.switch_to.window(self.driver.window_handles[-1])
                            
                            time.sleep(1)
                        
                        except AccessRestrictedError as e:
                            raise e
                        except Exception as e:
                            error_trace = traceback.format_exc()
                            logging.error(f"    Error processing product {product_idx}: {str(e)}\nStack Trace:\n{error_trace}")
                            continue

                    time.sleep(1)
                
                except AccessRestrictedError as e:
                    raise e
                except Exception as e:
                    error_trace = traceback.format_exc()
                    logging.error(f"  Error processing type group {group_idx}: {str(e)}\nStack Trace:\n{error_trace}")
                    continue

        except AccessRestrictedError as e:
            raise e
        except Exception as e:
            error_trace = traceback.format_exc()
            logging.error(f"\nFailed to process types index page: {str(e)}\nStack Trace:\n{error_trace}")
            raise e

    def _get_optional_element_attribute(self, parent, by, value, attr):
        """Helper to safely get optional element attribute"""
        try:
            return parent.find_element(by, value).get_attribute(attr)
        except:
            return None

    def _get_optional_element_text(self, parent, by, value):
        """Helper to safely get optional element text"""
        try:
            return parent.find_element(by, value).text
        except:
            return None
    
    def handle_subcategories_index_page(self, subcat_name1="", subcat_name2="", category_name=""):
        """Handles scraping of subcategories index pages"""
        global things_to_skip
        
        try:
            # Wait for the main container to load
            rendered_content_div = self.wait.until(
                EC.visibility_of_element_located((By.ID, "ClientRenderedContentWebPart"))
            )
            subcat_eles = rendered_content_div.find_elements(By.TAG_NAME, "a")
            
            logging.info(f"Found {len(subcat_eles)} subcategory items to process")

            for idx, subcat_e in enumerate(subcat_eles, 1):
                try:
                    # Extract all data first
                    link = subcat_e.get_attribute("href")
                    image = subcat_e.find_element(
                        By.XPATH,
                        ".//div[starts-with(@class, 'TileLayout_imageContainer')]//img"
                    ).get_attribute("src")
                    subcat_name3 = subcat_e.find_element(
                        By.XPATH, ".//div[starts-with(@class, 'TileLayout_titleContainer')]"
                    ).text.strip()
                    description = subcat_e.find_element(
                        By.XPATH, ".//div[starts-with(@class, 'TileLayout_copyContainer')]"
                    ).text.strip()
                    product_count = subcat_e.find_element(
                        By.XPATH, ".//div[starts-with(@class, 'ProductCount_productCount')]"
                    ).text.strip()

                    logging.info(f"    Processing item {idx}/{len(subcat_eles)}")
                    logging.info(f"  Sub Category 3: {subcat_name3}")
                    logging.info(f"  Products: {product_count}")
                    
                    # Skip if this subcategory is in our skip list
                    if subcat_name3 in things_to_skip:
                        logging.info(f"  Skipping {subcat_name3} - found in skip list")
                        continue
                        
                    logging.info(f"  Opening: {link}")

                    self.open_new_tab(link)
                    self.driver.switch_to.window(self.driver.window_handles[-1])
                    logging.info("--- Switched to new tab ")

                    if self.access_restricted():
                        raise AccessRestrictedError("Could not access the resource: access has been restricted by site")
                
                    if self.whether_table_page_or_not():
                        logging.info("  [Contains Table page ]")
                        self.handle_product_page(link, subcat_name1, subcat_name2, category_name, subcat_name3, "")
                    elif self.whether_product_page_or_not():
                        logging.info("  [Product page detected]")
                        self.handle_product_page(link, subcat_name1, subcat_name2, category_name, subcat_name3, '')
                    elif self.whether_types_index_page_or_not():
                        logging.info("  [Types index page detected]")
                        self.handle_types_index_page(subcat_name1, subcat_name2, category_name, subcat_name3)
                    
                    # Add to skip list after successful processing
                    if subcat_name3 not in things_to_skip:
                        things_to_skip.append(subcat_name3)
                        save_skip_list(things_to_skip)
                        logging.info(f"  Added '{subcat_name3}' to skip list")
                    
                    self.close_current_tab()
                    self.driver.switch_to.window(self.driver.window_handles[-1])
                    
                    time.sleep(1)
                
                except AccessRestrictedError as e:
                    raise e
                except Exception as e:
                    error_trace = traceback.format_exc()
                    logging.error(f"  Error processing subcategory item {idx}: {str(e)}\nStack Trace:\n{error_trace}")
                    continue
        except AccessRestrictedError as e:
            raise e
        except Exception as e:
            error_trace = traceback.format_exc()
            logging.error(f"Failed to process subcategories index page: {str(e)}\nStack Trace:\n{error_trace}")
            raise e

    def whether_types_index_page_or_not(self):
        """
        Determines if the current page is a types index page.
        Returns:
            bool: True if page is a types index page, False otherwise
        """
        time.sleep(2)
        self.wait_for_page_to_load()
        try:
            return len(self.driver.find_elements(By.CLASS_NAME, "GroupPrsnttn")) > 0
        except Exception:
            return False

    def whether_subcat_index_page_or_not(self):
        """
        Determines if the current page is a subcategory index page.
        Returns:
            bool: True if page is a subcategory index page, False otherwise
        """
        time.sleep(2)  # Allow page to load
        self.wait_for_page_to_load()
        try:
            return self.driver.find_element(By.ID, "ClientRenderedContentWebPart") is not None
        except Exception:
            return False

    def whether_product_page_or_not(self):
        """
        Determines if the current page is a product page.
        Returns:
            bool: True if page is a product page, False otherwise
        """
        time.sleep(2)  # Allow page to load
        self.wait_for_page_to_load()
        try:
            page_cntnr_ele = self.driver.find_element(By.ID, "PageCntnr")

            
            if len(page_cntnr_ele.find_elements(By.CLASS_NAME, "GroupPrsnttn")) == 0:
                return True
            else:
                # if not present then an exception will be raised
                self.driver.find_element(By.ID, "ProductPage")
                return True
        except Exception:
            return False
        
    def whether_table_page_or_not(self)-> bool:
        """
        Determines if the current page is a product page.
        Returns:
            bool: True if page is a Table page, False otherwise
        """
        time.sleep(2)  # Allow page to load
        self.wait_for_page_to_load()
        try:
            table_ele = self.driver.find_elements(By.TAG_NAME, "table")
            
            if table_ele:
                return True
            else:
                # if table not present then its a sub-category
                return False
        except Exception:
            return False
        

    def run(self):
        """Main scraping function"""
        try:
            self.load_site()
            # self.login_to_site() - Uncomment if login is required
            # logging.info("Successfully logged in")

            categories_container_ele = self.wait.until(
                EC.visibility_of_element_located((By.ID, "HomePageContent"))
            )
            category_eles = categories_container_ele.find_elements(By.CLASS_NAME, "catg")

            logging.info(f"Found {len(category_eles)} categories")
            logging.info(f"Current skip list has {len(things_to_skip)} items")

            for cat_ele in category_eles[5::]:
                cat_h1 = cat_ele.find_element(By.TAG_NAME, "h1")
                if cat_h1.text == "":
                    continue
                category_name = cat_h1.text

                logging.info(f" Processing category : {category_name}")
                # eg - Fastening and Joining

                subcat_eles = cat_ele.find_elements(By.CLASS_NAME, "subcat")

                for subcat_e in subcat_eles:
                    subcat_h2 = subcat_e.find_element(By.TAG_NAME, "h2")
                    subcat_name1 = subcat_h2.text
                    logging.info(f"  Processing sub category 1: {subcat_name1}")
                    # eg - Fasteners

                    subcat_items = subcat_e.find_elements(By.TAG_NAME, "li")
                    for sc_it in subcat_items:
                        subcat_name2 = sc_it.text
                        logging.info(f"   Processing sub category 2: {subcat_name2}")
                        # eg - Screws and Bolts

                        sc_it_link = sc_it.find_element(By.TAG_NAME, "a").get_attribute("href")
                        logging.info(f"   Processing item: {subcat_name2} ({sc_it_link})")

                        skip_item_name = category_name + '/' + subcat_name2

                        # Skip if this item is in our skip list
                        if skip_item_name in things_to_skip:
                            logging.info(f"    Skipping {skip_item_name} - found in skip list")
                            continue
                            
                        self.open_new_tab(sc_it_link)
                    
                        if self.access_restricted():
                            raise AccessRestrictedError("Could not access the resource: access has been restricted by site")
                        
                        if self.whether_table_page_or_not():
                            logging.info("      [Contains Table page ]")
                            self.handle_product_page(sc_it_link, subcat_name1, subcat_name2, category_name, "", "")

                            # Add to skip list after successful processing
                            if skip_item_name not in things_to_skip:
                                things_to_skip.append(skip_item_name)
                                save_skip_list(things_to_skip)
                                logging.info(f"    Added '{skip_item_name}' to skip list")

                        elif self.whether_subcat_index_page_or_not():
                            logging.info("      [Subcategory index page detected]")
                            self.handle_subcategories_index_page(subcat_name1, subcat_name2, category_name)

                            # Add to skip list after successful processing
                            if skip_item_name not in things_to_skip:
                                things_to_skip.append(skip_item_name)
                                save_skip_list(things_to_skip)
                                logging.info(f"    Added '{skip_item_name}' to skip list")

                        elif self.whether_types_index_page_or_not():
                            logging.info("      [Types index page detected]")
                            self.handle_types_index_page(subcat_name1, subcat_name2, category_name, "")

                            # Add to skip list after successful processing
                            if skip_item_name not in things_to_skip:
                                things_to_skip.append(skip_item_name)
                                save_skip_list(things_to_skip)
                                logging.info(f"    Added '{skip_item_name}' to skip list")

                        else:
                            logging.warning("   [Unhandeled page encountered]")

                        self.close_current_tab()
                        time.sleep(1)
        except AccessRestrictedError as e:
            logging.error(f"Access restricted: {e}")
            raise e
        except Exception as e:
            error_trace = traceback.format_exc()
            logging.error(f"Error in main run function: {str(e)}\nStack Trace:\n{error_trace}")
            raise e
        finally:
            try:
                if hasattr(self, "driver"):
                    self.driver.quit()
                    logging.info("Driver closed successfully")
            except Exception as e:
                logging.error(f"Error while closing driver: {str(e)}")


# Entry point function to execute the scraper
def run_scraper():
    scraper = McMasterScraper()
    try:
        scraper.run()
    except AccessRestrictedError as e:
        logging.error(f"Scraping stopped due to access restrictions: {e}")
        # Could implement a retry mechanism here if needed
    except Exception as e:
        logging.error(f"Scraping failed with error: {str(e)}")
    finally:
        # Final cleanup - save the skip list one last time
        save_skip_list(things_to_skip)
        logging.info(f"Scraping complete. Skip list saved with {len(things_to_skip)} items.")


if __name__ == "__main__":
    run_scraper()