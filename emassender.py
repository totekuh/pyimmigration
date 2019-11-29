import sys
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


class EmailMassSender:
    def __init__(self, mail_user, mail_password, subject, text):
        self.mail_user = mail_user
        self.mail_password = mail_password
        self.subject = subject
        self.text = text

    def send_to_list(self, email_list):
        for to in email_list:
            msg = MIMEMultipart()
            msg['From'] = self.mail_user
            msg['To'] = to
            msg['Subject'] = self.subject
            msg.attach(MIMEText(self.text, 'plain'))
            text_msg = msg.as_string()
            try:
                server = smtplib.SMTP_SSL('smtp.mail.ru', 465)
                # server.set_debuglevel(1)
                server.ehlo()
                server.login(self.mail_user, self.mail_password)
                server.sendmail(self.mail_user, to, text_msg)
                server.close()
                print('Email sent!')
            except Exception as e:
                print('Something went wrong...')
                print(str(e))


def main():
    mail_user = 'account@mail.ru'
    mail_password = 'password'
    subject = 'yo dog!'
    text = "where is my money?"

    to_list = ['mail1@gmail.com', 'mail2@gmail.com']
    sender = EmailMassSender(mail_user, mail_password, subject, text)
    sender.send_to_list(to_list)


if __name__ == '__main__':
    sys.exit(main())
