Step 1 — Add a new temporary UUID column

Add a new column new_id (UUIDField) to User:

# accounts/models.py
class User(AbstractBaseUser, PermissionsMixin):
    ...
    new_id = models.UUIDField(null=True, blank=True, unique=True)

Then run:

python manage.py makemigrations accounts
python manage.py migrate
Step 2 — Populate new_id with central_id

You can use a standalone script safely:

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
Step 3 — Update foreign keys

If other tables reference User.id (like Document.userid), you will need to update them to point to new_id before swapping columns.

Step 4 — Drop old id and rename new_id

Drop the old id column (or rename it old_id).

Rename new_id → id.

Make id the primary key.

This can be done with a custom SQL migration:

ALTER TABLE accounts_user DROP CONSTRAINT accounts_user_pkey;
ALTER TABLE accounts_user DROP COLUMN id;
ALTER TABLE accounts_user RENAME COLUMN new_id TO id;
ALTER TABLE accounts_user ADD PRIMARY KEY (id);
Step 5 — Test thoroughly

Check that User.id is now UUID

Check that related tables still reference the correct UUID

Backup before performing each step!