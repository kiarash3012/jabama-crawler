import scrapy
import json
import re
import os
import shutil
import pymongo
import requests

from urllib import request
from common import class_utils


class QuotesSpider(scrapy.Spider):
    def __init__(self, city=None, **kwargs):
        self.city = city
        self.first_time = True
        super().__init__(**kwargs)
    name = "jabama"
    all_data = list()

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

        # call this part if u need to build your own custom hotel list although there is default list here with
        # project (have all hotels in it). this is part one (u should active part 2 and 3 to make it work)
        # (activate mean that u call that function and comment rest of code)
        def make_hotel_list():
            hotel_list = response.css('div.row script::text').extract()[1]
            hotel_list = hotel_list[22:len(hotel_list)-3]
            hotel_list = json.loads(hotel_list)
            for hotel in hotel_list['searchResultRowViewModelList']:
                cls.gathered_data['hotel_list'].append(hotel)
            for hotel in cls.gathered_data['hotel_list']:
                cls.gathered_data['hotel_links'].append(hotel['Url'])

        # scrap hotels clean data
        hotel_data = response.xpath('//script[@type="application/ld+json"]/text()').extract()
        clean_hotel_data = str(hotel_data[0]).replace('\n', '')
        clean_hotel_data = str(clean_hotel_data).replace('\r', '')
        try:
            clean_hotel_data = json.loads(clean_hotel_data)
        except:
            clean_hotel_data = ''
        gathered_data = {"hotel_data": clean_hotel_data}
        scripts_list = response.css('script').extract()
        for script in scripts_list:
            if 'hotelDetailResult' in script:
                script = script[38:-87]
                script = script.replace('\n', '')
                script = script.replace('\r', '')
                script = _clean_html(script)
                try:
                    script_in_json = json.loads(script)
                except:
                    script_in_json = ''
                gathered_data['script_data'] = script_in_json
        return gathered_data

    def start_requests(self):
        # part 2
        def make_list_of_all_hotels():
            list_of_cites = json.loads(open('DataBase/list-of-cites.json').read())
            _base_url = 'https://www.jabama.com/city/{}-hotels/'
            for city in list_of_cites:
                _url = _base_url.format(city['slug'])
                yield scrapy.Request(url=_url, callback=self.parse)

        # organise dir
        gathered_data = dict()
        gathered_data['hotel_list'] = list()
        gathered_data['hotel_links'] = list()

        # part 3
        # base_url = 'https://www.jabama.com'
        # if self.city is None:
        #     # capture made links
        #     log_file = open('data/jabama/log.txt', 'r')
        #     json_file = json.loads(log_file.read())
        #
        #     c = 0
        #     for sub_url in json_file:
        #         # c += 1
        #         if c >= 3:
        #             break
        #         url = base_url + sub_url
        #         yield scrapy.Request(url=url, callback=self.parse)
        # else:
        url = 'https://www.jabama.com/'
        yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        def api_call_get(data, **kwargs):
            api_response = class_utils.RestApiConnector.get(url='<your web service url>', params=data, **kwargs)
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
                    pass

        # if u want to have extra logs here is the code
        # def make_log():
        #     log_file = open('data/jabama/log.txt', 'w+')
        #     json_file = json.dumps(gathered_data['hotel_links'])
        #     log_file.write(str(json_file))
        #     log_file.close()
        #     log_file = open('data/jabama/log.txt', 'r')
        #     json_file2 = json.loads(log_file.read())
        #     print(len(json_file2))

        if self.city is None and self.first_time is True:
            r = requests.get('https://www.jabama.com/sitemap/iran').content
            a = re.findall("(http|https)://([\w_-]+(?:(?:\.[\w_-]+)+))([\w.,@?^=%&:/~+#-]*[\w@?^=%&/~+#-])?", str(r))
            for url in a:
                if 'hotel' in url[2]:
                    url_to_get = url[0] + '://' + url[1] + url[2]
                    yield scrapy.Request(url=url_to_get, callback=self.parse)
            self.first_time = False
            return

        if self.city is not None and self.first_time is True:
            _city_data = api_call_get(data={"country_hid": "CTRIR", "query": self.city})
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
            return
        if "city" in response.url:
            hotel_list = response.css('div.row script::text').extract()[1]
            hotel_list = hotel_list[22:len(hotel_list) - 3]
            hotel_list = json.loads(hotel_list)
            for item in hotel_list['searchResultRowViewModelList']:
                if 'villa' not in item['Url']:
                    url = 'https://www.jabama.com' + item['Url']
                    yield scrapy.Request(url=url, callback=self.parse)
            return

        gathered_data = QuotesSpider.data_processor(response)
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

        # get city hid, hid our way of uniquate of elements
        city_data = api_call_get(data={"country_hid": "CTRIR", "query": self.city})
        if city_data:
            city_hid = city_data[0]['hid']
        else:
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
        }

        client = pymongo.MongoClient('localhost', 27017)
        db = client['test-database']
        try:
            db.get_collection('jabama')
        except:
            db.create_collection('jabama')

        gathered_data['ours_data'] = {'city_hid': city_hid}
        jabamadb = db.jabama
        jabamadb.insert_one(gathered_data)

        # todo u need to write some code here to match it with your needs
        endpoint_result = api_call_post(url="<your web service url>", data=endpoint_data)
        if endpoint_result:
            print('{} has been pushed'.format(gathered_data['title']))
