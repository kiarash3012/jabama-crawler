from mongoengine import connect, register_connection
from DataBase.config import Configs as DB_Configs


class GlobalInit:
    register_connection(alias='core', name='spider')

# connect(
#     db=DB_Configs.db_name,
#     host=DB_Configs.host,
#     port=DB_Configs.port
# )
