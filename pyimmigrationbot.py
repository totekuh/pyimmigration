#!/usr/bin/env python3.7
import os
from threading import Thread
from time import sleep

PYTHON_INTERPRETER = 'python3'
USED_SEARCH_KEYWORD_FILE = 'search-keywords.txt'

import logging
from functools import wraps

from telegram import ParseMode
from telegram.ext import CommandHandler, Updater

from config import TOKEN, WHITELIST


def whitelist_only(func):
    @wraps(func)
    def wrapped(update, context, *args, **kwargs):
        user = update.effective_user
        logging.info(
            f"@{user.username} ({user.id}) is trying to access a privileged command"
        )
        if user.username not in WHITELIST:
            logging.warning(f"Unauthorized access denied for {user.username}.")
            text = (
                "🚫 *ACCESS DENIED*\n"
                "Sorry, you are *not authorized* to use this command"
            )
            update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
            return
        return func(update, context, *args, **kwargs)

    return wrapped


def show_help(update, context):
    """Send a message when the command /help is issued."""
    howto = f"This bot starts the pyimmigration engine for the job searching. \n" + \
            f"Use the /search <Job title> command for starting email harvesting " + \
            f"and automated email delivery. \n" + \
            f"Use the /start command to enable the background search service. \n" + \
            f"Use the /interval <seconds> command to specify a new " + \
            f"interval between background searches."
    update.message.reply_text(howto, parse_mode=ParseMode.MARKDOWN)


INTERVAL = 1 * 60
SEARCH_LOCK = False


class SearchBackgroundThread:
    def __init__(self, update):
        self.update = update
        self.thread = Thread(target=self.run)

    def start(self):
        self.thread.start()

    def run(self):
        global SEARCH_LOCK
        while True:
            if SEARCH_LOCK:
                self.update.message.reply_text("The background search service is locked.\n"
                                               "There is a job already in progress.")
            elif os.path.exists(USED_SEARCH_KEYWORD_FILE):
                with open(USED_SEARCH_KEYWORD_FILE, 'r') as f:
                    search_keywords = [line.strip() for line in f.readlines() if line.strip()]

                    self.update.message.reply_text("Starting a new background search thread.\n"
                                                   f"The thread will search for {len(search_keywords)} job titles")

                    SEARCH_LOCK = True
                    for keyword in search_keywords:
                        self.update.message.reply_text(f"Starting the searching engine for '{keyword}'")
                        start_job_search(keyword, self.update)
                    SEARCH_LOCK = False
            else:
                self.update.message.reply_text('There are no saved keywords to use for searching. \n'
                                               f'Use need to provide them in the "{USED_SEARCH_KEYWORD_FILE}" file or '
                                               f'use the /search command to automatically add new ones to the keywords list.')

            # self.update.message.reply_text(f'Sleeping for {INTERVAL//60} minutes')
            self.update.message.reply_text(f'Sleeping for {INTERVAL} seconds')
            sleep(INTERVAL)


@whitelist_only
def start(update, context):
    update.message.reply_text("Starting the pyimmigration service")

    search_background_thread = SearchBackgroundThread(update)
    search_background_thread.start()


@whitelist_only
def change_interval(update, context):
    args = context.args

    if not args or len(args) != 1:
        update.message.reply_text("You didn't provide a new valid interval")
    else:
        interval = context.args[0]
        update.message.reply_text(f"Changing the interval to {interval} seconds")

        global INTERVAL
        INTERVAL = int(interval)


@whitelist_only
def search(update, context):
    global SEARCH_LOCK
    if SEARCH_LOCK:
        update.message.reply_text("Couldn't initiate a new job search, as there is one already in progress.")
        return
    else:
        SEARCH_LOCK = True
    raw_jobs = context.args
    if not raw_jobs:
        update.message.reply_text("You didn't provide a job to search for. "
                                  "Please pass a job title or a semicolon separated-list of jobs.")
    else:
        logging.info(f'{update.effective_user.username} has started searching of a new job')
        jobs = " ".join(raw_jobs)
        if ';' in jobs:
            jobs = [line.strip() for line in jobs.split(';')]
        else:
            jobs = [jobs.strip()]
        for i, job in enumerate(jobs):
            if '&&' in job or '&' in job or ';' in job or '|' in job:
                update.message.reply_text('I can break rules, too. Goodbye.')
                return
            update.message.reply_text(f"Initiating a new job search '{job}' [{i + 1}/{len(jobs)}]")
            start_job_search(job, update)
        SEARCH_LOCK = False


def start_job_search(job, update):
    if os.path.exists(USED_SEARCH_KEYWORD_FILE):
        with open(USED_SEARCH_KEYWORD_FILE, 'r') as f:
            content = [line.strip() for line in f.readlines() if line.strip()]
        if job.strip() not in content:
            with open(USED_SEARCH_KEYWORD_FILE, 'a') as f:
                f.write(job.strip())
                f.write(os.linesep)

    os.system('rm -rf harvest.txt')
    os.system('rm -rf links.txt')
    os.system('rm -rf dataset')
    # update.message.reply_text(f'Starting the stepstone webscraper for "{job}"')
    os.system(f'timeout 15m {PYTHON_INTERPRETER} pyapplicant.py '
              f'--stepstone --country de --limit 70 --search "{job}"')
    # update.message.reply_text(f'Starting the google webscraper for "{job}"')
    os.system(f'timeout 15m {PYTHON_INTERPRETER} google_scraping.py '
              f'--search "{job}" --limit 50 ')
    # update.message.reply_text(f"[1/2] Starting the email-harvester for \"{job}\"")
    os.system(f'timeout 15m {PYTHON_INTERPRETER} email_harvester.py '
              f'--threads 250')
    # update.message.reply_text(f"[2/2] Starting the email-harvester for \"{job}\"")
    os.system(f'timeout 15m {PYTHON_INTERPRETER} email_harvester.py '
              f'--dataset-file links.txt --threads 250')
    os.system(f'{PYTHON_INTERPRETER} harvest-fix.py harvest.txt > fixed_harvest.txt')
    if os.path.exists('fixed_harvest.txt'):
        with open('fixed_harvest.txt', 'r') as f:
            fixed_harvest = [line.strip() for line in f.readlines() if line.strip()]
        if fixed_harvest:
            update.message.reply_text(f"The email-harvester"
                                      f" has captured {len(fixed_harvest)} new emails. \n"
                                      f"Starting the email delivery.")
            os.system('bash run-delivery.sh fixed_harvest.txt')

            with open('used_emails.txt', 'r') as f:
                used_emails = [line.strip() for line in f.readlines() if line.strip()]

            update.message.reply_text(f"All tasks have finished. "
                                      f"{os.linesep}"
                                      f"Emails sent in total: {len(used_emails)}")
        else:
            update.message.reply_text("Skipping the delivery, "
                                      "since all discovered emails have been already used")
    else:
        update.message.reply_text("Skipping the delivery, "
                                  "since all discovered emails have been already used")


"""
    ERROR HANDLING
"""


def error(update, context):
    """Log Errors caused by Updates."""
    logging.warning(f"Update {update} caused error {context.error}")


def main():
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO
    )

    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("help", show_help))
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("search", search))
    dp.add_handler(CommandHandler("interval", change_interval))
    dp.add_error_handler(error)

    updater.start_polling()
    logging.info("BOT DEPLOYED. Ctrl+C to terminate")

    updater.idle()


if __name__ == "__main__":
    main()
