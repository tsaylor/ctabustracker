#!/bin/env python
# coding: utf-8

from datetime import datetime
import logging
import time
try:
    from urllib import urlencode
    from urllib2 import urlopen, URLError
except ImportError:
    from urllib.parse import urlencode
    from urllib.request import urlopen
    from urllib.error import URLError
from bs4 import BeautifulSoup

try:
    input = raw_input
except NameError:
    pass


"""
This module provides a thin wrapper around the CTA BusTracker API.

All objects returned by this module are simple dictionaries of the
attributes parsed from the API's XML.

For a demonstration of features, execute the module.
"""

CTA_API_VERSION = 'v1'
CTA_API_ROOT_URL = 'http://www.ctabustracker.com/bustime/api'

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


class CTABusTracker(object):

    def __init__(self, api_key, retry_urls=True, retry_attempts=3,
                 retry_delay=3, retry_backoff=2):
        self.api_key = api_key
        self.retry_urls = retry_urls
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        self.retry_backoff = retry_backoff

    def _build_api_url(self, method, **params):
        """
        Build a valid CTA API url.
        """
        params['key'] = self.api_key

        url = '%(root)s/%(version)s/%(method)s?%(params)s' % {
            'root': CTA_API_ROOT_URL,
            'version': CTA_API_VERSION,
            'method': method,
            'params': urlencode(params)}

        return url

    def _grab_url(self, url):
        """
        URLOpen wrapper with exponential back-off.

        Algorithm sourced from:
        http://www.saltycrane.com/blog/2009/11/trying-out-retry-decorator-python/
        """
        attempts_remaining = self.retry_attempts
        delay = self.retry_delay

        while attempts_remaining > 1:
            try:
                logger.debug('Fetching %s', url)
                return urlopen(url, timeout=5)
            except URLError:
                # print "%s, Retrying in %d seconds..." % (str(e), delay)
                time.sleep(delay)
                attempts_remaining -= 1
                delay *= self.retry_backoff

        # Final attempt, errors will propogate up
        return urlopen(url, timeout=5)

    def get_time(self):
        """
        Get CTA system time.

        Return a datetime object.
        """
        url = self._build_api_url('gettime')

        xml = self._grab_url(url)
        soup = BeautifulSoup(xml, features='xml')

        tag = soup.find('tm')

        return datetime.strptime(tag.string, '%Y%m%d %H:%M:%S')

    def get_vehicles(self, vehicle_ids=[], route_ids=[], time_res='s'):
        """
        Get the details of several vehicles by id or by route they're on.

        Return a dictionary of vehicle attributes.
        """
        params = {'tmres': time_res}
        if vehicle_ids:
            params['vid'] = ','.join([str(a) for a in vehicle_ids])
        else:
            params['rt'] = ','.join([str(a) for a in route_ids])

        url = self._build_api_url('getvehicles', **params)

        xml = self._grab_url(url)
        soup = BeautifulSoup(xml, features='xml')

        vehicle_tags = soup.findAll('vehicle')

        vehicle_data = [{
            'id': str(tag.vid.string),
            'last_update': datetime.strptime(
                tag.tmstmp.string, '%Y%m%d %H:%M:%S'
            ),
            'latitude': str(tag.lat.string),
            'longitude': str(tag.lon.string),
            'heading': int(tag.hdg.string),
            'pattern_id': str(tag.pid.string),
            'route_id': str(tag.rt.string),
            'destination': str(tag.des.string),
            'distance_into_route': float(tag.pdist.string),
            'delayed': bool(tag.find('dly')) and tag.dly.string == 'true'
        } for tag in vehicle_tags]

        return vehicle_data

    def get_route_vehicles(self, route_id):
        """
        Get all vehicles active on a given route.

        Return a dictionary with vehicle ids as keys. Values are dictionaries
        of vehicle attributes.
        """
        url = self._build_api_url('getvehicles', rt=route_id)

        xml = self._grab_url(url)
        soup = BeautifulSoup(xml, features='xml')

        vehicles = {}

        for tag in soup.findAll('vehicle'):
            vehicles[str(tag.vid.string)] = {
                'id': str(tag.vid.string),
                'last_update': datetime.strptime(
                    tag.tmstmp.string, '%Y%m%d %H:%M'
                ),
                'latitude': str(tag.lat.string),
                'longitude': str(tag.lon.string),
                'heading': int(tag.hdg.string),
                'pattern_id': str(tag.pid.string),
                'route_id': str(tag.rt.string),
                'destination': str(tag.des.string),
                'distance_into_route': float(tag.pdist.string),
                'delayed': bool(tag.find('dly')) and tag.dly.string == 'true'
            }

        return vehicles

    def get_routes(self):
        """
        Get all available routes.

        Return a dictionary with route ids as keys. Values are dictionaries
        of route attributes.
        """
        url = self._build_api_url('getroutes')

        xml = self._grab_url(url)
        soup = BeautifulSoup(xml, features='xml')

        routes = {}

        for tag in soup.findAll('route'):
            routes[str(tag.rt.string)] = {
                'id': str(tag.rt.string),
                'name': str(tag.rtnm.string)
                }

        return routes

    def get_route_directions(self, route_id):
        """
        Get all directions that buses travel on a given route.

        Return a list of directions (as strings).
        """
        url = self._build_api_url('getdirections', rt=route_id)

        xml = self._grab_url(url)
        soup = BeautifulSoup(xml, features='xml')

        directions = []

        for tag in soup.findAll('dir'):
            directions.append(str(tag.string))

        return directions

    def get_route_stops(self, route_id, direction):
        """
        Get all stops for a given route, traveling in a given direction.

        Return a dictionary with stop ids as keys.  Values are dictionaries
        of stop attributes.
        """
        url = self._build_api_url('getstops', rt=route_id, dir=direction)

        xml = self._grab_url(url)
        soup = BeautifulSoup(xml, features='xml')

        stops = {}

        for tag in soup.findAll('stop'):
            try:
                stops[str(tag.stpid.string)] = {
                    'id': str(tag.stpid.string),
                    'name': str(tag.stpnm.string),
                    'latitude': str(tag.lat.string),
                    'longitude': str(tag.lon.string)
                    }
            except AttributeError:
                # Stops sometimes come back without proper lat/lon attributes
                continue

        return stops

    def get_pattern(self, pattern_id):
        """
        Get a single pattern by id.

        Return a dictionary of pattern attributes.
        """
        url = self._build_api_url('getpatterns', pid=pattern_id)

        xml = self._grab_url(url)
        soup = BeautifulSoup(xml, features='xml')

        pattern_tags = soup.findAll('ptr')

        if len(pattern_tags) > 1:
            raise Exception('Multiple patterns with the same id?')

        tag = pattern_tags[0]

        pattern = {
            'id': str(tag.pid.string),
            'length': int(float(tag.ln.string)),
            'route_direction': str(tag.rtdir.string),
            'path': {}
            }

        for pt in tag.findAll('pt'):
            pattern['path'][str(pt.seq.string)] = {
                'id': str(pt.seq.string),
                'type': str(pt.typ.string),  # S = stop, W = waypoint
                'latitude': str(pt.lat.string),
                'longitude': str(pt.lon.string)
                }

            if str(pt.typ.string) == 'S':
                pattern['path'][str(pt.seq.string)]['stop_id'] = str(
                    pt.stpid.string
                )
                pattern['path'][str(pt.seq.string)]['stop_name'] = str(
                    pt.stpnm.string
                )
            else:
                pattern['path'][str(pt.seq.string)]['stop_id'] = None
                pattern['path'][str(pt.seq.string)]['stop_name'] = None

        return pattern

    def get_route_patterns(self, route_id):
        """
        Get all active patterns for a given route.

        Return a dictionary with pattern ids as keys. Values are dictionaries
        of pattern attributes.
        """
        url = self._build_api_url('getpatterns', rt=route_id)

        xml = self._grab_url(url)
        soup = BeautifulSoup(xml, features='xml')

        patterns = {}

        for tag in soup.findAll('ptr'):
            patterns[str(tag.pid.string)] = {
                'id': str(tag.pid.string),
                'length': int(float(tag.ln.string)),
                'route_direction': str(tag.rtdir.string),
                'path': {}
                }

            for pt in tag.findAll('pt'):
                patterns[str(tag.pid.string)]['path'][str(pt.seq.string)] = {
                    'id': str(pt.seq.string),
                    'type': str(pt.typ.string),  # S = stop, W = waypoint
                    'latitude': str(pt.lat.string),
                    'longitude': str(pt.lon.string)
                    }

                path_dict = (
                    patterns[str(tag.pid.string)]['path'][str(pt.seq.string)]
                )
                if str(pt.typ.string) == 'S':
                    path_dict['stop_id'] = str(pt.stpid.string)
                    path_dict['stop_name'] = str(pt.stpnm.string)
                else:
                    path_dict['stop_id'] = None
                    path_dict['stop_name'] = None

        return patterns

    def get_vehicle_predictions(self, vehicle_ids):
        """
        Get ETD/ETA predictions for a given list of vehicles.

        Return a list of predictions (dictoinaries of prediction attributes).
        """
        url = self._build_api_url(
            'getpredictions', vid=','.join(str(a) for a in vehicle_ids)
        )

        return self._parse_predictions(url)

    def get_stop_predictions(self, stop_ids):
        """
        Get ETD/ETA predictions for a given list of stops.

        Return a list of predictions (dictoinaries of prediction attributes).
        """
        url = self._build_api_url(
            'getpredictions', stpid=','.join(str(a) for a in stop_ids)
        )

        return self._parse_predictions(url)

    def _parse_predictions(self, url):
        """
        Encapsulates prediction parsing since it has multiple entry points.
        """
        xml = self._grab_url(url)
        soup = BeautifulSoup(xml, features='xml')

        predictions = []

        for tag in soup.findAll('prd'):
            p = {
                'last_update': datetime.strptime(
                    tag.tmstmp.string, '%Y%m%d %H:%M'
                ),
                'type': str(tag.typ.string),  # A = arrival, D = departure
                'stop_id': str(tag.stpid.string),
                'stop_name': str(tag.stpnm.string),
                'distance_to_destination': int(tag.dstp.string),
                'vehicle_id': str(tag.vid.string),
                'route_id': str(tag.rt.string),
                'direction': str(tag.rtdir.string),
                'destination': str(tag.des.string),
                'prediction': datetime.strptime(
                    tag.prdtm.string, '%Y%m%d %H:%M'
                ),
                'delayed': bool(tag.find('dly')) and tag.dly.string == 'true'
            }
            predictions.append(p)

        return predictions

    def get_route_service_bulletins(self, route_id, direction=None):
        """
        Get all service bulletins for a given route.

        Return a list of bulletins (dictoinaries of bulletins attributes).
        """
        if direction:
            url = self._build_api_url(
                'getservicebulletins', rt=route_id, rtdir=direction
            )
        else:
            url = self._build_api_url('getservicebulletins', rt=route_id)

        return self._parse_service_bulletins(url)

    def get_stop_service_bulletins(self, stop_id):
        """
        Get all service bulletins for a given stop.

        Return a list of bulletins (dictoinaries of bulletins attributes).
        """
        url = self._build_api_url('getservicebulletins', stpid=stop_id)

        return self._parse_service_bulletins(url)

    def _parse_service_bulletins(self, url):
        """
        Encapsulates service bulletin parsing since there are multiple ways
        of requesting this information.
        """
        xml = self._grab_url(url)
        soup = BeautifulSoup(xml, features='xml')

        bulletins = []

        for tag in soup.findAll('sb'):
            b = {
                'title': str(tag.sbj.string),
                'details_full': str(tag.dtl.string),
                'details_short': str(tag.brf.string),
                'priority': str(tag.prty.string),
                'affects': []  # if empty, affects all
                }

            if hasattr(tag, 'srvc'):
                for elem in tag.srvc:
                    # Skip non-tags
                    if not hasattr(elem, 'name'):
                        continue

                    if elem.name == 'stpid':
                        b['affects'].append(('stop', str(elem.string)))
                    elif elem.name == 'rt':
                        b['affects'].append(('route', str(elem.string)))

            bulletins.append(b)

        return bulletins


