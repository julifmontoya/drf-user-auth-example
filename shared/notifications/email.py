from django.core.mail import EmailMessage, send_mail
from decouple import config


def send_email(subject, email_body):
    # Function to send an email with the provided subject and body
    email = EmailMessage(subject, email_body, config('EMAIL_HOST_USER'), [config('EMAIL_HOST_CONTACT')])
    email.send()


def send_email_to(recipient, subject, email_body):
    # Function to send an email with the provided subject and body to a
    # specific (variable) recipient, from EMAIL_HOST_USER.
    send_mail(subject, email_body, config('EMAIL_HOST_USER'), [recipient])
