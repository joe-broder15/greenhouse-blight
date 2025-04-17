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


def merge_csv_files(folders, output_file):
    """
    Merge all CSV files from the specified folders into a single output CSV file.
    Writes the header from the first file, then appends all rows (excluding headers) from all files.
    Returns the number of CSV files processed.
    """
    file_count = 0
    header_written = False
    with open(output_file, 'w', newline='', encoding='utf-8') as fout:
        writer = csv.writer(fout)
        for folder in folders:
            # Skip folders that do not exist
            if not os.path.isdir(folder):
                print(f"Warning: Folder '{folder}' does not exist, skipping.")
                continue
            # Find all CSV files in the folder
            csv_pattern = os.path.join(folder, '*.csv')
            csv_files = glob.glob(csv_pattern)
            for csv_file in csv_files:
                with open(csv_file, 'r', newline='', encoding='utf-8') as fin:
                    reader = csv.reader(fin)
                    rows = list(reader)
                    if not rows:
                        continue  # Skip empty files
                    if not header_written:
                        writer.writerow(rows[0])  # Write header from first file
                        header_written = True
                    # Write all rows except header
                    writer.writerows(rows[1:])
                file_count += 1
    return file_count


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
    # Merge CSV files from all output folders into the output file
    num_files = merge_csv_files(folders, output_file)
    print(f"Merged {num_files} CSV file(s) into '{output_file}'.")
    sys.exit(0)


if __name__ == '__main__':
    main()


