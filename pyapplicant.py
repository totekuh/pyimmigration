#!/usr/bin/env python3
import logging
import random
import string

import requests

DEFAULT_LOGGING_LEVEL = 'INFO'
PUBLISHER_ID = '7837020139926262'


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
                        required=False,
                        help='Keywords to search within crawler web sites or API\'s.')
    parser.add_argument('-l',
                        '--logging',
                        dest='logging',
                        default=DEFAULT_LOGGING_LEVEL,
                        required=False,
                        help='Logging level. Default is ' + DEFAULT_LOGGING_LEVEL)
    return parser.parse_args()


class IndeedCrawler:

    # job key is an identifier of a job
    # you should use job API to search the jobs and Get Job API to get information about the specific job
    def __init__(self, published_id):
        self.publisher_id = published_id
        self.user_agent = 'Mozilla Firefox'
        self.user_ip = '127.0.0.1'
        self.job_types = ['fulltime', 'parttime', 'contract', 'internship', 'temporary']

    def search_jobs(self,
                    search,
                    country='us'):
        # https://opensource.indeedeng.io/api-documentation/docs/job-search/
        logging.info(f'Collecting the jobs: {search}; country: {country}')
        url = f'http://api.indeed.com/ads/apisearch?publisher={self.publisher_id}&' \
            f'q={search}&' \
            'l=austin%2C+tx&' \
            'sort=&' \
            'radius=&' \
            'st=&' \
            'jt=&' \
            'start=&' \
            'limit=&' \
            'fromage=&' \
            'filter=&' \
            'latlong=1&' \
            f'co={country}&' \
            'chnl=&' \
            f'userip={self.user_ip}&' \
            f'useragent={self.user_agent}&' \
            'v=2'
        try:
            resp = requests.get(url)
            if resp.ok:
                logging.info('Jobs have been collected')
                print(resp.text)
            else:
                logging.warning('Jobs API has responded with unsuccessful status code')
                logging.debug(resp.status_code)
                logging.debug(resp.text)
        except Exception as e:
            logging.error(e)

    def get_job(self, job_key):
        logging.info(f'Getting a job, job_key: {job_key}')
        url = f'http://api.indeed.com/ads/apigetjobs?publisher={self.publisher_id}&' \
            f'jobkeys={job_key}&' \
            f'v=2'
        try:
            resp = requests.get(url)
            if resp.ok:
                logging.info('Job details have been collected')
                print(resp.text)
            else:
                logging.warning('Get a job API has responded with unsuccessful status code')
                logging.debug(resp.status_code)
                logging.debug(resp.text)
        except Exception as e:
            logging.error(e)


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


options = get_arguments()
logging.basicConfig(format='[%(asctime)s %(levelname)s]: %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p',
                    level=options.logging)

search = options.search
if not options.search:
    raise Exception('You have to give something to search. Use --help for more info.')

if options.indeed:
    indeed_crawler = IndeedCrawler(published_id=PUBLISHER_ID)
    indeed_crawler.search_jobs(search)
