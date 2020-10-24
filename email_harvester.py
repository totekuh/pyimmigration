#!/usr/bin/env python3
import glob
import logging
import os
from threading import Thread, Lock, Event

import urllib3

urllib3.disable_warnings()

import requests
from email_scraper import scrape_emails

global_lock = Lock()

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
    parser.add_argument('--url',
                        dest='url',
                        required=False,
                        help='Specify an URL to scrape the emails from')
    parser.add_argument('--dataset-dir',
                        dest='dataset_dir',
                        required=False,
                        help='Specify a dataset directory from the pyapplicant script to collect the emails. ')
    parser.add_argument('--dataset-file',
                        dest='dataset_file',
                        required=False,
                        help='Specify a dataset file for the email harvesting. '
                             'The script uses the --dataset-dir by default. ')
    parser.add_argument('--threads',
                        dest='threads',
                        required=False,
                        default=DEFAULT_THREADS_LIMIT,
                        type=int,
                        help='Specify a number of threads for the email harvesting. '
                             f'Default is {DEFAULT_THREADS_LIMIT}')
    options = parser.parse_args()

    if not options.url:
        if options.dataset_dir and options.dataset_file:
            parser.error("You can't use both --dataset-dir and --dataset-file "
                         "arguments in the same time.")

        if not options.dataset_dir and not options.dataset_file:
            logging.info("Neither --dataset-dir nor --dataset-file have been provided. "
                         f"Falling back to the default --dataset-dir {DATASET_DIR} argument.")
            options.dataset_dir = DATASET_DIR

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
        while global_lock.locked():
            pass
        global_lock.acquire()

        with open(self.output_file, 'a') as f:
            logging.info(f'Storing a new email: {email}')
            f.write(f'{email}{os.linesep}')
        global_lock.release()


def parse_contacts_dataset_file(dataset_file):
    contacts = set()
    with open(dataset_file, 'r') as f:
        for line in f.readlines():
            contacts.add(line.strip())
    logging.info(f'{len(contacts)} URLs have been passed for email harvesting')
    return contacts


def parse_contacts_dataset_dir(dataset_dir):
    contact_files = glob.glob(f'{dataset_dir}/*/{CONTACTS_FILE_PATTERN}')
    contacts = set()
    for file in contact_files:
        with open(file, 'r') as contact_file:
            for line in contact_file.readlines():
                contacts.add(line.strip())
    logging.info(f'{len(contacts)} URLs have been passed for email harvesting')
    return contacts


def run_email_harvesting(contacts, threads_limit):
    scraper = EmailScraper()

    event = Event()
    scraper_threads = []

    for i, line in enumerate(contacts):
        if '###' in line:
            chunks = line.split('###')
            if len(chunks) != 2:
                logging.error(f"Skipping the line '{line}' as it has invalid format")
                continue

            company = chunks[0]
            url = chunks[1]
        elif line.startswith('http'):
            company = line
            url = line
        else:
            logging.warning(f'Unsupported line format: {line}')
            continue

        while len(scraper_threads) >= threads_limit:
            for thread in scraper_threads.copy():
                if not thread.is_alive():
                    scraper_threads.remove(thread)

        scraper_thread = Thread(target=scraper.find_email, args=(company, url))
        scraper_threads.append(scraper_thread)
        logging.info(f'Collecting emails from {company} [{i + 1}/{len(contacts)}]')
        scraper_thread.start()

    for thread in scraper_threads:
        thread.join(30)
        event.set()
        thread.join()


if options.url:
    contacts = [options.url]
elif options.dataset_dir:
    contacts = parse_contacts_dataset_dir(dataset_dir=options.dataset_dir)
else:
    contacts = parse_contacts_dataset_file(dataset_file=options.dataset_file)

run_email_harvesting(contacts=contacts, threads_limit=options.threads)

logging.info(f'All jobs have finished with {len(read_captures_emails())} emails')
