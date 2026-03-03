import requests


API_URL = 'http://212.224.93.137:240/api/Values'
HEADERS = {'Content-Type': 'application/json'}

def register_vault(company_name):
    payload = {'vaultName': company_name}

    try:
        post_response = requests.post(API_URL, json=payload, headers=HEADERS)
        post_response.raise_for_status()  # Raise an exception for non-2xx responses
        return post_response.status_code  # Return the status code for successful requests
    except requests.exceptions.RequestException as e:
        return 400  # Return None or raise further, depending on the desired behavior

