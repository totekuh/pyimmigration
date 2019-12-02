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

API_KEY_FILE = 'apikey.txt'
with open(API_KEY_FILE, 'r') as f:
    sendgrid_api_key = f.read().strip()


def get_arguments():
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('--target',
                        dest='target',
                        required=True,
                        help='An email address or a '
                             'txt file with a new-line separated list of email addresses to '
                             'make a massive delivery.')
    parser.add_argument('--file',
                        dest='file',
                        required=False,
                        help='Attach a file to your email.')
    parser.add_argument('--sender',
                        dest='sender',
                        required=True,
                        help='A name to use as a sender name')
    parser.add_argument('--subject',
                        dest='subject',
                        required=True,
                        help='A mail subject to use')
    parser.add_argument('--text',
                        dest='text',
                        required=True,
                        help='A mail text to use. You can pass a file name as an argument or an quotted text')
    options = parser.parse_args()

    return options


class EmailMassSender:
    def __init__(self,
                 sender_email,
                 sendgrid_api_key,
                 subject,
                 text,
                 attached_file_path=None,
                 smtp_host='smtp.sendgrid.net',
                 smtp_port=465,
                 used_emails_file='used_emails.txt'):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sendgrid_api_key = sendgrid_api_key
        self.subject = subject
        self.text = text
        self.attached_file_path = attached_file_path
        self.used_emails_file = used_emails_filea

    def send_to(self, recipient_address):
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
        msg.attach(MIMEText(self.text, 'plain'))
        if self.attached_file_path:
            msg.attach(part)

        text_msg = msg.as_string()
        if recipient_address in self.read_used_emails():
            logging.warning(f'Skipping {recipient_address} as it was used before')
        else:
            try:
                logging.info(f'Sending email to {recipient_address}')
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port)
                server.ehlo()
                server.login('apikey', self.sendgrid_api_key)
                server.sendmail(self.sender_email, recipient_address, text_msg)
                server.close()
                self.store_used_email(recipient_address)
            except Exception as e:
                logging.error(e)

    def store_used_email(self, email_address):
        with open(self.used_emails_file, 'a') as used_f:
            used_f.write(email_address)
            used_f.write('\n')

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
attached_file_path = options.file

sender = EmailMassSender(sender_email,
                         sendgrid_api_key,
                         subject,
                         text,
                         attached_file_path)
for email in emails:
    sender.send_to(email)
