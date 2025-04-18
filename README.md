# greenhouse-blight

## Description

**greenhouse-blight** is an OSINT-powered toolkit to discover and aggregate job postings from major recruiting platforms (Greenhouse and Lever). It automates the process of finding, parsing, and merging job listings, making it easy to collect every job application ever for your target criteria.

## Supported Software

- Greenhouse
- Lever

## Explanation of Each Script

- **recon.py**  
  Uses Selenium to perform Google dorking and collect job board links for the specified recruiting software. It simulates human browsing to avoid CAPTCHAs and saves discovered links to output folders. Supports Greenhouse and Lever.

- **parse_company_portals.py**  
  Processes the collected links, extracts unique company names using regex, and generates company-specific job portal URLs for each supported platform. Supports Greenhouse and Lever.

- **scrape_portals.py**  
  Scrapes job postings from each company's job portal (Greenhouse or Lever), extracting job details and saving them to CSV files.

- **build_csv.py**  
  Merges all the individual CSV files from each platform into a single, unified `jobs.csv` file. Only Greenhouse and Lever jobs are merged. Supports filtering by job title using the configuration in `scrape_config.toml`.

- **main.sh**  
  A shell script that runs the entire pipeline in order: collecting links, parsing companies, scraping jobs, and merging results. Only Greenhouse and Lever are included in the scraping and merging steps.

## Running the Program

1. **Install dependencies**  
   - Python 3.8+ (with `tomli` for TOML parsing)
   - Selenium (`pip install selenium`)
   - ChromeDriver (place in the `chromedriver/` directory)
   - BeautifulSoup (`pip install beautifulsoup4`)
   - Requests (`pip install requests`)

2. **Configure**  
   Edit `scrape_config.toml` to adjust dorks, patterns, and output folders if needed.

3. **Run the pipeline**  
   The easiest way is to execute the provided shell script:
   ```sh
   sh main.sh
   ```
   Or, run each step manually:
   ```sh
   python recon.py --software greenhouse
   python recon.py --software lever
   python parse_company_portals.py --software greenhouse
   python parse_company_portals.py --software lever
   python scrape_portals.py --software greenhouse
   python scrape_portals.py --software lever
   python build_csv.py
   ```
   **Note:** Ashby is not currently supported in the pipeline. Only Greenhouse and Lever are supported for all steps.

4. **Result**  
   The final merged job listings (Greenhouse and Lever only) will be in `jobs.csv`.
