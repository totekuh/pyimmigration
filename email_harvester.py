#!/usr/bin/env python3
import glob
import logging
import os
from threading import Thread
from time import sleep

import requests
from email_scraper import scrape_emails

logging.basicConfig(format='[%(asctime)s %(levelname)s]: %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p',
                    level='INFO')
DATASET_DIR = 'dataset'
HARVEST_FILE = 'harvest.txt'
threads_limit = 50
scraper_threads = []
sleep_timer_in_seconds = 5

# we don't need it
EMAIL_BLACKLIST = ['noreply@indeed.com', '@sentry.indeed.com']


def read_captures_emails(harvest_file=HARVEST_FILE):
    if os.path.exists(harvest_file):
        with open(HARVEST_FILE, 'r') as f:
            return [email.strip() for email in f.readlines()]
    else:
        return []


class EmailScraper:
    def __init__(self, line, file=HARVEST_FILE):
        self.company = line.split('###')[0]
        self.url = line.split('###')[1]
        self.output_file = file
        self.thread = Thread(target=self.find_email, args=())

    def start(self):
        self.thread.start()

    def is_alive(self):
        return self.thread.isAlive()

    def find_email(self):
        logging.info(f'Collecting emails from {self.company}')
        try:
            resp = requests.get(self.url)
            if resp.ok:
                emails = scrape_emails(resp.text)
                if emails:
                    for email in emails:
                        if not any(junk in email for junk in EMAIL_BLACKLIST) and email not in read_captures_emails():
                            self.save_email(email)
            else:
                logging.warning(f'{self.company} has returned unexpected status code: {resp.status_code}')
        except Exception as e:
            logging.error(e)

    def save_email(self, email):
        with open(self.output_file, 'a') as f:
            f.write(email)
            f.write('\n')


def create_scrapers_threads(dataset_dir, output_file):
    contact_files = glob.glob(f'{dataset_dir}/*/*.txt')
    contacts = set()
    for file in contact_files:
        with open(file, 'r') as contact_file:
            for line in contact_file.readlines():
                contacts.add(line.strip())
    scrapers = [EmailScraper(line, file=output_file) for line in contacts]
    logging.info(f'{len(scrapers)} scrapers have been created for email harvesting')
    return scrapers


scrapers = create_scrapers_threads(dataset_dir=DATASET_DIR, output_file=HARVEST_FILE)
all_jobs_count = len(scrapers)
running_scrapers = []

while len(scrapers) != 0:
    for scraper in scrapers.copy():
        if len(running_scrapers) >= threads_limit:
            logging.info(f'Running jobs: {len(running_scrapers)}; '
                         f'remaining jobs: {len(scrapers)}; '
                         f'all jobs: {all_jobs_count}; '
                         f'sleeping for {sleep_timer_in_seconds} seconds')
            sleep(sleep_timer_in_seconds)
        for running_scraper in running_scrapers.copy():
            if not running_scraper.is_alive():
                running_scrapers.remove(running_scraper)
        try:
            scraper.start()
            running_scrapers.append(scraper)
            scrapers.remove(scraper)
        except Exception as e:
            logging.error(e)

while any(scraper.is_alive() for scraper in running_scrapers):
    sleep(sleep_timer_in_seconds)

logging.info(f'All scrapers have finished with {len(read_captures_emails())} emails')
