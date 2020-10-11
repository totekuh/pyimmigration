#!/usr/bin/env python3
import json
from threading import Thread
import logging
from os import linesep
from pathlib import Path
import json
import requests
from bs4 import BeautifulSoup as bs
from requests_html import HTMLSession, HTML

DEFAULT_DAYS_SINCE_PUBLISHED = 5
DEFAULT_LOGGING_LEVEL = 'INFO'
PUBLISHER_ID_FILE = 'publisher_id.txt'
API_RESULTS_LIMIT = 1000
DATASET_DIR = Path("dataset")
DATASET_DIR.mkdir(exist_ok=True)
JOB_TYPES = ['fulltime', 'parttime', 'contract', 'internship', 'temporary', 'all']

with open(PUBLISHER_ID_FILE, 'r', encoding='utf-8') as f:
    PUBLISHER_ID = f.read().strip()


def get_arguments():
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('--indeed',
                        action='store_true',
                        required=False,
                        help='Start the Indeed web crawler. '
                             'The crawler will use the publisher ID to search various'
                             'jobs for you. '
                             'The job keywords must be specified with the --search flag.')
    parser.add_argument('--stepstone',
                        action='store_true',
                        required=False,
                        help='Start the Stepstone web crawler. '
                             'Pretty much the same thing as the indeed web crawler '
                             'but scrapes stepstone.de instead')
    parser.add_argument('--search',
                        dest='search',
                        required=True,
                        help='The keywords to use while searching')
    parser.add_argument('--country',
                        dest='country',
                        default='us',
                        required=False,
                        help='A value or a comma-separated list of countries to use while searching the jobs. '
                             'Default is "us"')
    parser.add_argument('--days',
                        dest='days',
                        default=DEFAULT_DAYS_SINCE_PUBLISHED,
                        type=int,
                        required=False,
                        help=f"Days since published. Default is '{DEFAULT_DAYS_SINCE_PUBLISHED}'")
    parser.add_argument('--job-type',
                        dest='job_type',
                        required=False,
                        default='fulltime',
                        choices=JOB_TYPES,
                        help='Search by a specific job type. Use "all" to search for the all job types. '
                             "Default is 'fulltime'")
    parser.add_argument('--limit',
                        dest='limit',
                        required=False,
                        type=int,
                        help='Limit results to the given number.')
    parser.add_argument('-l',
                        '--logging',
                        dest='logging',
                        default=DEFAULT_LOGGING_LEVEL,
                        choices=["ERROR", "WARNING", "INFO", "DEBUG"],
                        required=False,
                        help=f"Logging level. Default is {DEFAULT_LOGGING_LEVEL}")
    return parser.parse_args()


class Job:
    def __init__(self, company, url):
        self.company = company
        self.url = url


