import scrapy
import os
import shutil
import re
import pymongo
import json

from urllib import request
from scrapy.selector import Selector
from common import class_utils
from DataBase.models import Hotel as HotelModel

class QuotesSpider(scrapy.Spider):
    def __init__(self, city=None, **kwargs):
        self.city = city
        self.first_time = True
        super().__init__(**kwargs)
    handle_httpstatus_list = [404]
    name = "hotelyar"
    list_of_mis_cities = list()

    @staticmethod
    def data_processor(response):
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

        gathered_data = dict()
        gathered_data['hotel_id'] = int(re.findall('[\S]+hotel/([\d]+)/[\S]+', response.url)[0])
        gathered_data['title'] = Selector(text=response.body).xpath('//h1/text()').extract()[0]
        gathered_data['city'] = \
            response.xpath('//span[@itemprop="name"]/text()').extract()[1].replace('هتل های', '').strip(' ')
        try:
            gathered_data['address'] = _clean_html(response.css('span.hotel-lt-details span').extract()[0])
        except:
            gathered_data['address'] = None
        # extracting images
        gathered_data['imgs'] = response.css('ul.hotel-single-slider li img').extract()
        for item in gathered_data['imgs']:
            imgs_list = list()
            new_item = re.search("(?P<url>https?://[^\s]+jpg)", item).group("url")
            imgs_list.append(new_item)

        # extracting description
        try:
            gathered_data['description_title'] = response.css('h2.heading::text').extract()[0]
            gathered_data['description'] = _clean_html(response.css('div.hotel-single-desc p').extract()[0])
        except:
            gathered_data['description_title'] = None
            gathered_data['description'] = None

        try:
            gathered_data['important_points_title'] = response.css('h2.heading::text').extract()[1]
            gathered_data['important_points'] = _clean_html(response.css('div.hotel-single-desc p').extract()[1])
        except:
            gathered_data['important_points_title'] = None
            gathered_data['important_points'] = None

        gathered_data['not_available_facilities'] = _clean_html(response.css('div.mt-40px li').extract(), is_list=True)
        _temp = _clean_html(response.css('ul.hotel-single-facilities li').extract(), is_list=True)
        mapped_facilities = json.loads(open('data/mapped_facilities.json', 'r').read())
        list_of_avil_facils = list()
        for item in _temp:
            if item not in gathered_data['not_available_facilities']:
                for facil in mapped_facilities:
                    if "hotelyar_code" in facil:
                        if facil['hotelyar_code'] == item:
                            list_of_avil_facils.append({'facility': item, 'hid': facil['hid']})

        gathered_data['facilities'] = list_of_avil_facils
        gathered_data['rating'] = response.css('div #1397 div.skill-bar-percent').extract()
        _temp = list()
        gathered_data['rating_indexs'] = list()
        for year in range(1390, 1398):
            try:
                item_addr = 'div #{} div.skill-bar-percent'.format(year)
                gathered_data['rating'] = response.css(item_addr).extract()
                for rate in gathered_data['rating']:
                    _temp.append(_clean_html(rate).strip('%'))
                gathered_data['rating_indexs'].append({str(year): _temp})

            except:
                print('there is no data for {}'.format(year))
            _temp = list()
        try:
            gathered_data['total_rating'] = response.css('div.ratingValue span').extract()
            gathered_data['total_rating'] = float(re.search('[\d+][.]?[\d+]?',
                                                  gathered_data['total_rating'][0]).group(0))
        except:
            gathered_data['total_rating'] = None
        try:
            gathered_data['total_number_of_votes'] = int(_clean_html(response.css('div.ratingValue span').extract()[2]))
        except:
            gathered_data['total_number_of_votes'] = None

        try:
            _temp = None
            _temp = re.search('(latitude["][\s][:][\s]["])([\d]+[.][\d]+["])', str(response.body)).group(0)
            gathered_data['latitude'] = re.search('[\d]+[.][\d]+', _temp).group(0)
            _temp = None
            _temp = re.search('(longitude["][\s][:][\s]["])([\d]+[.][\d]+["])', str(response.body)).group(0)
            gathered_data['longitude'] = re.search('[\d]+[.][\d]+', _temp).group(0)
        except:
            gathered_data['latitude'] = None
            gathered_data['longitude'] = None

        return gathered_data

    def start_requests(self):
        path = 'data/hotelyar'
        if os.path.exists(path):
            shutil.rmtree(path)
        os.makedirs(path)

        HotelModel.drop_collection()
        yield scrapy.Request(url='https://hotelyar.com/hotel/0/', callback=self.parse)

    def parse(self, response):
        def api_call_get(data, **kwargs):
            api_response = class_utils.RestApiConnector.get(url='<your web service url>', params=data, **kwargs)
            if api_response.status_code == 200:
                return api_response.json()
            return None

        def api_call_post(url, data, **kwargs):
            api_response = class_utils.RestApiConnector.post(url=url, json=data, **kwargs)
            if api_response.status_code == 200:
                return api_response.json()
            return None

        if self.city is not None and self.first_time:
            city_list = list()
            other_cities_list = list()
            _temp_list = response.xpath('/html/body/div/div[2]/div[2]/div/div/div/div[1]/a/@title').extract()
            for item in _temp_list:
                item = item[13:]
                city_list.append(item)
            del _temp_list
            _temp_list =\
                response.xpath('//html/body/div/div[2]/div[2]/div/div/div[90]/div[2]/div/div/table//a/text()').extract()
            for item in _temp_list:
                other_cities_list.append(item.split(' ')[-1])

            _city_data = api_call_get(data={"country_hid": "CTRIR", "query": self.city})
            for lang in _city_data[0]['languages']:
                if lang['code'] == 'fa':
                    target_urls = list()
                    for elem_id in range(0, len(city_list)):
                        if city_list[elem_id] == lang['title']:
                            target_urls = response.xpath(
                                '/html/body/div/div[2]/div[2]/div/div/div[{}]/div[2]/div/div/table/'
                                '/a/@href'.format(elem_id+1)).extract()
                    for elem in other_cities_list:
                        if elem == lang['title']:
                            other_target_urls = \
                                response.xpath('//html/body/div/div[2]/div[2]/div/div/div[90]/div[2]'
                                               '/div/div/table//a/text()').extract()
                            for item_id in range(0, len(other_target_urls)):
                                if lang['title'] in other_target_urls[item_id]:
                                    yield scrapy.Request(
                                        url=response.xpath('//html/body/div/div[2]/div[2]/div/div/div[90]/div[2]'
                                                           '/div/div/table//a/@href').extract()[item_id])

                    for url in target_urls:
                        yield scrapy.Request(url=url, callback=self.parse)

        if self.city is None:
            city_list = list()
            other_cities_list = list()
            _temp_list = response.xpath('/html/body/div/div[2]/div[2]/div/div/div/div[1]/a/@title').extract()
            for item in _temp_list:
                item = item[13:]
                city_list.append(item)
            del _temp_list
            _temp_list = \
                response.xpath('//html/body/div/div[2]/div[2]/div/div/div[90]/div[2]/div/div/table//a/text()').extract()
            for item in _temp_list:
                other_cities_list.append(item.split(' ')[-1])
                target_urls = list()
                for elem_id in range(0, len(city_list)):
                    target_urls = response.xpath('/html/body/div/div[2]/div[2]/div/div/div[{}]/div[2]/div/div/table/'
                                                 '/a/@href'.format(elem_id + 1)).extract()
                for elem in other_cities_list:
                    other_target_urls = \
                        response.xpath(
                            '//html/body/div/div[2]/div[2]/div/div/div[90]/div[2]/div/div/table//a/text()').extract()
                    for item_id in range(0, len(other_target_urls)):
                        yield scrapy.Request(url=response.xpath('//html/body/div/div[2]/div[2]/div/div/div[90]/div[2]'
                                                                '/div/div/table//a/@href').extract()[item_id])

                    for url in target_urls:
                        yield scrapy.Request(url=url, callback=self.parse)

        print(response.url)
        if response.status != 200 or ('city' in response.url):
            print('%'*50)
            self.log('there is problem with url: {}'.format(response))

        else:
            def save_images(hotel_directory, data):
                os.makedirs(hotel_directory+'/images')
                for image_item in data['imgs']:
                    image_url = re.search("(?P<url>https?://[^\s]+[jpg-png])", image_item).group("url")
                    image_name = os.path.basename(image_url)
                    dir_to_save = hotel_directory+'/images/{}'.format(image_name)
                    try:
                        request.urlretrieve(image_url, dir_to_save)
                    except:
                        request.urlretrieve(image_url, dir_to_save)
                    finally:
                        pass

            print('$$$$$$$$$$$$$$$$$$')
            gathered_data = QuotesSpider.data_processor(response)
            print('hotel {} has been spidered XD HAHA'.format(gathered_data['title']))

            hotel_dir = 'data/hotelyar/{}'.format(gathered_data['hotel_id'])
            os.makedirs(hotel_dir)
            main_file = hotel_dir + '/%s.html' % gathered_data['title']
            with open(main_file, 'w', ) as f:
                f.write(response.body.decode("utf-8"))
                f.close()
            self.log('Saved file %s' % main_file)

            save_images(hotel_dir, gathered_data)

            city_data = api_call_get(data={"country_hid": "CTRIR", "query": gathered_data['city']})
            if city_data and len(city_data) == 1:
                city_hid = city_data[0]['hid']
            else:
                error_statement = 'city not found: {} with url: {}'.format(gathered_data['city'], response.url)
                print(error_statement)
                return

            endpoint_data = {
                "check_in": "14:00",
                "check_out": "12:00",
                "latitude": gathered_data['latitude'],
                "longitude": gathered_data['longitude'],
                "rating": gathered_data['total_rating'],
                "room_count": None,
                "languages": [
                    {
                        "code": "fa",
                        "title": gathered_data['title'],
                        "address": gathered_data['address'],
                        "description": gathered_data['description'],
                    }
                ],
                "city_hid": city_hid,
            }

            client = pymongo.MongoClient('localhost', 27017)
            db = client['test-database']
            try:
                db.get_collection('hotelyar')
            except:
                db.create_collection('hotelyar')

            gathered_data['ours_data'] = {'city_hid': city_hid}
            hotelyardb = db.hotelyar
            hotelyardb.insert_one(gathered_data)

            # todo u need to write some code here to match it with your needs
            endpoint_result = api_call_post(url="<your web service url>", data=endpoint_data)
            if endpoint_result:
                print('{} has been pushed'.format(gathered_data['title']))

    print(list_of_mis_cities)
