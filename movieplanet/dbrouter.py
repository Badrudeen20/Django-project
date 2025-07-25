class MoviePlanetRouter:
    def db_for_read(self, model, **hints):
        if model._meta.app_label in ['movieplanet']:
            return 'movieplanet'
        return 'default'

    def db_for_write(self, model, **hints):
        if model._meta.app_label in ['movieplanet']:
            return 'movieplanet'
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        if obj1._state.db == obj2._state.db:
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label in ['movieplanet']:
            return db == 'movieplanet'
        return db == 'default'