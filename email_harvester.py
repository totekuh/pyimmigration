#!/usr/bin/env python3
import glob
import logging

import requests
from email_scraper import scrape_emails

logging.basicConfig(format='[%(asctime)s %(levelname)s]: %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p',
                    level='INFO')

DATASET_DIR = 'dataset'
HARVEST_FILE = 'harvest.txt'

# we don't need it
EMAIL_BLACKLIST = ['noreply@indeed.com', '@sentry.indeed.com']


def dump_results(emails):
    with open(HARVEST_FILE, 'a') as f:
        f.write('\n'.join(emails))
    logging.info(f'{len(emails)} emails have been saved into {HARVEST_FILE}')


class Contact:
    def __init__(self, line):
        self.company = line.split('###')[0]
        self.url = line.split('###')[1]

    def find_email(self):
        try:
            resp = requests.get(self.url)
            if resp.ok:
                emails = scrape_emails(resp.text)
                if emails:
                    return emails
            else:
                logging.warning(f'{self.company} has returned unexpected status code: {resp.status_code}')
        except Exception as e:
            logging.error(e)


def parse_contact_files(dataset_dir=DATASET_DIR):
    contact_files = glob.glob(f'{dataset_dir}/*/*.txt')
    raw_contacts = set()
    for file in contact_files:
        with open(file, 'r') as contact_file:
            for line in contact_file.readlines():
                raw_contacts.add(line.strip())
    contacts = [Contact(line) for line in raw_contacts]
    logging.info(f'{len(contacts)} contacts have been collected for email harvesting')
    return contacts


contacts = parse_contact_files()
emails = set()
for i, contact in enumerate(contacts):
    logging.info(f'Collecting emails from {contact.company} {i}/{len(contacts)}')
    harvest = contact.find_email()
    if harvest:
        for email in harvest:
            if not any(junk in email for junk in EMAIL_BLACKLIST):
                emails.add(email)
if emails:
    dump_results(emails)
