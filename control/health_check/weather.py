#!/usr/bin/env python
"""
Regular weather data:
http://www.aviationweather.gov/dataserver
http://www.aviationweather.gov/dataserver/example?datatype=metar
Bishop regional is station KBIH (see map of stations here: http://www.aviationweather.gov/metar)
Request latest observation from station:
  http://www.aviationweather.gov/adds/dataserver_current/httpparam?dataSource=metars&requestType=retrieve&format=xml&hoursBeforeNow=3&mostRecent=true&stationString=KBIH

Ionosphere weather data:
http://services.swpc.noaa.gov/text/us-tec-total-electron-content.txt
http://services.swpc.noaa.gov/text/us-tec-uncertainty.txt

Lat: +N, -S
Lon: +E, -W
"""

import urllib2
import datetime
from StringIO import StringIO
import numpy as np
import scipy.interpolate
import xml.etree.ElementTree as ET

class GroundWeather(object):
    def __init__(self, station):
        self.station = station
        self.update()

    def update(self):
        data_url = "http://www.aviationweather.gov/adds/dataserver_current/httpparam?dataSource=metars&requestType=retrieve&format=xml&hoursBeforeNow=3&mostRecent=true&stationString=" + self.station
        response = urllib2.urlopen(data_url)
        raw_xml = response.read()
        root = ET.fromstring(raw_xml)
        metar = root.find("data").find("METAR")
        utc_str = metar.find("observation_time").text
        year = int(utc_str[:4])
        month = int(utc_str[5:7])
        day = int(utc_str[8:10])
        hour = int(utc_str[11:13])
        minute = int(utc_str[14:16])
        second = int(utc_str[17:19])
        self.utc_str = utc_str
        self.utc = datetime.datetime(year, month, day, hour, minute, second)
        self.lat = float(metar.find("latitude").text)
        self.lon = float(metar.find("longitude").text)
        self.temp_c = float(metar.find("temp_c").text)
        self.dewpoint_c = float(metar.find("dewpoint_c").text)
        self.wind_dir_degs = float(metar.find("wind_dir_degrees").text)
        self.wind_speed_kt = float(metar.find("wind_speed_kt").text)
        self.visibility_mi = float(metar.find("visibility_statute_mi").text)
        self.pressure_mb = float(metar.find("sea_level_pressure_mb").text)
        # self.sky_cover     = metar.find("sky_condition").attrib["sky_cover"] # Sometimes causes errors
        # self.dpressure_mb  = metar.find("three_hr_pressure_tendency_mb").text
        self.elevation_m = float(metar.find("elevation_m").text)


class TotalElectronContent(object):
    """See here for lots more data files: http://services.swpc.noaa.gov/text/
    """

    def __init__(self):
        self.update()

    def update(self):
        # Note: These are updated every 15 minutes
        tec_data_url = "http://services.swpc.noaa.gov/text/us-tec-total-electron-content.txt"
        tec_error_url = "http://services.swpc.noaa.gov/text/us-tec-uncertainty.txt"
        self.utc, lat, lon, tec = self.load_data_url(tec_data_url)
        self.dutc, dlat, dlon, dtec = self.load_data_url(tec_error_url)
        # TODO: These technically need to interpolate in spherical coordinates
        # Sampling function for TEC (in TECU = 1e16/m**2)
        # """ HACK disabled
        self.tecmap = scipy.interpolate.interp2d(lon, lat, tec,
                                                 kind='linear', copy=True)
        # Sampling function for TEC uncertainty (in TECU = 1e16/m**2)
        self.dtecmap = scipy.interpolate.interp2d(dlon, dlat, dtec,
                                                  kind='linear', copy=True)

    # """
    # self.tecmap  = lambda x,y: np.array([-1])
    #self.dtecmap = lambda x,y: np.array([-1])
    def load_data_url(self, url):
        """See: http://www.swpc.noaa.gov/ustec/docs/DataFormat.html
        """
        response = urllib2.urlopen(url)
        raw = response.read()
        product_key = 'Product:'
        product_str = raw[raw.find(product_key):raw.find('\n')][len(product_key):]
        date_str = product_str[:product_str.find('_')].strip()
        year = int(date_str[:4])
        month = int(date_str[4:6])
        day = int(date_str[6:8])
        hour = int(date_str[8:10])
        minute = int(date_str[10:12])
        product_utc = datetime.datetime(year, month, day, hour, minute)
        product_utc += datetime.timedelta(minutes=15)
        # Jump to start of data
        raw = raw[raw.find('\n', raw.find('#-----------')) + 1:]
        # Cut out just the Vertical data (first table)
        eor = '999'
        end = raw.find(eor)
        if end == -1:
            end = None
        raw = raw[:end]
        # Parse text data
        data = np.loadtxt(StringIO(raw))
        #data = np.genfromtxt(StringIO(raw))
        nstations = data[0, 0]
        lat = data[1:, 0] / 10.
        lon = data[0, 1:] / 10.
        tec = data[1:, 1:] / 10.
        return product_utc, lat, lon, tec


if __name__ == "__main__":
    station = "KBIH"  # Note: Bishop regional; closest to OVRO
    gnd = GroundWeather(station)
    print "[%s] GND @ %.2f,%.2f: temp %.3g C, dewpoint %.3g C, pressure %.3g atm" % (gnd.utc,
                                                                                     gnd.lon, gnd.lat,
                                                                                     gnd.temp_c,
                                                                                     gnd.dewpoint_c,
                                                                                     gnd.pressure_mb * 0.987 / 1e3)

    lon = -118.281667  # -118.282222222
    lat = 37.239777  # 37.233888889
    tec = TotalElectronContent()
    print "[%s] TEC @ %.2f,%.2f: %.3g +- %.2g x1e16/m^2" % (tec.utc,
                                                            lon, lat,
                                                            tec.tecmap(lon, lat),
                                                            tec.dtecmap(lon, lat))
