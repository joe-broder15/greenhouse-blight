import time
import signal
import sys
import os
import argparse
import tomli
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains

class JobBoardScraper:
    def __init__(self, software="greenhouse", config_file="scrape_config.toml", chromedriver_path=None):
        """
        Initialize the JobBoardScraper.
        Args:
            software (str): The recruiting software to use (e.g., 'greenhouse', 'lever', 'ashby').
            config_file (str): Path to the TOML configuration file.
            chromedriver_path (str or None): Path to the ChromeDriver executable. If None, uses default path.
        """
        self.software = software.lower()
        self.found_links = set()
        self.driver = None
        if chromedriver_path is None:
            self.chromedriver_path = os.path.join("chromedriver", "chromedriver.exe")
        else:
            self.chromedriver_path = chromedriver_path
        self.is_exiting = False
        self.load_config(config_file)
        # Ensure the links file exists
        if not os.path.exists(self.links_file):
            with open(self.links_file, "w") as f:
                pass
        self.setup_driver()
        # Register signal handler for graceful exit
        signal.signal(signal.SIGINT, self.handle_exit)

    def load_config(self, config_file):
        """
        Load configuration from TOML file based on selected software.
        Sets up search dork, URL patterns, and output folder.
        Args:
            config_file (str): Path to the TOML configuration file.
        """
        try:
            with open(config_file, "rb") as f:
                config = tomli.load(f)
            # Extract configuration values for the specified software
            software_config = config.get(self.software, {})
            if not software_config:
                print(f"No configuration found for {self.software}, falling back to greenhouse")
                self.software = "greenhouse"
                software_config = config.get("greenhouse", {})
            # Combine the site-specific dork with the common dork if present
            site_dork = software_config.get("dork", "")
            common_dork = config.get("common", {}).get("common_dork", "")
            if common_dork:
                self.search_dork = f"{site_dork} {common_dork}".strip()
            else:
                self.search_dork = site_dork
            self.url_patterns = software_config.get("url_patterns", [])
            output_folder = software_config.get("output_folder", "").strip()
            os.makedirs(output_folder, exist_ok=True)
            self.links_file = os.path.join(output_folder, "links.txt")
            print(f"Loaded {self.software} configuration from {config_file}")
        except Exception as e:
            print(f"Error loading configuration: {e}")
            sys.exit(1)

    def setup_driver(self):
        """
        Initialize Chrome browser with local chromedriver, using a random user-agent.
        """
        options = Options()
        # List of common user-agent strings
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        ]
        user_agent = random.choice(user_agents)
        options.add_argument(f"--user-agent={user_agent}")
        service = Service(executable_path=self.chromedriver_path)
        self.driver = webdriver.Chrome(service=service, options=options)

    def handle_exit(self, sig=None, frame=None):
        """
        Handle exit (Ctrl+C or normal termination).
        Saves links and closes the browser.
        Args:
            sig: Signal number (optional).
            frame: Current stack frame (optional).
        """
        if self.is_exiting:
            return
        self.is_exiting = True
        print("\nSaving links and exiting...")
        self.save_links()
        if self.driver:
            self.driver.quit()
        sys.exit(0)

    def save_links(self):
        """
        Save collected links to file.
        Writes all found links to the links file.
        """
        # Ensure output directory exists
        os.makedirs(os.path.dirname(self.links_file), exist_ok=True)
        print(f"Saving {len(self.found_links)} links to {self.links_file}")
        with open(self.links_file, "w") as f:
            for link in sorted(self.found_links):
                f.write(f"{link}\n")

    def is_captcha_present(self):
        """
        Check for CAPTCHA based on the presence of the reCAPTCHA script.
        Returns:
            bool: True if CAPTCHA is detected, False otherwise.
        """
        page_source = self.driver.page_source
        return 'Our systems have detected unusual traffic from your computer network.' in page_source

    def handle_captcha(self):
        """
        Pause execution until user solves CAPTCHA.
        Automatically detects if CAPTCHA is solved by checking for the target text every second.
        """
        captcha_text = 'Our systems have detected unusual traffic from your computer network.'
        if self.is_captcha_present():
            print("CAPTCHA detected! Waiting for it to be solved...")
            while captcha_text in self.driver.page_source:
                time.sleep(1)
            print("CAPTCHA appears to be solved. Continuing...")

    def wait_for_element(self, selector, by=By.CSS_SELECTOR, max_retries=5):
        """
        Wait for an element with retry logic instead of timeout.
        Args:
            selector (str): The selector to search for.
            by (selenium.webdriver.common.by.By): The method to locate elements.
            max_retries (int): Maximum number of retries.
        Returns:
            bool: True if element is found, False otherwise.
        """
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
        """
        Find and collect relevant links on current page.
        Adds links matching configured URL patterns to found_links.
        """
        # Iterate over all anchor elements on the page
        for element in self.driver.find_elements(By.CSS_SELECTOR, "a"):
            href = element.get_attribute("href")
            if href:
                # Check if any configured URL pattern matches
                if any(pattern in href for pattern in self.url_patterns):
                    self.found_links.add(href)
                    print(f"Found link: {href}")

    def random_human_delay(self, min_sec=1, max_sec=3):
        """
        Sleep for a random duration between min_sec and max_sec seconds to simulate human behavior.
        Args:
            min_sec (int): Minimum seconds to sleep.
            max_sec (int): Maximum seconds to sleep.
        """
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)

    def simulate_human_interaction(self):
        """
        Simulate human-like scrolling and mouse movement on the page, in random order.
        """
        actions = []
        # Add scrolling action
        def scroll_action():
            scroll_height = self.driver.execute_script("return document.body.scrollHeight")
            for _ in range(random.randint(0, 2)):
                scroll_to = random.randint(0, scroll_height)
                self.driver.execute_script(f"window.scrollTo(0, {scroll_to});")
                self.random_human_delay(0, 2)
        actions.append(scroll_action)
        # Add mouse movement action
        def mouse_action():
            try:
                action = ActionChains(self.driver)
                window_width = self.driver.execute_script("return window.innerWidth")
                window_height = self.driver.execute_script("return window.innerHeight")
                for _ in range(random.randint(0, 2)):
                    x = random.randint(0, window_width - 1)
                    y = random.randint(0, window_height - 1)
                    action.move_by_offset(x, y).perform()
                    self.random_human_delay(0, 2)
                    action.move_by_offset(-x, -y)  # Move back to origin for next move
            except Exception:
                pass  # Ignore if mouse movement fails
        actions.append(mouse_action)
        # Shuffle and execute actions
        random.shuffle(actions)
        for act in actions:
            act()

    def go_to_next_page(self):
        """
        Navigate to next page of results if available, with simulated human interaction before clicking.
        Returns:
            bool: True if next page is found and clicked, False otherwise.
        """
        self.simulate_human_interaction()  # Simulate interaction before clicking next
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
        """
        Wait for either search results or CAPTCHA to appear.
        Returns:
            bool: True if page loads or CAPTCHA appears, False otherwise.
        """
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
        """
        Main execution flow for scraping.
        Navigates to Google, performs the search, collects links, and paginates through results.
        """
        try:
            # Go to Google and search
            self.driver.get("https://www.google.com")
            self.simulate_human_interaction()
            search_box = self.driver.find_element(By.NAME, "q")
            search_box.send_keys(self.search_dork)
            self.simulate_human_interaction()
            search_box.send_keys(Keys.RETURN)
            # Wait for page to load (either results or CAPTCHA)
            self.wait_for_page_load()
            self.simulate_human_interaction()
            page_number = 1
            while True:
                self.simulate_human_interaction()
                self.handle_captcha()
                print(f"Processing page {page_number}...")
                self.collect_links_on_page()
                if not self.go_to_next_page():
                    break
                page_number += 1
                # Wait after navigating to next page as well
                self.wait_for_page_load()
                self.simulate_human_interaction()
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            self.handle_exit()

def parse_args():
    """
    Parse command-line arguments for the script.
    Returns:
        argparse.Namespace: Parsed arguments including software type and config file path.
    """
    parser = argparse.ArgumentParser(description="Scrape job board links from recruiting software sites")
    parser.add_argument(
        "--software", "-s", 
        type=str, 
        default="greenhouse",
        choices=["greenhouse", "lever", "ashby"],
        help="Recruiting software to scrape (default: greenhouse)"
    )
    parser.add_argument(
        "--config", "-c",
        type=str,
        default="scrape_config.toml",
        help="Path to configuration TOML file (default: scrape_config.toml)"
    )
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    scraper = JobBoardScraper(software=args.software, config_file=args.config)
    scraper.run()