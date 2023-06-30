from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, From, To, Bcc
from extra.utils import fill_html
from dotenv import load_dotenv
import os
import sys

load_dotenv()
SG_API_KEY = os.getenv("SG_API_KEY")

def send_onboarding_email(email, user_id):
    message = Mail(
        from_email=From('pablo@upstreamapi.com', 'Upstream'),
        to_emails=[To(email), Bcc('pablo@upstreamapi.com')],
        subject='Login for Upstream',
        html_content=fill_html('templates/email.html', **{'user_id': user_id, 'email': email}))
    sg = SendGridAPIClient(SG_API_KEY)
    response = sg.send(message)
    return response


def send_upload_email(email, user, title):
    try:
        message = Mail(
            from_email=From('pablo@upstreamapi.com', 'Upstream'),
            to_emails=[To(email)],
            subject='New upload',
            html_content=fill_html('templates/upload_email.html', **{'user': user, 'title': title}))
        SendGridAPIClient(SG_API_KEY).send(message)
    except Exception as e:
        print('Error sending upload email: ', e)


def payed_customer(email):
    message = Mail(from_email=From('pablo@upstreamapi.com', 'Upstream AI'),
                   to_emails=[To(email), Bcc(
                       'pablo+payments@upstreamapi.com')],
                   subject='Thanks for subscribing to Upstream AI',
                   html_content=fill_html('templates/purchase_email.html', **{'email': email}))
    sg = SendGridAPIClient(SG_API_KEY)
    response = sg.send(message)
    return response


if __name__ == '__main__':
    args = sys.argv; print(args)
    if len(args) == 2:
        if args[1] == '--onboarding':
            send_onboarding_email('pablofelgueres@gmail.com', 'abc123')
        elif args[1] == '--payed':
            payed_customer('pablofelgueres@gmail.com')
