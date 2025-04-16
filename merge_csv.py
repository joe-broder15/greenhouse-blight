#!/usr/bin/env python
import os
import glob
import csv
import sys

# Try to use tomllib (Python 3.11+) or fallback to tomli for older versions.
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        sys.stderr.write("Please install toml support: pip install tomli\n")
        sys.exit(1)


def load_config(config_file):
    with open(config_file, 'rb') as f:
        return tomllib.load(f)


def get_output_folders(config):
    folders = []
    for section, settings in config.items():
        if isinstance(settings, dict) and 'output_folder' in settings:
            folders.append(settings['output_folder'])
    return folders


def merge_csv_files(folders, output_file):
    file_count = 0
    header_written = False
    with open(output_file, 'w', newline='', encoding='utf-8') as fout:
        writer = csv.writer(fout)
        for folder in folders:
            if not os.path.isdir(folder):
                print(f"Warning: Folder '{folder}' does not exist, skipping.")
                continue
            csv_pattern = os.path.join(folder, '*.csv')
            csv_files = glob.glob(csv_pattern)
            for csv_file in csv_files:
                with open(csv_file, 'r', newline='', encoding='utf-8') as fin:
                    reader = csv.reader(fin)
                    rows = list(reader)
                    if not rows:
                        continue
                    if not header_written:
                        writer.writerow(rows[0])
                        header_written = True
                    # Write all rows except header
                    writer.writerows(rows[1:])
                file_count += 1
    return file_count


def main():
    config_file = 'scrape_config.toml'
    output_file = 'jobs.csv'
    config = load_config(config_file)
    folders = get_output_folders(config)
    num_files = merge_csv_files(folders, output_file)
    print(f"Merged {num_files} CSV file(s) into '{output_file}'.")
    sys.exit(0)


if __name__ == '__main__':
    main()


