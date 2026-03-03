import requests
from typing import Dict, Any
from django.conf import settings


def create_generate_license(
    company_id: int,
    number_of_users: int,
    number_of_years: int,
) -> Dict[str, Any]:
    """
    Create and generate a license for a company.
    
    Args:
        company_id: The ID of the company
        number_of_users: Number of users for the license
        number_of_years: Number of years for the license validity
    
    Returns:
        Dict containing the API response
        
    Raises:
        requests.exceptions.RequestException: If the API request fails
    """
    endpoint = f"{settings.DSS_API}/api/Licensing/CreateGenerate"
    
    headers = {
        "accept": "*/*",
        "Content-Type": "application/json"
    }
    
    payload = {
        "companyId": company_id,
        "numberOfUsers": number_of_users,
        "numberOfYears": number_of_years
    }
    
    response = requests.post(endpoint, json=payload, headers=headers)
    response.raise_for_status()
    
    try:
        return response.json()
    except requests.exceptions.JSONDecodeError:
        return {"status_code": response.status_code, "content": response.text}