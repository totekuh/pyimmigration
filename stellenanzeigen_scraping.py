#!/usr/bin/env python3
import os

import requests
from bs4 import BeautifulSoup as bs

DEFAULT_OUTPUT_FILE = 'links.txt'
DEFAULT_LIMIT = 200


def get_arguments():
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('--search',
                        dest='search',
                        required=True,
                        help='The keywords to use while searching')
    parser.add_argument('--limit',
                        dest='limit',
                        required=False,
                        default=DEFAULT_LIMIT,
                        type=int,
                        help='Limit results to the given number.')
    parser.add_argument('--output',
                        dest='output',
                        required=False,
                        default=DEFAULT_OUTPUT_FILE,
                        help='The output file. '
                             f'Default is {DEFAULT_OUTPUT_FILE}')
    return parser.parse_args()


class StellenanzeigenCrawler:
    def __init__(self, output_file=DEFAULT_OUTPUT_FILE):
        self.output_file = output_file

    def _extract_jobs_from_page(self, html):
        soup = bs(html, 'html.parser')
        links = set()
        for tag in soup.find_all('a', {'class': 'position-link'}):
            if hasattr(tag, 'attrs') and tag.attrs['href']:
                links.add(tag.attrs['href'])
        if links:
            print(f'{len(links)} links have been collected')
        return links

    def _go_next_page(self, html):
        pass

    def search_jobs(self, query, radius=200):
        print(f"Searching for '{query}' on the stellenanzeigen.de domain")
        # GET
        # 	https://www.stellenanzeigen.de/suche/?voll=Englisch Lehrer&radius=30
        try:
            resp = requests.get(f"https://www.stellenanzeigen.de/suche/",
                                params={
                                    'voll': query,
                                    'radius': radius
                                })

            if resp.ok:
                links = set()

                new_links = self._extract_jobs_from_page(resp.text)
                if new_links:
                    for link in new_links:
                        links.add(link)

                # not implemented yet

                # while self._go_next_page(resp.text):
                #     new_links = self._extract_jobs_from_page(resp.text)
                #     if new_links:
                #         for link in new_links:
                #             links.add(link)
                #     else:
                #         print("Didn't find any new links")
                #         break
                if links:
                    print(f'{len(links)} URLs have been extracted in total')
                    with open(self.output_file, 'a') as f:
                        for link in links:
                            f.write(link)
                            f.write(os.linesep)
                else:
                    print("The crawler has failed to find anything")
                    exit(1)


            else:
                print(f"Unexpected status code: {resp.status_code}")
                exit(1)
        except Exception as e:
            print(f'Failed to open a page with jobs: {e}')
            exit(1)


options = get_arguments()
query = options.search
stellenanzeigen_scraper = StellenanzeigenCrawler(output_file=options.output)

stellenanzeigen_scraper.search_jobs(query, radius=options.limit)
