#!/usr/bin/env python3
import json
import logging
import random
import string
from pathlib import Path

import requests

DEFAULT_LOGGING_LEVEL = 'INFO'
PUBLISHER_ID_FILE = 'publisher_id.txt'
API_RESULTS_LIMIT = 1000
DATASET_DIR = Path("dataset")
DATASET_DIR.mkdir(exist_ok=True)

with open(PUBLISHER_ID_FILE, 'r', encoding='utf-8') as f:
    PUBLISHER_ID = f.read().strip()


def get_arguments():
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('--indeed',
                        action='store_true',
                        required=False,
                        help='Invoke the Indeed web crawler. '
                             'The crawler will use stored publisher ID to search the '
                             'jobs for you. '
                             'The job keywords to search for must be specified with --search flag.')
    parser.add_argument('--search',
                        dest='search',
                        required=True,
                        help='Keywords to search within crawler web sites or API\'s.')
    parser.add_argument('--country',
                        dest='country',
                        default='us',
                        required=False,
                        help='A value of a comma-separated list of countries to use while searching the jobs. '
                             'Default is "us"')
    parser.add_argument('-l',
                        '--logging',
                        dest='logging',
                        default=DEFAULT_LOGGING_LEVEL,
                        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"],
                        required=False,
                        help='Logging level. Default is ' + DEFAULT_LOGGING_LEVEL)
    return parser.parse_args()


class IndeedCrawler:

    # job key is an identifier of a job
    # you should use job API to search the jobs and Get Job API to get information about the specific job
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
            'jt=&'
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
                    self.search_jobs(query, city, country, start + results_per_page)

            else:
                logging.warning('Search jobs API has responded with unsuccessful status code')
                logging.debug(resp.status_code)
                logging.debug(resp.text)
        except KeyboardInterrupt:
            logging.warning("Search interrupted. Dumping current results.")
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
        with open(jobs_save_path, "w") as json_f:
            json.dump(self.search_results, json_f)
        logging.info(f"Saved {len(self.search_results)} jobs to {jobs_save_path}")

        # now, save the companies and their URLs in a separate file
        companies = [f"{job_as_json['company'].replace('.', '').replace(',', '').strip()}###{job_as_json['url']}"
                     for job_as_json in self.search_results]
        contacts_save_path = country_dir / f'{query.replace(" ", "_")}_contacts.txt'
        with open(contacts_save_path, 'w') as companies_f:
            companies_f.write("\n".join(companies))
        logging.info(f"Saved {len(self.companies)} companies and their URLs to {contacts_save_path}")


# too complicated
class LinkedInCrawler:
    @staticmethod
    def get_random_string(length=10):
        # Generate a random string of fixed length
        letters = string.ascii_lowercase
        return ''.join(random.choice(letters) for i in range(length))

    def __init__(self):
        self.client_id = '123'
        self.client_secret = '123'
        self.redirect_url = 'http://localhost:8080'
        self.state = self.get_random_string()

    # https://docs.microsoft.com/en-us/linkedin/shared/authentication/authorization-code-flow?context=linkedin/context
    def get_linkedin_authorization_code(self,
                                        client_id,
                                        redirect_url,
                                        state,
                                        response_type='code',
                                        scope='r_liteprofile%20r_emailaddress%20w_member_social'):
        authorization_code_url = 'https://www.linkedin.com/oauth/v2/authorization?' \
            f'response_type={response_type}&' \
            f'client_id={client_id}&' \
            f'redirect_uri={redirect_url}' \
            f'&state={state}&' \
            f'scope={scope}'
        try:
            print(authorization_code_url)
            resp = requests.get(authorization_code_url)
            if resp.status_code == 200:
                logging.info('Authorization code received')
                print(resp.text)
                return resp.text
            else:
                logging.warning('Failed to obtain authorization code')
                print(resp.status_code, resp.json())
        except Exception as e:
            logging.error(e)

    def get_linkedin_access_token(self,
                                  client_id,
                                  client_secret,
                                  redirect_url,
                                  authorization_code,
                                  grant_type='authorization_code'):
        access_token_url = 'https://www.linkedin.com/oauth/v2/accessToken'
        post_data = f'grant_type={grant_type}&' \
            f'code={authorization_code}&' \
            f'client_id={client_id}&' \
            f'client_secret={client_secret}&' \
            f'redirect_uri={redirect_url}'
        try:
            resp = requests.post(access_token_url, data=post_data, headers={
                'Content-Type': 'application/x-www-form-urlencoded'
            })
            if resp.status_code == 200:
                logging.info('Access token received')
                resp_body = resp.json()
                return resp_body
            else:
                logging.warning('Failed to obtain access token')
                logging.debug(resp.status_code, resp.json())
        except Exception as e:
            logging.error(e)


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

    if options.indeed:
        indeed_crawler = IndeedCrawler(publisher_id=PUBLISHER_ID)
        if ',' not in options.country:
            countries = [options.country]
        else:
            countries = options.country.split(',')
        for query in search:
            for country in countries:
                indeed_crawler.search_jobs(query, country=country)
