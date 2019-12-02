#!/usr/bin/env python3
import logging
import os
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import boto3

logging.basicConfig(format='[%(asctime)s %(levelname)s]: %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p',
                    level='INFO')

AWS_KEY_FILE = 'aws-keys.txt'
DEFAULT_AWS_REGION = 'eu-central-1'

DEFAULT_USED_EMAILS_FILE = 'used_emails.txt'
DEFAULT_SUBJECT = 'Job Application'
DEFAULT_ATTACH_FILENAME = 'cv.pdf'
DEFAULT_MAIL_TEXT_FILENAME = 'text.txt'

with open(AWS_KEY_FILE, 'r') as f:
    aws_keys = f.read().strip()


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
                        default=DEFAULT_ATTACH_FILENAME,
                        required=False,
                        help='Attach a file to your email. Default is ' + DEFAULT_ATTACH_FILENAME)
    parser.add_argument('--sender',
                        dest='sender',
                        required=True,
                        help='A name to use as a sender name')
    parser.add_argument('--subject',
                        dest='subject',
                        default=DEFAULT_SUBJECT,
                        required=False,
                        help='A mail subject to use. Default is ' + DEFAULT_SUBJECT)
    parser.add_argument('--text',
                        dest='text',
                        default=DEFAULT_MAIL_TEXT_FILENAME,
                        required=False,
                        help='The mail text. This argument might be used as a string or as a file name. Default is '
                             + DEFAULT_ATTACH_FILENAME)
    parser.add_argument('--used-emails',
                        dest='used_emails',
                        default=DEFAULT_USED_EMAILS_FILE,
                        required=False,
                        help='A txt file to write used emails.')
    options = parser.parse_args()

    return options


class EmailMassSender:
    def __init__(self,
                 sender_email,
                 aws_access_key_id,
                 aws_secret_key,
                 subject,
                 attached_file_path=None,
                 region=DEFAULT_AWS_REGION,
                 smtp_host='smtp.sendgrid.net',
                 smtp_port=465,
                 used_emails_file='used_emails.txt'):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.sender_email = sender_email

        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_key = aws_secret_key

        self.subject = subject
        self.attached_file_path = attached_file_path
        self.used_emails_file = used_emails_file
        self.charset = 'UTF-8'
        self.region = region

    def send_to(self, recipient_address, text):
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
            logging.warning(f'Skipping {recipient_address} as it was used before')
        else:
            try:
                logging.info(f'Sending email to {recipient_address}')
                client = boto3.client('ses',
                                      region_name=self.region,
                                      aws_access_key_id=self.aws_access_key_id,
                                      aws_secret_access_key=self.aws_secret_key
                                      )
                response = client.send_email(
                            Source=self.sender_email,
                            Destination={
                                'ToAddresses': [
                                    recipient_address,
                                ]
                                # ,
                                # 'CcAddresses': [
                                #     'string',
                                # ],
                                # 'BccAddresses': [
                                #     'string',
                                # ]
                            },
                            Message={
                                'Subject': {
                                    'Data': self.subject,
                                    'Charset': self.charset
                                },
                                'Body': {
                                    'Text': {
                                        'Data': text_msg,
                                        'Charset': self.charset
                                    }
                                    # ,
                                    # 'Html': {
                                    #     'Data': 'string',
                                    #     'Charset': 'string'
                                    # }
                                }
                            },
                            ReplyToAddresses=[
                                self.sender_email,
                            ],
                            # ReturnPath='string',
                            # SourceArn='string',
                            # ReturnPathArn='string',
                            # Tags=[
                            #     {
                            #         'Name': 'string',
                            #         'Value': 'string'
                            #     },
                            # ],
                            # ConfigurationSetName='string'
                )

                logging.info(response)
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

aws_access_key_id = aws_keys.split(':')[0].strip()
aws_secret_key = aws_keys.split(':')[1].strip()
sender = EmailMassSender(sender_email=sender_email,
                         aws_access_key_id=aws_access_key_id,
                         aws_secret_key=aws_secret_key,
                         subject=subject,
                         attached_file_path=options.file,
                         used_emails_file=options.used_emails)
for email in emails:
    sender.send_to(email, text)

# sending the last email to the sender in order to confirm the delivery
sender.send_to(sender_email, f'Massive email delivery has finished with {len(emails)} emails')
