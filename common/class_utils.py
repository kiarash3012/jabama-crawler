import abc
import threading
import types

import mongoengine
import requests
from zeep import Client
from zeep import helpers


class BaseThread(threading.Thread):
    def __init__(self, callback=None, callback_args=None, *argss, **kwargs):
        target = kwargs.pop('target')
        self.default_args = kwargs.pop('args', [])
        super(BaseThread, self).__init__(target=self.target_with_callback, *argss, **kwargs)
        self.callback = callback
        self.method = target
        self.callback_args = callback_args

    def target_with_callback(self):
        self.method(*self.default_args)
        if self.callback is not None:
            self.callback(*self.callback_args)


class ProviderView(object):
    @classmethod
    @abc.abstractmethod
    def import_data(cls):
        pass

    @classmethod
    @abc.abstractmethod
    def sync_data(cls):
        pass


class RestApiConnector(object):
    @staticmethod
    def get(**kwargs):
        response = requests.get(**kwargs)
        return response

    @staticmethod
    def post(**kwargs):
        response = requests.post(**kwargs)
        return response

    @staticmethod
    def put(**kwargs):
        response = requests.put(**kwargs)
        return response

    @staticmethod
    def patch(**kwargs):
        response = requests.patch(**kwargs)
        return response

    @staticmethod
    def delete(**kwargs):
        response = requests.delete(**kwargs)
        return response


class SoapConnector(object):
    def __init__(self, base_url):
        self._client = Client(base_url)

    def send(self, **kwargs):
        connector = getattr(self._client.service, kwargs.pop("method"))
        result = connector(**kwargs.pop('data'))
        return helpers.serialize_object(result) \
            if isinstance(result, types.ListType) or isinstance(result, types.ClassType) else result


class BaseDocument(mongoengine.Document):
    meta = {
        "abstract": True
    }

    @classmethod
    def bulk_raw_insert(cls, raw_data=None):
        if raw_data is None:
            raw_data = []
        if cls._meta.get('auto_create_index', True):
            cls.ensure_indexes()

        return cls._get_collection().insert(raw_data)

    @classmethod
    def get_fields_ordered(cls):
        return cls._fields_ordered