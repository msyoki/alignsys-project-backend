import secrets
import string


from django.template.loader import render_to_string 
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags
from accounts.models import User

from datetime import datetime
import pytz
from django.conf import settings
from email.message import EmailMessage
from email.utils import make_msgid, formatdate
import smtplib

def generate_pdw():
    # define the alphabet
    letters = string.ascii_letters
    digits = string.digits
    special_chars = string.punctuation

    alphabet = letters + digits + special_chars

    # fix password length
    pwd_length = 12

    # generate password meeting constraints
    while True:
        pwd = ''
        for i in range(pwd_length):
            pwd += ''.join(secrets.choice(alphabet))

        if (any(char in special_chars for char in pwd) and 
            sum(char in digits for char in pwd)>=2):
                break
    # print(pwd)

    return pwd

def send_email(email, email_body):
    smtp_server = "mail.privateemail.com"
    smtp_port = 587

    login = settings.ALIGNSYS_LOGIN   # apps@alignsys.tech
    password = settings.ALIGNSYS_PWD

    msg = EmailMessage()
    msg.add_alternative(email_body, subtype="html")

    # Use the authenticated mailbox but display as "No Reply"
    email_from = "apps@alignsys.tech"
    display_name = "No Reply - Alignsys Support"

    msg["Subject"] = "Alignsys DSS: Password Reset"
    msg["From"] = f"{display_name} <{email_from}>"
    msg["To"] = email
    msg["Reply-To"] = "no-reply@alignsys.tech"  # ✅ replies won’t go to apps@
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid()
    msg["List-Unsubscribe"] = f"<mailto:unsubscribe@{email_from.split('@')[1]}>"

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


def send_email_newadmin(company_obj,pwd):
    # send email to new user

    mail_subject = 'Alignsys Corporate DSS - Account registration completed successfully'
    message = render_to_string('email/new_admin_email.html', {  
        'company': company_obj.name,   
        'username': company_obj.email,
        'password': pwd,
    })  
    text_content=strip_tags(message)
    to_email = company_obj.email 

    email=EmailMultiAlternatives(
        mail_subject, text_content, to=[to_email]  
    )
    email.attach_alternative(message,"text/html")
    email.send()

def send_email_newcompany(email,name):
    # send email to new user

    mail_subject = 'Alignsys Corporate DSS - Welcome'
    message = render_to_string('email/welcome.html', {  
        'company': name,   
    })  
    text_content=strip_tags(message)
    to_email = email 

    email=EmailMultiAlternatives(
        mail_subject, text_content, to=[to_email]  
    )
    email.attach_alternative(message,"text/html")
    email.send()


def send_email_newuser(user,pwd):
    # send email to new user

    mail_subject = 'Alignsys Corporate DSS - Account registration completed successfully'
    message = render_to_string('email/new_users_email.html', {  
        'first_name': user.first_name,
        'last_name' :user.last_name,
        'username': user.email,
        'password': pwd,
    })  
    text_content=strip_tags(message)
    to_email = user.email 

    email=EmailMultiAlternatives(
        mail_subject, text_content, to=[to_email]  
    )
    email.attach_alternative(message,"text/html")
    email.send()

# check if email has same domain

def compare_email_domain(email,reference_email):
    
    # Extract domain from the reference email
    reference_domain = reference_email.split("@")[1]
    
    # Extract domain from the passed email
    passed_domain = email.split("@")[1]
    
    # Compare the domains
    if reference_domain == passed_domain:
        return True
    else:
        return False
    
def getUser(id):
    user= User.objects.get(id=id)
    response= {
        "email":user.email,
        "first_name":user.first_name,
        "last_name":user.last_name
    }
    return response



def humanize_timestamp(time):
   # Define the timestamp in the given format
    timestamp_str = f'{time}'

    # Parse the timestamp
    timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S.%f%z')

    # Convert to the 'Africa/Nairobi' time zone
    nairobi_timezone = pytz.timezone('Africa/Nairobi')
    nairobi_timestamp = timestamp.astimezone(nairobi_timezone)

    # Format and print the converted timestamp
    formatted_timestamp = nairobi_timestamp.strftime("%Y-%m-%d %H:%M:%S")
    return formatted_timestamp

