#!/usr/bin/env python3
from time import sleep
import os
import requests
import bs4
import logging

logging.basicConfig(format='[%(asctime)s %(levelname)s]: %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p',
                    level='INFO')

DEFAULT_SEARCH_FILE = 'search.txt'
DEFAULT_OUTPUT_FILE = 'links.txt'


def get_arguments():
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('--search',
                        dest='search',
                        required=False,
                        default=DEFAULT_SEARCH_FILE,
                        type=str,
                        help='Specify your search query for Google. '
                             'It can be a string or a file name with a new-line separated list of keywords. '
                             f'Default file name is {DEFAULT_SEARCH_FILE}')
    parser.add_argument('--output',
                        dest='output',
                        required=False,
                        default=DEFAULT_OUTPUT_FILE,
                        type=str,
                        help='Specify an output file to capture the links. '
                             f'Default is {DEFAULT_OUTPUT_FILE}')

    options = parser.parse_args()
    return options


options = get_arguments()


def scrape(keyword, output_file):
    # Google Search URL
    url = "https://google.co.in/search"

    logging.info(f"Starting Google scraping for '{keyword}'")
    # Gets response from the server for the search query
    response = requests.get(url=url, params=[('q', keyword)])

    links = set()

    def get_next_page_url(html):
        soup = bs4.BeautifulSoup(html, 'lxml')
        tag = soup.find('a', {'aria-label': 'Nächste Seite'})
        if hasattr(tag, 'attrs') and 'href' in tag.attrs:
            href = tag.attrs['href']
            return f"https://google.co.in{href}"

    def get_links(html):
        soup = bs4.BeautifulSoup(html, 'lxml')

        new_links = set()
        for tag in soup.find_all('a', href=True):
            if hasattr(tag, 'attrs') and 'href' in tag.attrs:
                href = tag.attrs['href']
                if href.startswith('/url?q=') \
                        and 'accounts.google.com' not in href:
                    fixed_href = href.lstrip('/url?q=')
                    logging.info(f"Harvesting a new link - {fixed_href}")
                    new_links.add(fixed_href)
        if new_links:
            logging.info(f'{len(new_links)} links have been extracted from the page')
            with open(output_file, 'a', encoding='utf-8') as f:
                for link in new_links:
                    f.write(link.strip())
                    f.write(os.linesep)
        return new_links

    html = response.text
    new_links = get_links(html)
    for link in new_links:
        links.add(link)

    while True:
        next_page_url = get_next_page_url(html)
        if next_page_url:
            logging.info("Processing a new page with links")
            next_page = requests.get(next_page_url)
            html = next_page.text
            new_links = get_links(html)
            for link in new_links:
                links.add(link)

            logging.info("Sleeping for 5 seconds")
            sleep(5)
        else:
            logging.error("Couldn't find the next page URL")
            break
    logging.info(f"Finished scraping '{keyword}'")


if os.path.exists(options.search):
    with open(options.search, 'r') as f:
        search = [line.strip() for line in f.readlines() if line.strip()]
else:
    search = [options.search]

for query in search:
    scrape(keyword=query, output_file=options.output)
