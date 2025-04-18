import time
from src.scraper.scraper import McMasterScraper
from src.scraper.exceptions import AccessRestrictedError


if __name__ == "__main__":
    max_retries = 5
    retry_delay = 60  # seconds
    
    for attempt in range(max_retries):
        try:
            scraper = McMasterScraper()
            scraper.run()
            break
        except AccessRestrictedError as e:
            del scraper
            print(f"Attempt {attempt + 1}/{max_retries}: Access restricted. Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
    else:
        print("Max retries reached. Exiting...")