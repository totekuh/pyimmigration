#!/usr/bin/env python3.7
import os

PYTHON_INTERPRETER = 'python3'

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
    howto = (
        f"This bot starts the pyimmigration engine for the job searching. \n"
        f"Please use the /search <Job title> for starting email harvesting and automatic email develiry."
    )
    update.message.reply_text(howto, parse_mode=ParseMode.MARKDOWN)


@whitelist_only
def start(update, context):
    """Send a message when the command /start is issued."""
    update.message.reply_text("Starting the pyimmigration service")

@whitelist_only
def search(update, context):
    raw_jobs = context.args
    if not raw_jobs:
        update.effective_user.reply_text("You didn't provide a job to search for. "
                                         "Please pass a job title or a semicolon separated-list of jobs.")
    else:
        logging.info(f'{update.effective_user.username} has started searching of a new job')
        jobs = " ".join(raw_jobs)
        if ';' in jobs:
            jobs = [line.strip() for line in jobs.split(';')]
        else:
            jobs = [jobs.strip()]
        for i, job in enumerate(jobs):
            logging.info(f"Starting the search for the {job} title [{i + 1}/{len(job)}]")

            update.effective_user.reply_text('Deleting the harvest.txt file')
            os.system('rm -rf harvest.txt')

            update.effective_user.reply_text(f'Starting the stepstone web scraper for "{job}"')
            os.system(f'{PYTHON_INTERPRETER} pyapplicant.py --stepstone --country de --limit 70 --search {job}')
            update.effective_user.reply_text(f'Finished scraping the stepstone.de website for "{job}"')

            update.effective_user.reply_text(f'Starting the google scraping for "{job}"')
            os.system(f'{PYTHON_INTERPRETER} google_scraping.py --search {job} --limit 50 ')
            update.effective_user.reply_text(f'Finished Google scraping for "{job}"')

            update.effective_user.reply_text(f"[1/2] Starting the email harvesting for \"{job}\"")
            os.system(f'{PYTHON_INTERPRETER} email_harvester.py --threads 250')

            update.effective_user.reply_text(f"[2/2] Starting the email harvesting for \"{job}\"")
            os.system(f'{PYTHON_INTERPRETER} email_harvester.py --dataset-file links.txt --threads 250')

            with open("harvest.txt", 'r') as harvest:
                harvest_content = [line.strip() for line in harvest.readlines() if line.strip()]
            update.effective_user.reply_text(f"The email-harvester has captured {len(harvest_content)} emails")

            update.effective_user.reply_text(f"Removing duplicates from the harvest file "
                                             f"and comparing it with used emails")
            os.system(f"{PYTHON_INTERPRETER} harvest-fix.py harvest.txt > fixed_harvest.txt")

            with open('fixed_harvest.txt', 'r') as f:
                fixed_harvest = [line.strip() for line in f.readlines() if line.strip()]

            if fixed_harvest:
                update.effective_user.reply_text(f"Starting the email delivery")
                os.system('bash run-delivery.sh fixed_harvest.txt')
                update.effective_user.reply_text(f"All tasks have finished")
            else:
                update.effective_user.reply_text("No new emails found, couldn't start the delivery.")







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
    dp.add_error_handler(error)

    updater.start_polling()
    logging.info("BOT DEPLOYED. Ctrl+C to terminate")

    updater.idle()


if __name__ == "__main__":
    main()
