from mongoengine import *
from DataBase import initialization

initialization.GlobalInit()


class RatingIndex(EmbeddedDocument):
    employee_attitude = IntField()
    room_clarity = IntField()
    lobby_clarity = IntField()
    hotel_prestige = IntField()
    restaurant_quality = IntField()
    hotel_position = IntField()
    bcr = IntField()  # Benefit/Cost Ratio
    recommend = IntField()
    date = StringField()


class Rating(EmbeddedDocument):
    total_rating = FloatField(default=None)
    total_number_of_votes = IntField(default=None)
    rating_index = EmbeddedDocumentListField(RatingIndex)


class Image(EmbeddedDocument):
    uri = StringField()
    weight = IntField()


class Hotel(Document):
    hash = StringField()
    hotel_id = StringField()
    title = StringField(required=True)
    url = StringField()
    website = StringField(max_length=50)
    address = StringField()
    stars = IntField(default=0)
    description_title = StringField()
    description = StringField()
    important_points_title = StringField()
    important_points = StringField()
    facilities = ListField()
    not_available_facilities = ListField()
    distance_to_important_places = ListField()
    longitude = StringField()
    latitude = StringField()
    ratings = EmbeddedDocumentField(Rating)
    # images = EmbeddedDocumentListField(Image)
    # comments = ListField()

    meta = {
            "db_alias": 'core',
            "collection": 'Hotel',
        }
