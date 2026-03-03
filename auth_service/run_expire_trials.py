# run_expire_trials.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from accounts.tasks import check_and_expire_trials

check_and_expire_trials()  # call the function directly