
import os
from selenium.webdriver.chrome.options import Options
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class SiteConfig:
    # Base URLs
    BASE_URL = "https://www.mcmaster.com/"

    # Selectors (CSS or XPath)


class ScraperConfig:
    # Browser settings
    HEADLESS = False  # Run browser in headless mode (no GUI)
    BROWSER = "chrome"  # Options: "chrome", "firefox", etc.
    # Proxy settings (if needed)
    USE_PROXY = False
    PROXY_HOSTNAME = "gate.smartproxy.com"
    PROXY_PORT = 10005

    @staticmethod
    def get_chrome_options():
        """Returns Chrome options based on the configuration."""
        chrome_options = Options()
        if ScraperConfig.HEADLESS:
            chrome_options.add_argument("--headless")  # Run in headless mode
        if ScraperConfig.USE_PROXY:
            proxy_address = "{hostname}:{port}".format(
                hostname=ScraperConfig.PROXY_HOSTNAME,
                port=ScraperConfig.PROXY_PORT,
            )
            chrome_options.add_argument("--proxy-server={}".format(proxy_address))
        chrome_options.add_argument("--disable-gpu")  # Disable GPU acceleration
        chrome_options.add_argument("--no-sandbox")  # Bypass OS security model
        chrome_options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
        chrome_options.add_argument("--incognito")
        chrome_options.add_argument("--disable-popup-blocking")
        return chrome_options