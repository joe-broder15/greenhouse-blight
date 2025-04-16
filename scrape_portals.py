#!/usr/bin/env python3
import os
import sys
import csv
import argparse
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tomli as tomllib
import requests
from bs4 import BeautifulSoup


# Class to store job data that will be written to a csv file
class Job:
    """
    Class to store job data that will be written to a csv file.
    Args:
        title (str): The job title.
        company (str): The company name.
        second_line (str): Additional job info (e.g., location, department).
        link (str): URL to the job posting.
        software (str): Recruiting software name (e.g., greenhouse, lever).
    """
    def __init__(self, title: str, company: str, second_line: str, link: str, software: str):
        # Store job attributes
        self.company = company
        self.software = software
        self.title = title
        self.second_line = second_line
        self.link = link

    def __str__(self):
        # String representation for CSV writing
        return f"{self.company},{self.software},{self.title},{self.second_line},{self.link}"

    def __repr__(self):
        return self.__str__()


def greenhouse_scraper_func(company: str, portal: str) -> list:
    """
    Scrape job postings from a Greenhouse portal for a given company.
    Args:
        company (str): The company name.
        portal (str): The Greenhouse portal URL.
    Returns:
        list: A list of Job objects containing job details for the company.
    """
    jobs = []
    page = 1
    # Loop through paginated job listings
    while True:
        url = f"{portal}&page={page}"
        print(f"Scraping Greenhouse for {company} at {url}")
        try:
            # Fetch the page
            response = requests.get(url)
            response.raise_for_status()
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            break
        # Stop if no jobs are found
        if "There are no jobs that fit these filter criteria" in response.text:
            break
        soup = BeautifulSoup(response.text, "html.parser")
        job_rows = soup.find_all("tr", class_="job-post")
        if not job_rows:
            break
        # Parse each job row
        for row in job_rows:
            a_tag = row.find("a")
            if not a_tag:
                continue
            link = a_tag.get("href")
            ps = a_tag.find_all("p")
            if len(ps) < 2:
                continue
            title = ps[0].get_text(strip=True)
            second_line = ps[1].get_text(strip=True)
            jobs.append(Job(
                title=title,
                company=company,
                second_line=second_line,
                link=link,
                software="greenhouse"
            ))
        page += 1
    print(f"Finished scraping Greenhouse for {company}, found {len(jobs)} jobs.")
    return jobs


def lever_scraper_func(company: str, portal: str) -> list:
    """
    Scrape job postings from a Lever portal for a given company.
    Args:
        company (str): The company name.
        portal (str): The Lever portal URL.
    Returns:
        list: A list of Job objects containing job details for the company.
    """
    jobs = []
    print(f"Scraping Lever for {company} at {portal}")
    try:
        # Fetch the page
        response = requests.get(portal)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching {portal}: {e}")
        return jobs
    soup = BeautifulSoup(response.text, "html.parser")
    postings = soup.find_all("div", class_="posting")
    # Parse each job posting
    for posting in postings:
        link_element = posting.find("a", class_="posting-title")
        if not link_element:
            continue
        href = link_element.get("href")
        title_element = posting.find("h5", attrs={"data-qa": "posting-name"})
        if not title_element:
            continue
        title = title_element.get_text(strip=True)
        categories_div = posting.find("div", class_="posting-categories")
        second_line = ""
        if categories_div:
            spans = categories_div.find_all("span")
            second_line = " ".join(
                span.get_text(strip=True)
                for span in spans
                if span.get_text(strip=True)
            )
        jobs.append(Job(
            title=title,
            company=company,
            second_line=second_line,
            link=href,
            software="lever"
        ))
    print(f"Finished scraping Lever for {company}, found {len(jobs)} jobs.")
    return jobs


# Registry for scraper functions
SCRAPER_REGISTRY = {
    "greenhouse": greenhouse_scraper_func,
    "lever": lever_scraper_func,
}


def parse_args():
    """
    Parse command-line arguments for the script.
    Returns:
        argparse.Namespace: Parsed arguments including config file path and software type.
    """
    parser = argparse.ArgumentParser(description="Scrape Job Portals to extract job data")
    parser.add_argument(
        "--config", "-c",
        default="scrape_config.toml",
        help="Path to configuration TOML file (default: scrape_config.toml)"
    )
    parser.add_argument(
        "--software", "-s",
        type=str,
        default="greenhouse",
        choices=["greenhouse", "lever"],
        help="Recruiting software to scrape (default: greenhouse)"
    )
    return parser.parse_args()


def load_config(config_path):
    """
    Load a TOML configuration file from the given path using tomllib/tomli fallback.
    Args:
        config_path (str): Path to the TOML configuration file.
    Returns:
        dict: Parsed configuration as a dictionary.
    """
    try:
        with open(config_path, "rb") as f:
            return tomllib.load(f)
    except Exception as e:
        logging.error(f"Error loading configuration file '{config_path}': {e}")
        sys.exit(1)


def main():
    """
    Main entry point for the script. Loads configuration, selects the appropriate scraper,
    runs the scraping process for each company, and writes the results to a CSV file.
    """
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    config = load_config(args.config)

    software_key = args.software.lower()
    software_config = config.get(software_key)
    if not software_config:
        logging.error(f"Configuration for software '{args.software}' not found in config file.")
        sys.exit(1)

    output_folder = software_config.get("output_folder", "").strip()
    if not output_folder:
        logging.error(f"'output_folder' not specified in configuration for {args.software}.")
        sys.exit(1)
    os.makedirs(output_folder, exist_ok=True)

    combined_file = os.path.join(output_folder, f"{args.software}_combined.txt")
    if not os.path.exists(combined_file):
        logging.error(f"Combined file '{combined_file}' not found. Please run the company parser first.")
        sys.exit(1)

    # Read company and portal entries from the combined file
    with open(combined_file, "r", encoding="utf-8") as f:
        entries = [line.strip() for line in f if line.strip()]
        entries = [line.split(",", 1) for line in entries]

    # Get the scraper function from the registry
    scraper_func = SCRAPER_REGISTRY.get(software_key)
    if not scraper_func:
        logging.error(f"Unsupported software: {args.software}")
        sys.exit(1)

    # Use threads to process each entry with a maximum of 10 workers
    def run_scraper(entry):
        """
        Run the scraper function for a single company/portal entry.
        Args:
            entry (list): [company, portal] pair.
        Returns:
            list: List of Job objects for the company.
        """
        company, portal = entry
        return scraper_func(company, portal)

    # Run scrapers in parallel
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(run_scraper, entries))

    # Flatten the list of job lists
    jobs = [job for sublist in results for job in sublist]
    logging.info(f"Scraped a total of {len(jobs)} jobs.")

    # Write results to CSV
    csv_file = os.path.join(output_folder, f"{args.software}_jobs.csv")
    try:
        with open(csv_file, "w", newline='', encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["company", "software", "title", "second_line", "link"])
            for job in jobs:
                writer.writerow([job.company, job.software, job.title, job.second_line, job.link])
        logging.info(f"Job data successfully written to CSV file: {csv_file}")
    except Exception as e:
        logging.error(f"Error writing CSV file '{csv_file}': {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()





