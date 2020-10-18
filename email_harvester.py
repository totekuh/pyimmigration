#!/usr/bin/env python3
import glob
import logging
import os
from threading import Thread
import urllib3

urllib3.disable_warnings()

import requests
from email_scraper import scrape_emails

logging.basicConfig(format='[%(asctime)s %(levelname)s]: %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p',
                    level='INFO')
DATASET_DIR = 'dataset'
DEFAULT_THREADS_LIMIT = 10
CONTACTS_FILE_PATTERN = '*_contacts.txt'
DEFAULT_FORMAT = 'name###url'
HARVEST_FILE = 'harvest.txt'
sleep_timer_in_seconds = 10

# we don't need it
EMAIL_BLACKLIST = ['noreply@indeed.com', '@sentry.indeed.com']


def get_arguments():
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('--dataset-dir',
                        dest='dataset_dir',
                        default=DATASET_DIR,
                        required=False,
                        help='Specify a dataset directory from the pyapplicant script to collect the emails. '
                             f"Default is {DATASET_DIR}")
    parser.add_argument('--format',
                        dest='format',
                        default=DEFAULT_FORMAT,
                        required=False,
                        help='Specify the link format for the email harvester. '
                             'It can be an URL or a company name with an URL. '
                             '1st example: https://company-site.com ;'
                             '2nd example: companyName###https://company-site.com ;'
                             f'Default is {DEFAULT_FORMAT}')
    parser.add_argument('--threads',
                        dest='threads',
                        required=False,
                        default=DEFAULT_THREADS_LIMIT,
                        type=int,
                        help='Specify a number of threads for the email harvesting. '
                             f'Default is {DEFAULT_THREADS_LIMIT}')
    options = parser.parse_args()

    return options


options = get_arguments()


def read_captures_emails(harvest_file=HARVEST_FILE):
    if os.path.exists(harvest_file):
        with open(HARVEST_FILE, 'r') as f:
            return [email.strip() for email in f.readlines()]
    else:
        return []


class EmailScraper:
    def __init__(self, file=HARVEST_FILE):
        self.output_file = file

    def find_email(self, company, url):
        if not url.startswith('https://'):
            url = f"https://{url}"
        try:
            resp = requests.get(url, headers={
                'User-Agent': "Did you play Crusader Kings 3?"
            },
                                verify=False,
                                timeout=10)
            if resp.ok:
                emails = scrape_emails(resp.text)
                if emails:
                    for email in emails:
                        if not any(junk in email for junk in EMAIL_BLACKLIST) and email not in read_captures_emails():
                            self.save_email(email)

            else:
                logging.warning(f'{company} has returned unexpected status code: {resp.status_code}')
        except Exception as e:
            logging.error(e)

    def save_email(self, email):
        with open(self.output_file, 'a') as f:
            f.write(email)
            f.write('\n')


def parse_contacts_files(dataset_dir):
    contact_files = glob.glob(f'{dataset_dir}/*/{CONTACTS_FILE_PATTERN}')
    contacts = set()
    for file in contact_files:
        with open(file, 'r') as contact_file:
            for line in contact_file.readlines():
                contacts.add(line.strip())
    logging.info(f'{len(contacts)} URLs have been passed for email harvesting')
    return contacts


def run_email_harvesting(contacts, threads_limit, format):
    scraper = EmailScraper()

    scraper_threads = []

    for i, line in enumerate(contacts):
        if '###' in format:
            chunks = line.split('###')
            if len(chunks) != 2:
                logging.error(f"Skipping the line '{line}' as it has invalid format")
                continue

            company = chunks[0]
            url = chunks[1]
        elif line.startswith('http'):
            company = 'NOT_AVAILABLE'
            url = line
        else:
            logging.warning(f'Unsupported line format: {line}, skipping it')
            continue

        while len(scraper_threads) >= threads_limit:
            for thread in scraper_threads.copy():
                thread.join(timeout=10)
                scraper_threads.remove(thread)

        scraper_thread = Thread(target=scraper.find_email, args=(company, url))
        scraper_threads.append(scraper_thread)
        logging.info(f'Collecting emails from {company} [{i + 1}/{len(contacts)}]')
        scraper_thread.start()

    for thread in scraper_threads:
        thread.join(30)


contacts = parse_contacts_files(dataset_dir=options.dataset_dir)

run_email_harvesting(contacts=contacts, threads_limit=options.threads, format=options.format)

logging.info(f'All jobs have finished with {len(read_captures_emails())} emails')
