from unittest.mock import patch
from ctabustracker import CTABusTracker
import datetime


@patch('ctabustracker.bustracker.urlopen')
def test_get_vehicle(urlopen_mock):
    vehicle_response = '''<bustime-response>
<vehicle>
<vid>1870</vid>
<tmstmp>20171112 20:07:47</tmstmp>
<lat>41.9783533387265</lat>
<lon>-87.68994619078555</lon>
<hdg>334</hdg>
<pid>1180</pid>
<rt>49</rt>
<des>Berwyn</des>
<pdist>83642</pdist>
<dly>true</dly>
<tablockid>49 -503</tablockid>
<tatripid>67</tatripid>
<zone/>
</vehicle>
</bustime-response>'''
    urlopen_mock.return_value = vehicle_response
    c = CTABusTracker('api_key')
    response = c.get_vehicles(vehicle_ids=[1870])
    assert response[0] == {
        'id': '1870',
        'last_update': datetime.datetime(2017, 11, 12, 20, 7, 47),
        'latitude': '41.9783533387265',
        'longitude': '-87.68994619078555',
        'heading': 334,
        'pattern_id': '1180',
        'route_id': '49',
        'destination': 'Berwyn',
        'distance_into_route': 83642.0,
        'delayed': True
    }

    vehicle_response = '''<bustime-response>
<vehicle>
<vid>1870</vid>
<tmstmp>20171112 20:07:47</tmstmp>
<lat>41.9783533387265</lat>
<lon>-87.68994619078555</lon>
<hdg>334</hdg>
<pid>1180</pid>
<rt>49</rt>
<des>Berwyn</des>
<pdist>83642</pdist>
<tablockid>49 -503</tablockid>
<tatripid>67</tatripid>
<zone/>
</vehicle>
</bustime-response>'''
    urlopen_mock.return_value = vehicle_response
    c = CTABusTracker('api_key')
    response = c.get_vehicles(vehicle_ids=[1870])
    assert response[0] == {
        'id': '1870',
        'last_update': datetime.datetime(2017, 11, 12, 20, 7, 47),
        'latitude': '41.9783533387265',
        'longitude': '-87.68994619078555',
        'heading': 334,
        'pattern_id': '1180',
        'route_id': '49',
        'destination': 'Berwyn',
        'distance_into_route': 83642.0,
        'delayed': False
    }