class StepstoneCrawler:
    def __init__(self, limit=None):
        self.jobs = []
        self.session = HTMLSession()
        self.limit = limit

    def get_company_information(self, job_link, extracted_jobs):
        try:
            logging.debug(f"Extracting information about the company from '{job_link}'")
            resp = requests.get(job_link, headers={
                'User-Agent': 'Your Mom'
            })
            company_document = HTML(html=resp.text)

            # get the company name
            company_name = ''
            for tag in company_document.find('div'):
                for attr in tag.attrs:
                    if attr == 'data-replyone':
                        data = json.loads(tag.attrs[attr])
                        company_name = data['companyName']
            if not company_name:
                company_name = 'NOT_AVAILABLE'

            # get the company URL
            company_url = ''
            for tag in company_document.find('a'):
                if 'href' in tag.attrs and \
                        'target' in tag.attrs and \
                        'rel' in tag.attrs:
                    if tag.full_text.strip() and \
                            not tag.full_text.strip() == 'Geben Sie uns Feedback' and \
                            '.de' in tag.full_text:
                        if not tag.full_text.startswith('https'):
                            company_url = f'https://{tag.full_text.strip()}'
                        else:
                            company_url = tag.full_text.strip()
            if not company_url:
                logging.warning(f"Failed to extract the company URL from '{company_name}'")
            else:
                logging.info(f"Storing '{company_name}' - '{company_url}' for the email harvesting")
                extracted_jobs.append(Job(company=company_name, url=company_url))

        except Exception as e:
            logging.error(f"Failed to extract the company information from {job_link} - {e}")

    def extract_jobs(self, html):
        extracted_jobs = []
        document = HTML(html=html)

        # for each vacancy we have to visit the job URL and extract the company URL and the company name
        base_url = 'https://www.stepstone.de'
        extracted_links = []
        for link in document.links:
            if not link.startswith('http'):
                absolute_link = f"{base_url}{link}"
            elif link.startswith(base_url):
                absolute_link = link
            else:
                continue
            if 'stellenangebote' in absolute_link:
                extracted_links.append(absolute_link)
        logging.info(f"{len(extracted_links)} links have been extracted")

        threads_limit = 50
        scraper_threads = []
        for link in extracted_links:
            while len(scraper_threads) > threads_limit:
                for thread in scraper_threads.copy():
                    if not thread.is_alive():
                        scraper_threads.remove(thread)

            thread = Thread(target=self.get_company_information, args=(link, extracted_jobs))
            scraper_threads.append(thread)
            thread.start()

        while any(thread.is_alive() for thread in scraper_threads):
            pass

        return extracted_jobs

    def get_next_page_url(self, html):
        soup = bs(html, 'html.parser')

        next_page_button = soup.find('a', attrs={'title': "Nächste"})
        if hasattr(next_page_button, 'attrs') and 'href' in next_page_button.attrs:
            href = next_page_button.attrs['href']
            return href

    def search_jobs(self,
                    url,
                    start=0):
        country_dir = DATASET_DIR / country
        if start == 0:
            country_dir.mkdir(exist_ok=True)

        logging.info(f"Searching for '{query}' on the stepstone.de domain; "
                     f"jobs found in total: [{len(self.jobs)}]")
        try:
            resp = self.session.get(url)
            resp.html.render()
            if resp.ok:
                html = resp.text
                jobs = self.extract_jobs(html)
                if jobs:
                    for job in jobs:
                        self.jobs.append(job)

                    if len(self.jobs) > self.limit:
                        logging.info('Stopping the scraper as the jobs limit has been exceeded')
                        self.dump_results(country_dir, query)
                        return
                    next_page_url = self.get_next_page_url(html)
                    if next_page_url:
                        self.search_jobs(url=next_page_url)
                    elif self.jobs:
                        logging.info(f"Done parsing {query}; {len(self.jobs)} jobs found")
                        self.dump_results(country_dir, query)
                else:
                    if self.jobs:
                        logging.info(f"Done parsing {query}; {len(self.jobs)} jobs found")
                        self.dump_results(country_dir, query)
                    else:
                        logging.warning('Failed to find any jobs. '
                                        'You should check the DEBUG log for the page content.')
                        logging.debug(html)

            else:
                logging.debug(resp.status_code)
                logging.debug(resp.text)
        except KeyboardInterrupt:
            logging.warning("Jobs searching has been interrupted")
            self.dump_results(country_dir, query)
        except Exception as e:
            logging.error(e)

    def dump_results(self, country_dir, search_query):
        # name###url
        companies = [f"{job.company.replace('.', '').replace(',', '').strip()}###{job.url}"
                     for job in self.jobs]
        contacts_file_name = country_dir / f'{search_query.replace(" ", "_")}_contacts.txt'
        with open(contacts_file_name, 'a') as companies_f:
            companies_f.write(linesep.join(companies))
        logging.info(f"Saved {len(companies)} companies and their URLs to {contacts_file_name}")