# Demo
if __name__ == "__main__":
    API_KEY = input('Enter your API Key:')
    TEST_ROUTE = input('Enter a route id (e.g. 60):')

    cbt = CTABusTracker(API_KEY)

    print('CTA system time is {}.'.format(cbt.get_time()))

    routes = cbt.get_routes()
    print('Found {} routes.'.format(len(routes)))

    dirs = cbt.get_route_directions(TEST_ROUTE)
    print('Route {} runs in {} directions.'.format(TEST_ROUTE, len(dirs)))

    vehicles = cbt.get_route_vehicles(TEST_ROUTE)
    print('Route {} has {} active vehicles.'.format(TEST_ROUTE, len(vehicles)))

    stops = cbt.get_route_stops(TEST_ROUTE, dirs[0])
    print('Route {} has {} active stops in the {} direction.'.format(
        TEST_ROUTE, len(stops), dirs[0]
    ))

    bulletins = cbt.get_route_service_bulletins(TEST_ROUTE)
    if bulletins:
        print('Route {} has {} services bulletins.'.format(
            TEST_ROUTE, len(bulletins)
        ))
    else:
        print('Route {} has no service bulletins.'.format(TEST_ROUTE))

    patterns = cbt.get_route_patterns(TEST_ROUTE)
    print('Route {} includes {} patterns.'.format(TEST_ROUTE, len(patterns)))

    predictions = cbt.get_route_predictions(TEST_ROUTE)
    print('Route {} has {} ETD/ETA predictions.'.format(
        TEST_ROUTE, len(predictions)
    ))
