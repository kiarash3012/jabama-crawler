import mongoengine

class Spiders:
    meta = {
        'db_alias': 'core',
        'collection': 'spiders_db'
    }