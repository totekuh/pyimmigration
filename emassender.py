import sys
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders


class EmailMassSender:
    def __init__(self, sender_email, sendgrid_api_key, subject, text, attached_file_path=None):
        self.sender_email = sender_email
        self.sendgrid_api_key = sendgrid_api_key
        self.subject = subject
        self.text = text
        self.attached_file_path = attached_file_path

    def send_to_list(self, email_list):
        if self.attached_file_path is not None:
            part = MIMEBase('application', "octet-stream")
            part.set_payload(open(self.attached_file_path, "rb").read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition',
                            'attachment; filename={0}'.format(os.path.basename(self.attached_file_path)))

        for to in email_list:
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = to
            msg['Subject'] = self.subject
            msg.attach(MIMEText(self.text, 'plain'))
            if self.attached_file_path is not None:
                msg.attach(part)

            text_msg = msg.as_string()
            try:
                server = smtplib.SMTP_SSL('smtp.sendgrid.net', 465)
                server.ehlo()
                server.login('apikey', self.sendgrid_api_key)
                server.sendmail(self.sender_email, to, text_msg)
                server.close()
                print('Email sent!')
            except Exception as e:
                print('Something went wrong...')
                print(str(e))


def main():
    sender_email = 'ninja@virtualsquad.com'
    sendgrid_api_key = 'apikey'
    subject = 'subject'
    text = "text of the message"
    attached_file_path = 'AI.pdf'

    to_list = ['evilden91@gmail.com', 'downtownxore@gmail.com']
    sender = EmailMassSender(sender_email, sendgrid_api_key, subject, text, attached_file_path)
    sender.send_to_list(to_list)


if __name__ == '__main__':
    sys.exit(main())
