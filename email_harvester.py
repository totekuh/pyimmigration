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
sleep_timer_in_seconds = 10

# we don't need it
EMAIL_BLACKLIST = ['noreply@indeed.com', '@sentry.indeed.com']


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

        try:
            resp = requests.get(url)
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
finished_jobs_count = 0

scraper = EmailScraper()
for line in contacts:
    company = line.split('###')[0]
    url = line.split('###')[1]
    logging.info(f'Collecting emails from {company} [{finished_jobs_count}/{all_jobs_count}]')
    scraper.find_email(company, url)
    finished_jobs_count += 1

logging.info(f'All jobs have finished with {len(read_captures_emails())} emails')
