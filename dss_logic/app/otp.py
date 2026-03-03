import requests
import json

import random as r

# This class returns the string needed to generate the key
phone="0752769602"

def send_sms(phone,OTP):
    url = "https://portal.paradox.co.ke/api/v1/send-sms"

    payload = json.dumps({
    "sender": "TECHEDGE",
    "message": f"Your device validation OTP is {OTP}.",
    "phone": f"{phone}",
    "correlator": 1
    })
    headers = {
    'Content-type': 'application/json',
    'Accept': 'application/json',
    'Authorization': 'Bearer  eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiIzIiwianRpIjoiOTBlNzQ0NWZkYjhjMTQ0MWIwODMyYmUxNDg1OTBkNjAwYTIwNWMwNjc4YzEzZDUzZTZhMDEwOGNkNTczNWE0MjEyYmJlOWJhOWUyZTM4ODciLCJpYXQiOjE2NTc2MDc4MjIsIm5iZiI6MTY1NzYwNzgyMiwiZXhwIjo0ODEzMjgxNDIyLCJzdWIiOiIyODUiLCJzY29wZXMiOltdfQ.ThEdVSVph44tTQsl3vIvJH5z3D1DAH9IISAq1LyS7u9E3ZaUNoqiPdq_QsX1zr5LXTm05bgharA5SbNY31AIsi-yzYY6lXx1A3ogIHyqmXMv7DeCCITjuyGmYMLKplbBytcYHGkqqDo8I2CPqgMOZyeV1aul2Uqg6z2NovwgMfSZSJ0ijY26-fdE3R1Cpfb29f_RlwXC0KQcZZ33z9gTiI9WT800hrYOwMQyLWz4Xe2zQL0wEmo_C53po43I7Uj8tbhim5oZdSr_Swc8Le_KZj0x3P-V3w_rVcA5xhfRUG9mDgm6xaeCCPVonrOmDKlCJPVWpoNn_psup_C-cuN6PIQOB08fIheluR2dm5SHRo91k0keVKDV5c9gx0MbMhN2s1yHU9PIPtKTg3SgE_dlYMuxy8YhnlvwZDCJEMazmw4YWT_1bXo8yO02PNvpzyE-d8Io6jRAfph1My5u0P5cxmNJf79L1gCxKYBZEHj-upLrhq23obB0LOjPBz2LkSvHeAzY16JKgBn3m97SBPaQe0zw-sxzX1jH3hgFNEvNME434peq9xayJlH4OSIliaXKZDekm4dDZePO9gv3hH9Ys6GgFHhZJj1kdBI5hqCdRPMiEmpBpDu-pIGHwd2N45dcmrtxKCGnmGx-u-Zh4LZws52Ane8Gp8lxukXZrKQm670'
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    return response.text


# Get to Create a call for OTP
def generateOTP(phone):
    otp=""
    for i in range(4):
        otp+=str(r.randint(1,9))
    send_sms(phone,otp)
    return otp

