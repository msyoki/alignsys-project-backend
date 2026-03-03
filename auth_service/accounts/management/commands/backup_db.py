import os
import subprocess
import zipfile
from datetime import datetime
from django.conf import settings
from django.core.mail import EmailMessage
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Backup database and email it as a zipped attachment"

    def handle(self, *args, **kwargs):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_dir = os.path.join(settings.BASE_DIR, "db_backups")
        os.makedirs(backup_dir, exist_ok=True)

        sql_file = f"db_backup_{timestamp}.sql"
        sql_path = os.path.join(backup_dir, sql_file)

        zip_file = f"{sql_file}.zip"
        zip_path = os.path.join(backup_dir, zip_file)

        # ---- DATABASE CREDENTIALS ----
        db = settings.DATABASES["default"]

        # ---- POSTGRES BACKUP ----
        dump_command = [
            "pg_dump",
            "-h", db["HOST"],
            "-p", str(db.get("PORT", 5432)),
            "-U", db["USER"],
            "-f", sql_path,
            db["NAME"],
        ]

        env = os.environ.copy()
        env["PGPASSWORD"] = db["PASSWORD"]

        subprocess.check_call(dump_command, env=env)

        # ---- ZIP FILE ----
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(sql_path, arcname=sql_file)

        # ---- EMAIL ----
        email = EmailMessage(
            subject="Database Backup",
            body="Attached is the latest database backup.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[settings.BACKUP_EMAIL],
        )

        email.attach_file(zip_path)
        email.send()

        # ---- CLEANUP ----
        os.remove(sql_path)
        os.remove(zip_path)

        self.stdout.write(self.style.SUCCESS("Backup created and emailed successfully"))
