🥇 OPTION 1 — Linux Cron Job (Production Recommended)
Step 1 — Find Python Path

Run:

which python

If using virtualenv:

which python
# Example:
# /home/ubuntu/venv/bin/python
Step 2 — Open Crontab
crontab -e
Step 3 — Add Cron Entry

Run every 5 minutes:

*/5 * * * * /home/ubuntu/venv/bin/python /home/ubuntu/project/manage.py process_trials >> /home/ubuntu/project/trials.log 2>&1

Replace:

/home/ubuntu/venv/bin/python

/home/ubuntu/project/

with your actual paths.

Cron Timing Examples
Schedule	Expression
Every 5 minutes	*/5 * * * *
Every hour	0 * * * *
Every day at midnight	0 0 * * *
🥈 OPTION 2 — Windows Task Scheduler

Since you develop on Windows, here’s the clean way.

Step 1 — Create a .bat File

Create file:

run_trials.bat

Inside:

cd C:\path\to\your\project
venv\Scripts\python manage.py process_trials

Adjust paths properly.

Step 2 — Open Task Scheduler

Press:

Win + R

Type:

taskschd.msc
Step 3 — Create Basic Task

Click Create Basic Task

Name: Process Expired Trials

Trigger:

Choose “Daily”

Then go to Advanced and set:

Repeat every 5 minutes

For duration: Indefinitely

Action:

Start a Program

Browse and select your run_trials.bat

Finish.