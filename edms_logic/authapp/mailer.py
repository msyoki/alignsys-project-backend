from rest_framework.response import Response
from rest_framework import status
import requests
from django.conf import settings

import smtplib
from email.message import EmailMessage
import smtplib
from email.message import EmailMessage
from email.utils import make_msgid, formatdate




def api_mailer(mail_service_base_url, email,email_body):
    
    # External API endpoint
    api_url = f"{mail_service_base_url}/api/Email"

    # Convert `email_body` to proper form-data encoding
    payload = {
        "Subject": (None, "Alignsys EDMS: Password Reset"),
        "recipient": (None, email),
        "emailBody": (None, email_body),
        "ProfileID": (None, "40cdb363-0b1b-4bda-bfdc-a60cce499f11"),
        "cc": (None, ""),
        "bcc": (None, ""),
        "IsText": (None, "false"),
    }


    headers = {"Accept": "*/*"}


    
    try:
        response = requests.post(api_url, headers=headers, files=payload)
        if response.status_code == 201:
            return {
                "success": True,
                "message": "Email sent successfully.",
            }
 
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"Email service error: {str(e)}",
        }
        
        
def send_email(email, email_body):
    smtp_server = "mail.privateemail.com"
    smtp_port = 587

    login = settings.ALIGNSYS_LOGIN
    password = settings.ALIGNSYS_PWD

    msg = EmailMessage()
    msg.add_alternative(email_body, subtype='html')

    email_from = "apps@alignsys.tech"
    display_name = "Alignsys Support"

    msg['Subject'] = "Alignsys EDMS: Password Reset"
    msg['From'] = f"{display_name} <{email_from}>"  # ✅ changed here
    msg['To'] = email
    msg['Reply-To'] = email_from
    msg['Date'] = formatdate(localtime=True)
    msg['Message-ID'] = make_msgid()
    msg['List-Unsubscribe'] = f"<mailto:unsubscribe@{email_from.split('@')[1]}>"

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(login, password)
            server.send_message(msg)
            return {
                "success": True,
                "message": "Email sent successfully.",
            }
    except Exception as e:
        return {
            "success": False,
            "error": f"Email service error: {str(e)}",
        }
