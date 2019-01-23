import scrapy
import json
import re
import os
import shutil

from urllib import request
from common import class_utils


class AlaeddinSpider(scrapy.Spider):
    name = "alaeddin"
    all_data = list()
    custom_settings = {"DEFAULT_REQUEST_HEADERS":  {"Content-Type": "application/json; charset=utf-8"}}

    @classmethod
    def data_processor(cls, response):
        def _clean_html(data, is_list=False):
            if is_list:
                final_list = list()
                for elem in data:
                    final_list.append(_clean_html(elem))
                return final_list
            else:
                cleaner = re.compile('<.*?>')
                clean_text = re.sub(cleaner, '', data)
                return clean_text

        gathered_data = json.loads(response)
        return gathered_data

    def start_requests(self):
        base_url = 'http://api.alaedin.travel/{}/<<put your api key here>>'
        url = base_url.format('city/odata')
        yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response, city=None):
        def api_call_get(data, **kwargs):
            # todo u need to write some code here to match it with your needs
            api_response = class_utils.RestApiConnector.get(url='<your web service url>',
                                                            params=data, **kwargs)
            if api_response.status_code == 200:
                return api_response.json()
            return None

        def _clean_html(data, is_list=False):
            if is_list:
                final_list = list()
                for elem in data:
                    final_list.append(_clean_html(elem))
                return final_list
            else:
                cleaner = re.compile('<.*?>')
                clean_text = re.sub(cleaner, '', data)
                return clean_text

        def api_call_post(url, data, **kwargs):
            api_response = class_utils.RestApiConnector.post(url=url, json=data, **kwargs)
            if api_response.status_code == 200:
                return api_response.json()
            return None

        def save_images(hotel_directory, data):
            if not os.path.exists(hotel_directory+'/images'):
                os.makedirs(hotel_directory + '/images')

            dir_to_save = hotel_directory + '/images/{}'.format(gathered_data['script_data']['PlaceId'])
            if not os.path.exists(dir_to_save):
                os.makedirs(dir_to_save)
            else:
                shutil.rmtree(dir_to_save)
                os.makedirs(dir_to_save)

            for image_item in data['script_data']['Images']:
                image_url = image_item['WebsiteUrl']
                image_name = image_item['FileName']
                save_it_to = dir_to_save + '/{}'.format(image_name)
                try:
                    request.urlretrieve(image_url, save_it_to)
                except:
                    request.urlretrieve(image_url, save_it_to)
                finally:
                    pass  # no more tries XD

        if city is None:
            print(str(response.body[:100], encoding='utf-8'))
            gathered_data = json.loads(str(response.body, encoding='utf-8'))
            yield scrapy.Request(url='http://api.alaedin.travel/city/odata/<<put your api key here>>',
                                 callback=self.parse)

        _city_data = api_call_get(data={"country_hid": "CTRIR", "query": city})

        if len(_city_data) > 1:
            exception_file = open('data/exeptions.txt', 'a+')
            exception_file.write("############################ From jabama ############################\n")
            exception_file.write(">>> Please Care <<<$>>> Please Care <<<$>>> Please Care <<<$>>> Please Care <<\n")
            exception_file.write('there is 2 cities with this name {} please consider to add it to exceptions'
                                 ' list\n'.format(self.city))
            exception_file.write(">>> Please Care <<<$>>> Please Care <<<$>>> Please Care <<<$>>> Please Care <<\n")
            print(('2 city result exception {}'.format(self.city))*2)
            exit()  # in this case u have a critical error that rly needs be fixed !!! ((duplicate city))
        for lang in _city_data[0]['languages']:
            if lang['code'] == 'fa':
                url = 'https://www.jabama.com/city/{}'.format(lang['title'])
                self.first_time = False
                yield scrapy.Request(url=url, callback=self.parse)

        gathered_data = AlaeddinSpider.data_processor(response)
        save_images('data/jabama', gathered_data)

        fa_json = open('data/mapped_facilities.json', 'r', encoding='utf8')
        fa_json = json.loads(fa_json.read())

        for elem in gathered_data['script_data']['HotelAtributes']:
            _do_find = False
            for item in fa_json:
                if 'jabama_code' in item:
                    if elem['FacilityCodeId'] == int(item['jabama_code']):
                        elem['hid'] = item['hid']
                        _do_find = True
            if _do_find is False:
                print('$'*50)
                print(elem)
                print('#'*50)

        # get city hid
        city_data = api_call_get(data={"country_hid": "CTRIR", "query": self.city})
        if city_data:
            city_hid = city_data[0]['hid']
        else:
            city_hid = None
            error_statement = 'city not found: {} with url: {}'.format(gathered_data['script_data']['CityUrlKey'],
                                                                       response.url)
            print(error_statement)
            return

        endpoint_data = {
            "check_in": "14:00",
            "check_out": "12:00",
            "latitude": gathered_data['script_data']['Latitude'],
            "longitude": gathered_data['script_data']['Longitude'],
            "rating": gathered_data['script_data']['Class'],
            "room_count": None,
            "languages": [
                {
                    "code": "fa",
                    "title": gathered_data['script_data']['PlaceName'],
                    "address": gathered_data['script_data']['Address'],
                    "description": gathered_data['script_data']['Description'],
                }
            ],
            "city_hid": city_hid,
            "hotel_provider": [
                {
                    "provider_id": 110011,
                    "provider_data": {
                        "destination_type": "city"
                    }
                }
            ],
        }

        gathered_data['ours_data'] = {'city_hid': city_hid}

        # todo u need to write some code here to match it with your needs
        endpoint_result = api_call_post(url="<your web service url>", data=endpoint_data)
        if endpoint_result:
            print('{} has been pushed'.format(gathered_data['title']))
