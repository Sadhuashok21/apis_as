# db_router.py

class AppDatabaseRouter:
    """
    Route database operations for specific apps to specific databases.
    """

    app_label_to_db = {
        'humbell': 'humbell',
        'krishi': 'krishi',
        'aaaab': 'aaaab',
        'aaaaa': 'aaaaa',
    }

    def db_for_read(self, model, **hints):
        return self.app_label_to_db.get(model._meta.app_label, 'default')

    def db_for_write(self, model, **hints):
        return self.app_label_to_db.get(model._meta.app_label, 'default')

    def allow_relation(self, obj1, obj2, **hints):
        db1 = self.app_label_to_db.get(obj1._meta.app_label, 'default')
        db2 = self.app_label_to_db.get(obj2._meta.app_label, 'default')
        if db1 == db2:
            return True
        return False

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Ensure migrations only happen on the correct database.
        """
        target_db = self.app_label_to_db.get(app_label, 'default')
        return db == target_db
