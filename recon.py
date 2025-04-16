import time
import signal
import sys
import os
import argparse
import tomli
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException

class JobBoardScraper:
    def __init__(self, software="greenhouse", config_file="scrape_config.toml", chromedriver_path=None):
        self.software = software.lower()
        self.found_links = set()
        self.driver = None
        if chromedriver_path is None:
            self.chromedriver_path = os.path.join("chromedriver", "chromedriver.exe")
        else:
            self.chromedriver_path = chromedriver_path
        self.is_exiting = False
        self.load_config(config_file)
        if not os.path.exists(self.links_file):
            with open(self.links_file, "w") as f:
                pass
        self.setup_driver()
        signal.signal(signal.SIGINT, self.handle_exit)

    def load_config(self, config_file):
        """Load configuration from TOML file based on selected software"""
        try:
            with open(config_file, "rb") as f:
                config = tomli.load(f)
                
            # Extract configuration values for the specified software
            software_config = config.get(self.software, {})
            if not software_config:
                print(f"No configuration found for {self.software}, falling back to greenhouse")
                self.software = "greenhouse"
                software_config = config.get("greenhouse", {})
                
            self.search_dork = software_config.get("dork", "")
            self.url_patterns = software_config.get("url_patterns", [])
            output_folder = software_config.get("output_folder", "").strip()
            os.makedirs(output_folder, exist_ok=True)
            self.links_file = os.path.join(output_folder, "links.txt")
            print(f"Loaded {self.software} configuration from {config_file}")

        except Exception as e:
            print(f"Error loading configuration: {e}")
            sys.exit(1)

    def setup_driver(self):
        """Initialize Chrome browser with local chromedriver"""
        options = Options()
        options.add_argument("--start-maximized")
        service = Service(executable_path=self.chromedriver_path)
        self.driver = webdriver.Chrome(service=service, options=options)

    def handle_exit(self, sig=None, frame=None):
        """Handle exit (Ctrl+C or normal termination)"""
        if self.is_exiting:
            return
        self.is_exiting = True
        print("\nSaving links and exiting...")
        self.save_links()
        if self.driver:
            self.driver.quit()
        sys.exit(0)

    def save_links(self):
        """Save collected links to file"""
        # Ensure wordlists directory exists
        os.makedirs(os.path.dirname(self.links_file), exist_ok=True)
        print(f"Saving {len(self.found_links)} links to {self.links_file}")
        with open(self.links_file, "w") as f:
            for link in sorted(self.found_links):
                f.write(f"{link}\n")

    def is_captcha_present(self):
        """Check for CAPTCHA based on the presence of the reCAPTCHA script."""
        page_source = self.driver.page_source
        return 'Our systems have detected unusual traffic from your computer network.' in page_source

    def handle_captcha(self):
        """Pause execution until user solves CAPTCHA"""
        if self.is_captcha_present():
            print("CAPTCHA detected! Please solve it manually.")
            input("Press Enter after solving the CAPTCHA...")

    def wait_for_element(self, selector, by=By.CSS_SELECTOR, max_retries=5):
        """Wait for an element with retry logic instead of timeout"""
        retries = 0
        while retries < max_retries:
            try:
                elements = self.driver.find_elements(by, selector)
                if elements:
                    return True
                print(f"Element {selector} not found, retrying ({retries+1}/{max_retries})...")
                time.sleep(2)
                retries += 1
            except Exception as e:
                print(f"Error while waiting: {e}")
                retries += 1
        
        print(f"Element {selector} not found after {max_retries} attempts")
        return False

    def collect_links_on_page(self):
        """Find and collect relevant links on current page"""
        # Wait without timeout
        for element in self.driver.find_elements(By.CSS_SELECTOR, "a"):
            href = element.get_attribute("href")
            if href:
                # Check if any configured URL pattern matches
                if any(pattern in href for pattern in self.url_patterns):
                    self.found_links.add(href)
                    print(f"Found link: {href}")

    def go_to_next_page(self):
        """Navigate to next page of results if available"""
        try:
            try:
                next_link = self.driver.find_element(By.ID, "pnnext")
                next_link = next_link.find_element(By.CSS_SELECTOR, "span.oeN89d")
            except NoSuchElementException:
                print("Next page element not found.")
                return False
            next_link.click()
            return True
        except NoSuchElementException:
            print("No more pages. Finished scraping.")
            return False
        
    def wait_for_page_load(self):
        """Wait for either search results or CAPTCHA to appear"""
        max_retries = 10
        retries = 0
        
        while retries < max_retries:
            try:
                # Check if search results container is present
                results_container = self.driver.find_elements(By.ID, "rcnt")
                
                # Check if CAPTCHA message is present
                page_source = self.driver.page_source
                captcha_present = 'Our systems have detected unusual traffic from your computer network.' in page_source
                
                if results_container or captcha_present:
                    return True
                    
                print(f"Waiting for page to load... ({retries+1}/{max_retries})")
                time.sleep(2)
                retries += 1
                
            except Exception as e:
                print(f"Error while waiting for page load: {e}")
                retries += 1
        
        print(f"Page did not load properly after {max_retries} attempts")
        return False

    def run(self):
        """Main execution flow"""
        try:
            # Go to Google and search
            self.driver.get("https://www.google.com")
            search_box = self.driver.find_element(By.NAME, "q")
            search_box.send_keys(self.search_dork)
            search_box.send_keys(Keys.RETURN)
            
            # Wait for page to load (either results or CAPTCHA)
            self.wait_for_page_load()
            
            page_number = 1
            while True:
                time.sleep(3)
                self.handle_captcha()
                print(f"Processing page {page_number}...")
                
                self.collect_links_on_page()
                
                if not self.go_to_next_page():
                    break

                page_number += 1
                
                # Wait after navigating to next page as well
                self.wait_for_page_load()
                    
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            self.handle_exit()

def parse_args():
    parser = argparse.ArgumentParser(description="Scrape job board links from recruiting software sites")
    parser.add_argument(
        "--software", "-s", 
        type=str, 
        default="greenhouse",
        choices=["greenhouse", "lever", "ashby"],
        help="Recruiting software to scrape (default: greenhouse)"
    )
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    scraper = JobBoardScraper(software=args.software)
    scraper.run()