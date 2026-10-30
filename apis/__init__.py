from django.db.backends.base.base import BaseDatabaseWrapper

# Allow MySQL 8.0.x with Django 6
BaseDatabaseWrapper.check_database_version_supported = lambda self: None

