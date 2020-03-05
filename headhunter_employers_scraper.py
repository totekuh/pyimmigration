#!/usr/bin/env python3
import json
import logging
import os

from requests import Session
from threading import Thread
logging.basicConfig(format='[%(asctime)s %(levelname)s]: %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p',
                    level='INFO')

DEFAULT_STORED_EMPLOYERS_FILE = 'employers.json'
DEFAULT_THREADS_LIMIT = 5

def get_arguments():
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('--start-id',
                        dest='start_id',
                        default=1,
                        type=int,
                        required=False,
                        help='Specify an id to start the scraper from. '
                             'Default is 1')
    parser.add_argument('--end-id',
                        dest='end_id',
                        default=60000000,
                        type=int,
                        required=False,
                        help='Specify an id where the scraper should stop. '
                             'Default is 60000000')
    parser.add_argument('--threads',
                        dest='threads',
                        default=DEFAULT_THREADS_LIMIT,
                        type=int,
                        required=False,
                        help='Specify a number of threads for the email harvesting. '
                             f'Default is {DEFAULT_THREADS_LIMIT}')
    options = parser.parse_args()

    return options


class HeadHunterScraper:
    def __init__(self, stored_employers_file=DEFAULT_STORED_EMPLOYERS_FILE):
        self.stored_employers_file = stored_employers_file
        self.base_url = 'https://api.hh.ru'
        self.session = Session()

    def scrape_employer(self, id):
        try:
            hh_url = f'{self.base_url}/employers/{id}'
            resp = self.session.get(hh_url, headers={
                'User-Agent': 'Your Mom'
            })
            status_code = resp.status_code
            if status_code == 200:
                employer_json = resp.json()
                self.save_employer(employer_json)
                return employer_json
            elif status_code == 404:
                return
            else:
                logging.warning(f'api.hh.ru service has returned unexpected status code: {status_code}')
        except Exception as e:
            logging.error(e)

    def save_employer(self, employer_json):
        stored_employers = self.read_stored_employers()
        for stored_employer in stored_employers:
            if employer_json['id'] == stored_employer['id']:
                # already stored
                return
        stored_employers.append(employer_json)
        logging.info(f'Saving a new employer with id: {employer_json["id"]}')
        with open(self.stored_employers_file, 'a', encoding='utf-8') as f:
            json.dump(employer_json, f, ensure_ascii=False)
            f.write(os.linesep)

    def read_stored_employers(self):
        stored_employers = []
        if os.path.exists(self.stored_employers_file):
            with open(self.stored_employers_file, 'r', encoding='utf-8') as f:
                for line in [l.strip() for l in f.readlines()]:
                    stored_employers.append(json.loads(line))
        return stored_employers


def start_hh_employers_scraper(start_id, end_id, threads_limit):
    hh_scraper = HeadHunterScraper()

    scraper_threads = []

    for id in range(start_id, end_id):
        while len(scraper_threads) >= threads_limit:
            for thread in scraper_threads.copy():
                if not thread.is_alive():
                    scraper_threads.remove(thread)

        scraper_thread = Thread(target=hh_scraper.scrape_employer, args=(id,))
        scraper_threads.append(scraper_thread)
        scraper_thread.start()
    while any(thread.is_alive() for thread in scraper_threads):
        pass


options = get_arguments()

start_id = options.start_id
end_id = options.end_id

start_hh_employers_scraper(start_id, end_id, options.threads)
