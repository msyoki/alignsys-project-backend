# populate_new_id.py
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from accounts.models import User

for user in User.objects.all():
    if user.central_id:
        user.new_id = user.central_id
    else:
        import uuid
        user.new_id = uuid.uuid4()  # fallback for users without central_id
    user.save(update_fields=["new_id"])

print("All new_id fields populated")


