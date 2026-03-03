from user_agents import parse as parse_ua
from .models import (
    Vault,
    LoginLog,

)
import logging
import secrets
import string

logger = logging.getLogger(__name__)

def get_client_ip(request):
    """Extract client IP from request"""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0]
    return request.META.get("REMOTE_ADDR", "")

def parse_user_agent(user_agent_str):
    """Parse user agent string and return device info"""
    if not user_agent_str:
        return None, None, None, None

    ua = parse_ua(user_agent_str)
    browser = f"{ua.browser.family} {ua.browser.version_string}"
    os = f"{ua.os.family} {ua.os.version_string}"
    device_type = (
        "Mobile"
        if ua.is_mobile
        else (
            "Tablet"
            if ua.is_tablet
            else "PC" if ua.is_pc else "Bot" if ua.is_bot else "Other"
        )
    )
    platform = ua.device.family

    return browser, os, device_type, platform

def get_vault_count(user):
    """Get vault count for user's organization"""
    try:
        return Vault.objects.filter(organization=user.organization).count()
    except Exception:
        return 0

def create_login_log(user, request):
    """Create login log entry"""
    try:
        ip = get_client_ip(request) if request else None
        user_agent_str = request.META.get("HTTP_USER_AGENT", "") if request else ""
        auth_source = (
            "external" if getattr(user, "is_domain_user", False) else "internal"
        )

        browser, os, device_type, platform = parse_user_agent(user_agent_str)

        LoginLog.objects.create(
            user=user,
            ip_address=ip,
            user_agent=user_agent_str,
            browser=browser,
            os=os,
            device_type=device_type,
            platform=platform,
            auth_source=auth_source,
        )
    except Exception as e:
        logger.error(f"Failed to create login log: {e}")

def generate_password(length=8):
    if length > 8:
        length = 8  # enforce max length
    
    alphabet = (
        string.ascii_lowercase +
        string.ascii_uppercase +
        string.digits +
        "!@#$%^&*"
    )

    # Ensure at least one character from each required group
    password = [
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%^&*")
    ]

    # Fill the remaining length
    password += [secrets.choice(alphabet) for _ in range(length - len(password))]

    # Shuffle to avoid predictable order
    secrets.SystemRandom().shuffle(password)

    return ''.join(password)