class IndeedCrawler:

    # The job key is an identifier of a job
    # you should use the job API to search for the jobs and
    # the 'Get Job API' to get information about the specific job
    def __init__(self, publisher_id):
        self.publisher_id = publisher_id
        self.user_agent = 'Mozilla Firefox'
        self.user_ip = '127.0.0.1'
        self.job_types = ['fulltime', 'parttime', 'contract', 'internship', 'temporary']
        self.search_results = []

    def search_jobs(self,
                    query,
                    city='',
                    country='',
                    start=0,
                    results_per_page=25,
                    job_type='fulltime',
                    days_since_published=10):
        # https://opensource.indeedeng.io/api-documentation/docs/job-search/
        country_dir = DATASET_DIR / country
        if start == 0:
            self.search_results = []
            self.companies = set()
            country_dir.mkdir(exist_ok=True)
        url = (
            f'http://api.indeed.com/ads/apisearch?publisher={self.publisher_id}&'
            f'q={query}&'
            'format=json&'
            f'l={city}&'
            'sort=&'
            'radius=&'
            'st=&'
            f'jt={job_type}&'
            f'start={start}&'
            f'limit={results_per_page}&'
            f'fromage={days_since_published}&'
            'filter=&'
            'latlong=1&'
            f'co={country}&'
            'chnl=&'
            f'userip={self.user_ip}&'
            f'useragent={self.user_agent}&'
            'v=2'
        )

        try:
            resp = requests.get(url)
            if resp.ok:
                job_data = resp.json()
                last_result = job_data['end']
                total_results = job_data['totalResults']
                logging.info(
                    f'Searching jobs: {query}; '
                    f'job type: {job_type}; '
                    f'country: {country}; '
                    f'days since published: {days_since_published} '
                    f'[{start}-{start + results_per_page} / '
                    f'{total_results}]')
                self.search_results += job_data['results']

                # extract all companies
                for job in job_data['results']:
                    try:
                        normalized_company_name = job['company'].replace('.', '').replace(',', '')
                        self.companies.add(normalized_company_name)
                    except Exception as e:
                        logging.error(e)
                        continue

                if last_result == API_RESULTS_LIMIT + results_per_page:
                    logging.warning(f"Reached {last_result} which is the API limit (bug?)")
                    self.dump_results(country_dir, query)

                elif last_result == total_results:
                    logging.info(f"Done parsing {query}.")
                    self.dump_results(country_dir, query)

                else:
                    self.search_jobs(query,
                                     city=city,
                                     country=country,
                                     start=start + results_per_page,
                                     job_type=job_type,
                                     days_since_published=days_since_published)

            else:
                logging.warning('Search jobs API has responded with unsuccessful status code')
                logging.debug(resp.status_code)
                logging.debug(resp.text)
        except KeyboardInterrupt:
            logging.warning("Job searching has been interrupted")
            self.dump_results(country_dir, query)
        except Exception as e:
            logging.error(e)

    def get_jobs(self, job_keys):
        if ',' in job_keys:
            job_keys = ','.join(job_keys)
            logging.info(f'Getting jobs with job_keys: {job_keys}')
        else:
            logging.info(f'Getting a job with job_key: {job_keys}')
        url = (
            f'http://api.indeed.com/ads/apigetjobs?publisher={self.publisher_id}&'
            f'jobkeys={job_keys}&'
            f'v=2'
        )

        try:
            resp = requests.get(url)
            if resp.ok:
                logging.info('Job details have been collected')
                return resp.json()
            else:
                logging.warning('Get jobs API has responded with unsuccessful status code')
                logging.debug(resp.status_code)
                logging.debug(resp.text)
        except Exception as e:
            logging.error(e)

    def dump_results(self, country_dir, query):
        # save the results as is
        jobs_save_path = country_dir / f"{query.replace(' ', '_')}.json"
        with open(jobs_save_path, "a") as json_f:
            json.dump(self.search_results, json_f)
        logging.info(f"Saved {len(self.search_results)} jobs to {jobs_save_path}")

        # now, save the companies and their URLs in a separate file
        companies = [f"{job_as_json['company'].replace('.', '').replace(',', '').strip()}###{job_as_json['url']}"
                     for job_as_json in self.search_results]
        contacts_save_path = country_dir / f'{query.replace(" ", "_")}_contacts.txt'
        with open(contacts_save_path, 'a') as companies_f:
            companies_f.write(linesep.join(companies))
        logging.info(f"Saved {len(self.companies)} companies and their URLs to {contacts_save_path}")


if __name__ == "__main__":
    options = get_arguments()
    logging.basicConfig(format='[%(asctime)s %(levelname)s]: %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p',
                        level=options.logging)

    search = options.search
    if Path(search).exists():
        with open(Path(search), 'r') as queries_f:
            search = list(q.strip() for q in queries_f if q.strip())
    else:
        search = [search]

    job_type = options.job_type
    if job_type == 'all':
        job_type = [t for t in JOB_TYPES if t != 'all']
    else:
        job_type = [job_type]

    if options.indeed:
        indeed_crawler = IndeedCrawler(publisher_id=PUBLISHER_ID)
        if ',' not in options.country:
            countries = [options.country]
        else:
            countries = options.country.split(',')
        for query in search:
            for country in countries:
                for t in job_type:
                    indeed_crawler.search_jobs(query,
                                               country=country,
                                               days_since_published=options.days,
                                               job_type=t)
    elif options.stepstone:
        country = options.country
        if country and country != 'de':
            raise Exception(f"'de' is the only valid country for the Stepstone crawler")
        else:
            stepstone_scraper = StepstoneCrawler(limit=options.limit)
            for query in search:
                stepstone_scraper.jobs = []
                stepstone_scraper.search_jobs(
                    url=(
                        'https://www.stepstone.de/5/ergebnisliste.html?'
                        'stf=freeText&'
                        'ns=1&'
                        'qs=%5B%7B%22id%22%3A%22300000115%22%2C%22description%22%3A%22Deutschland%22%2C%22type%22%3A%22geocity%22%7D%5D&'
                        'companyID=0&'
                        'cityID=300000115&'
                        'sourceOfTheSearchField=homepagemex%3Ageneral&searchOrigin=Homepage_top-search&'
                        f'ke={query}&'
                        f'ws=Deutschland&'
                        f'ra=100'
                    )
                )
