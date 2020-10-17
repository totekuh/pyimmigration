#!/usr/bin/env python3
import logging
import os
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

logging.basicConfig(format='[%(asctime)s %(levelname)s]: %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p',
                    level='INFO')

DEFAULT_USED_EMAILS_FILE = 'used_emails.txt'
DEFAULT_SUBJECT = 'Job Application'
DEFAULT_ATTACH_FILENAME = 'cv.pdf'
DEFAULT_MAIL_TEXT_FILENAME = 'text.txt'
DEFAULT_SMTP_PORT = 465


def get_arguments():
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('--target',
                        dest='target',
                        required=True,
                        help='An email address or a '
                             'txt file with a new-line separated list of email addresses to '
                             'perform a massive delivery to.')
    parser.add_argument('--file',
                        dest='file',
                        default=DEFAULT_ATTACH_FILENAME,
                        required=False,
                        help='Pass this argument to attach a file to your email. '
                             f"Default is {DEFAULT_ATTACH_FILENAME}")
    parser.add_argument('--sender',
                        dest='sender',
                        required=True,
                        help='A name to use as the sender name')
    parser.add_argument('--subject',
                        dest='subject',
                        default=DEFAULT_SUBJECT,
                        required=False,
                        help=f"A mail subject to use. Default is {DEFAULT_SUBJECT}")
    parser.add_argument('--text',
                        dest='text',
                        default=DEFAULT_MAIL_TEXT_FILENAME,
                        required=False,
                        help='The mail text. This argument might be used as a string or as a file name. '
                             f"Default is '{DEFAULT_ATTACH_FILENAME}'")
    parser.add_argument('--used-emails',
                        dest='used_emails',
                        default=DEFAULT_USED_EMAILS_FILE,
                        required=False,
                        help='A txt file to write used emails.')
    parser.add_argument('--smtp-login',
                        dest='smtp_login',
                        required=True,
                        help='An SMTP login to use for authentication')
    parser.add_argument('--smtp-password',
                        dest='smtp_password',
                        required=True,
                        help='An SMTP password to use for authentication')
    parser.add_argument('--smtp-host',
                        dest='smtp_host',
                        required=True,
                        help='An SMTP host to use')
    parser.add_argument('--smtp-port',
                        dest='smtp_port',
                        default=DEFAULT_SMTP_PORT,
                        type=int,
                        required=False,
                        help=f"An SMTP port to use. Default is {DEFAULT_SMTP_PORT}")
    options = parser.parse_args()

    return options


class EmailMassSender:
    def __init__(self,
                 sender_email,
                 subject,
                 smtp_login,
                 smtp_password,
                 smtp_host,
                 smtp_port=DEFAULT_SMTP_PORT,
                 attached_file_path=None,
                 used_emails_file='used_emails.txt'):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_login = smtp_login
        self.smtp_password = smtp_password
        self.sender_email = sender_email
        self.subject = subject
        self.attached_file_path = attached_file_path
        self.used_emails_file = used_emails_file

        self.emails_sent = set()
        self.emails_skipped = set()

    def send_to(self, recipient_address, text, write_log=True):
        if self.attached_file_path:
            part = MIMEBase('application', "octet-stream")
            part.set_payload(open(self.attached_file_path, "rb").read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition',
                            'attachment; filename={0}'.format(os.path.basename(self.attached_file_path)))

        msg = MIMEMultipart()
        msg['From'] = self.sender_email
        msg['To'] = recipient_address
        msg['Subject'] = self.subject
        msg.attach(MIMEText(text, 'plain'))
        if self.attached_file_path:
            msg.attach(part)

        text_msg = msg.as_string()
        if recipient_address in self.read_used_emails():
            logging.warning(f'Skipping {recipient_address} as it was already used')
            self.emails_skipped.add(recipient_address)
        else:
            try:
                logging.info(f'Sending an email to {recipient_address}')
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port)
                server.ehlo()
                server.login(self.smtp_login, self.smtp_password)
                server.sendmail(self.sender_email, recipient_address, text_msg)
                server.close()
                if write_log:
                    self.store_used_email(recipient_address)
            except Exception as e:
                logging.error(e)

    def store_used_email(self, email_address):
        self.emails_sent.add(email_address)
        with open(self.used_emails_file, 'a') as used_f:
            used_f.write(email_address)
            used_f.write(os.linesep)

    def read_used_emails(self):
        if Path(self.used_emails_file).exists():
            with open(self.used_emails_file) as used_f:
                return [e.strip() for e in used_f.readlines()]
        else:
            return []


options = get_arguments()
text = options.text
if Path(text).exists():
    with open(Path(text), 'r') as text_f:
        text = text_f.read()
emails = []
target = options.target
if Path(target).exists():
    with open(target, 'r') as emails_f:
        emails = [email.strip() for email in emails_f.readlines()]
else:
    emails = [target]

sender_email = options.sender
subject = options.subject

sender = EmailMassSender(sender_email=sender_email,
                         smtp_login=options.smtp_login,
                         smtp_password=options.smtp_password,
                         smtp_host=options.smtp_host,
                         smtp_port=options.smtp_port,
                         subject=subject,
                         attached_file_path=options.file,
                         used_emails_file=options.used_emails)
for email in emails:
    sender.send_to(email, text)

confirmation_text = f'Massive email delivery has finished with {len(emails)} emails. ' \
                    f'{os.linesep} ' \
                    f'{len(sender.emails_sent)} emails have been delivered;' \
                    f'{os.linesep} ' \
                    f'{len(sender.emails_skipped)} emails have been already used; ' \
                    f'{os.linesep}' \
                    f'Emails sent in total: {len(sender.read_used_emails())}; ' \
                    f'{os.linesep}' \
                    f'{os.linesep.join(sender.emails_sent)}'

# send an email to the sender in order to confirm the delivery
sender.send_to(sender_email, confirmation_text, write_log=False)
