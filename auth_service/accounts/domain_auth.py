"""Utilities for domain authentication."""
import httpx
import os
from django.conf import settings


async def verify_domain_user(username: str, password: str, domain: str) -> bool:
    """Verify user credentials against external domain auth API."""
    domain_auth_url = settings.DOMAIN_AUTH_URL
    
    if not domain_auth_url:
        return False
    
    payload = {
        "username": username,
        "password": password,
        "domain": domain,
    }
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(domain_auth_url, json=payload, timeout=10.0)
        return resp.status_code == 200
    except Exception:
        return False
