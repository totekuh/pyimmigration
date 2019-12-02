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
sleep_timer_in_seconds = 1

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
        global all_jobs_count
        global contacts
        global running_scrapers
        logging.info(f'Collecting emails from {self.company} '
                     f'running: {len(running_scrapers)}; finished: {len(contacts)}; remaining: {all_jobs_count}')
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


def parse_contacts_files(dataset_dir):
    contact_files = glob.glob(f'{dataset_dir}/*/*.txt')
    contacts = set()
    for file in contact_files:
        with open(file, 'r') as contact_file:
            for line in contact_file.readlines():
                contacts.add(line.strip())
    logging.info(f'{len(contacts)} URLs have been parsed for email harvesting')
    return contacts


contacts = parse_contacts_files(dataset_dir=DATASET_DIR)

all_jobs_count = len(contacts)
running_scrapers = []

while len(contacts) != 0:
    if len(running_scrapers) >= threads_limit:
        sleep(sleep_timer_in_seconds)
    for running_scraper in running_scrapers.copy():
        if not running_scraper.is_alive():
            running_scrapers.remove(running_scraper)
    for line in contacts.copy():
        try:
            scraper = EmailScraper(line)
            scraper.start()
            running_scrapers.append(scraper)
            contacts.remove(line)
        except Exception as e:
            logging.error(e)

while any(scraper.is_alive() for scraper in running_scrapers):
    sleep(sleep_timer_in_seconds)

logging.info(f'All scrapers have finished with {len(read_captures_emails())} emails')
