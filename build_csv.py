#!/usr/bin/env python
import os
import glob
import csv
import sys
import argparse
import tomli


def load_config(config_file):
    """
    Load the TOML configuration file and return the parsed config dictionary.
    """
    with open(config_file, 'rb') as f:
        return tomli.load(f)


def get_output_folders(config):
    """
    Extract the list of output folders from the config dictionary.
    Each section with an 'output_folder' key is included.
    """
    folders = []
    for section, settings in config.items():
        # Only consider sections that are dicts and have an 'output_folder' key
        if isinstance(settings, dict) and 'output_folder' in settings:
            folders.append(settings['output_folder'])
    return folders


def merge_csv_files(folders, output_file, filters=None, negative_filters=None):
    """
    Merge multiple CSV files into a single output, filtering rows by job title.

    Args:
        folders (list[str]): Directories containing CSV files to merge.
        output_file (str): Path for the merged CSV output.
        filters (list[str], optional): Include a row if its title contains any of these terms (case-insensitive).
        negative_filters (list[str], optional): Exclude a row if its title contains any of these terms (case-insensitive).

    Returns:
        int: Number of CSV files successfully processed.
    """
    # Normalize filter lists to lowercase for faster checks
    include_terms = [term.lower() for term in filters] if filters else []
    exclude_terms = [term.lower() for term in negative_filters] if negative_filters else []

    processed_count = 0
    header_written = False

    # Open the output CSV once for writing
    with open(output_file, 'w', newline='', encoding='utf-8') as fout:
        writer = csv.writer(fout)

        # Loop through each specified folder
        for folder in folders:
            if not os.path.isdir(folder):
                print(f"Warning: '{folder}' is not a directory, skipping.")
                continue

            # Find all CSV files in the folder
            pattern = os.path.join(folder, '*.csv')
            for csv_path in glob.glob(pattern):
                try:
                    with open(csv_path, 'r', newline='', encoding='utf-8') as fin:
                        reader = csv.reader(fin)

                        # Read header row; skip file if empty
                        try:
                            header = next(reader)
                        except StopIteration:
                            continue

                        # Write header only once
                        if not header_written:
                            writer.writerow(header)
                            header_written = True

                        # Locate the 'title' column index
                        try:
                            title_idx = next(
                                idx for idx, col in enumerate(header)
                                if col.strip().lower() == 'title'
                            )
                        except StopIteration:
                            print(f"Warning: No 'title' column in '{csv_path}', skipping.")
                            continue

                        # Process data rows
                        for row in reader:
                            if len(row) <= title_idx:
                                continue
                            title_lower = row[title_idx].strip().lower()

                            # Exclude rows matching any negative filter
                            if exclude_terms and any(term in title_lower for term in exclude_terms):
                                continue
                            # Include rows if no positive filters are set,
                            # or if at least one positive filter matches
                            if not include_terms or any(term in title_lower for term in include_terms):
                                writer.writerow(row)

                    processed_count += 1

                except Exception as err:
                    print(f"Warning: Could not process '{csv_path}': {err}")

    return processed_count


def parse_args():
    """
    Parse command-line arguments for the script.
    Returns:
        argparse.Namespace: Parsed arguments including config file path and output file name.
    """
    parser = argparse.ArgumentParser(description="Merge CSV files from multiple output folders specified in a TOML config.")
    parser.add_argument('--config', '-c', default='scrape_config.toml', help='Path to configuration TOML file (default: scrape_config.toml)')
    parser.add_argument('--output', '-o', default='jobs.csv', help='Output CSV file name (default: jobs.csv)')
    return parser.parse_args()


def main():
    args = parse_args()
    config_file = args.config  # Config file path from command line
    output_file = args.output  # Output CSV file path from command line

    # Load configuration from TOML file
    config = load_config(config_file)
    # Extract output folders from config
    folders = get_output_folders(config)
    # Get filters from the [common] section if available
    filters = None
    negative_filters = None
    if 'common' in config:
        if 'any_job_filters' in config['common']:
            filters = config['common']['any_job_filters']
        if 'none_job_filters' in config['common']:
            negative_filters = config['common']['none_job_filters']
    # Merge CSV files from all output folders into the output file, filtering by title
    num_files = merge_csv_files(folders, output_file, filters=filters, negative_filters=negative_filters)
    print(f"Merged {num_files} CSV file(s) into '{output_file}'.")
    sys.exit(0)


if __name__ == '__main__':
    main()


