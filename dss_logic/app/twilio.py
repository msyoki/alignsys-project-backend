# Download the helper library from https://www.twilio.com/docs/python/install
from decouple import config
from twilio.rest import Client

def sendOTP(phone):
    # Set environment variables for your credentials
    # Read more at http://twil.io/secure
    account_sid = config("TWILIO_ACCOUNT_SID")
    auth_token = config("TWILIO_AUTH_TOKEN")
    verify_sid = config("TWILIO_VERIFY_SID")
    client = Client(account_sid, auth_token)

    verified_number =phone

    verification = client.verify.v2.services(verify_sid) \
    .verifications \
    .create(to=verified_number, channel="sms")
    return verification.status



def verifyOTP(verified_number,otp_code):
    account_sid = config("TWILIO_ACCOUNT_SID")
    auth_token = config("TWILIO_AUTH_TOKEN")
    verify_sid = config("TWILIO_VERIFY_SID")
    client = Client(account_sid, auth_token)

    verification_check = client.verify.v2.services(verify_sid) \
    .verification_checks \
    .create(to=verified_number, code=otp_code)
    return verification_check.status
