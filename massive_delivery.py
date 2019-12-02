#!/usr/bin/env/python3
from pathlib import Path

import os
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
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
                 smtp_port=465):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sendgrid_api_key = sendgrid_api_key
        self.subject = subject
        self.text = text
        self.attached_file_path = attached_file_path

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
        try:
            logging.info(f'Sending email to {recipient_address}')
            server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port)
            server.ehlo()
            server.login('apikey', self.sendgrid_api_key)
            server.sendmail(self.sender_email, recipient_address, text_msg)
            server.close()
        except Exception as e:
            logging.error(e)


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
