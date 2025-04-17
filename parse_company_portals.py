import re
import sys
import os
import urllib.parse
import logging
import argparse
from pathlib import Path
import tomli

def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )


def load_config(config_path: str):
    """Load configuration from a TOML file."""
    try:
        with open(config_path, 'rb') as f:
            config = tomli.load(f)
        return config
    except Exception as e:
        logging.error(f"Error loading configuration file '{config_path}': {e}")
        sys.exit(1)


# Helper function to extract company names from the links file
def extract_company_names(links_file: str, pattern: str, site_name: str) -> set:
    """Extracts unique company names from the links file using a regex pattern.

    For the 'lever' site, trims the company name at '&' or '?' if present.
    Returns a set of unique company names.
    """
    company_names = set()
    try:
        with open(links_file, 'r', encoding='utf-8') as f:
            for line in f:
                # Apply the regex pattern to extract the company name
                match = re.search(pattern, line.strip())
                if match:
                    company = match.group(1)
                    # Special processing for Lever: remove extra query parameters
                    if site_name.lower() == "lever":
                        company = re.split(r"[&?]", company)[0]
                    company_names.add(company)
    except Exception as e:
        logging.error(f"{site_name}: Error reading links file '{links_file}': {e}")
    return company_names


# Helper function to write a list of lines to a file, overwriting existing content
def write_lines_to_file(file_path: str, lines: list) -> bool:
    """Writes the provided list of lines to the specified file.

    Each line is written followed by a newline. The file is overwritten if it exists.
    Returns True on success, False otherwise.
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            for line in lines:
                f.write(f"{line}\n")
        return True
    except Exception as e:
        logging.error(f"Error writing to file '{file_path}': {e}")
        return False


def parse_site_links(site_name: str, software_config: dict) -> bool:
    """Processes the site's links file to extract company names and generate portal URLs.

    This function performs the following steps:
      1. Reads the links file specified in the configuration.
      2. Uses a regex pattern to extract unique company names (with special handling for Lever).
      3. Overwrites the companies file with the sorted list of company names.
      4. Constructs portal URLs using a provided template and writes them to the portals file.

    All output files are overwritten on each run to ensure fresh data.
    """
    logging.info(f"Processing {site_name} links")

    # --- Retrieve and build output file paths using output_folder from configuration ---
    output_folder = software_config.get("output_folder", "").strip()
    if not output_folder:
        raise ValueError(f"{site_name}: 'output_folder' not specified or empty in configuration")
    os.makedirs(output_folder, exist_ok=True)
    links_file = os.path.join(output_folder, "links.txt")
    combined_file = os.path.join(output_folder, f"{site_name}_combined.txt")

    # Validate the regex pattern for extracting company names
    pattern = software_config.get("pattern")
    if not pattern:
        logging.error(f"{site_name}: 'pattern' not specified in configuration.")
        return False

    # Validate the portal URL template
    portal_url_template = software_config.get("portal_url_template")
    if not portal_url_template:
        logging.error(f"{site_name}: 'portal_url_template' not specified in configuration.")
        return False

    # --- Verify that the links file exists ---
    if not Path(links_file).exists():
        logging.error(f"{site_name}: Links file '{links_file}' not found.")
        return False

    # --- Extract company names from the links file ---
    company_names = extract_company_names(links_file, pattern, site_name)
    if not company_names:
        logging.warning(f"{site_name}: No matching URLs found in '{links_file}'.")
        return True

    # --- Generate and write the combined company and portal file ---
    if site_name.lower() == "ashby":
        combined_list = [f"{urllib.parse.unquote(company)},{portal_url_template.format(company=company)}" for company in sorted(company_names)]
    else:
        combined_list = [f"{company},{portal_url_template.format(company=company)}" for company in sorted(company_names)]
    if not write_lines_to_file(combined_file, combined_list):
        logging.error(f"{site_name}: Error writing combined company and portal URLs to '{combined_file}'.")
        return False
    logging.info(f"{site_name}: Written {len(company_names)} combined company and portal URLs in '{combined_file}'")

    # --- Return success ---
    return True


def parse_args():
    """
    Parse command-line arguments for the script.
    Returns:
        argparse.Namespace: Parsed arguments including config file path, software type, and verbose flag.
    """
    parser = argparse.ArgumentParser(
        description="Unified Company Parser: Extracts company names from job board URLs (Greenhouse, Lever, Ashby) based on a config TOML file."
    )
    parser.add_argument("--config", "-c", default="scrape_config.toml",
                        help="Path to configuration TOML file (default: scrape_config.toml)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--software", "-s", type=str, default="greenhouse", choices=["greenhouse", "lever", "ashby"], help="Recruiting software to process (default: greenhouse)")
    return parser.parse_args()


def main():
    args = parse_args()
    setup_logging(args.verbose)
    logging.info("Starting Unified Company Parser")

    config = load_config(args.config)

    site = args.software
    software_config = config.get(site)
    if not software_config:
        logging.warning(f"Configuration for site '{site}' not found in config file.")
        sys.exit(1)
    result = parse_site_links(site, software_config)
    success = result

    if success:
        logging.info("Processing completed successfully")
        sys.exit(0)
    else:
        logging.error("Processing encountered errors")
        sys.exit(1)


if __name__ == "__main__":
    main() 