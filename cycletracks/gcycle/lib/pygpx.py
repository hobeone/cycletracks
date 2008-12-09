import sys
import os
import xml.etree.cElementTree as ET
import string
import math
import datetime
import StringIO

from gcycle.lib import glineenc
from gcycle.lib import pytcx
from gcycle.lib.average import *
import pprint
pp = pprint.PrettyPrinter(indent=2)

mainNS=string.Template("{http://www.topografix.com/GPX/1/0}$tag")

wptTag=mainNS.substitute(tag="trkpt")
timeTag=mainNS.substitute(tag="time")
elevationTag=mainNS.substitute(tag="ele")


EARTH_RADIUS = 6371 # km

def parse_zulu(s):
    return datetime.datetime(int(s[0:4]), int(s[5:7]), int(s[8:10]),
        int(s[11:13]), int(s[14:16]), int(s[17:19]))

# http://www.movable-type.co.uk/scripts/latlong.html
def calculate_distance(start_lat, start_long, end_lat, end_long):
  dLat = math.radians(end_lat - start_lat)
  dLon = math.radians(end_long - start_long)
  a = (math.sin(dLat/2.0) * math.sin(dLat/2.0) +
      math.cos(math.radians(start_lat)) * math.cos(math.radians(end_lat)) *
      math.sin(dLon/2.0) * math.sin(dLon/2.0))
  c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
  d = EARTH_RADIUS * c
  return d * 1000

def calculate_speed(start_time, start_distance, end_time, end_distance):
  tdelta = end_time - start_time
  if tdelta == 0: return 0
  return (end_distance - start_distance) / tdelta

# Assume one activity/lap per file:
def parse_gpx(filedata):
  et=ET.parse(StringIO.StringIO(filedata))

  time_points = []
  geo_points = []
  altitude_list = []
  distance_list = []
  speed_list = []

  # TODO: error on no time data
  # record time as total delta since start in seconds

  start_time = None
  for wpt in et.findall("//"+wptTag):
    geo_points.append([float(wpt.get("lat")),float(wpt.get("lon"))])
    waypoint_time = parse_zulu(wpt.findtext(timeTag))
    if start_time is None:
      start_time = waypoint_time
    time_points.append((waypoint_time - start_time).seconds)
    altitude_list.append(float(wpt.findtext(elevationTag)))
    if len(geo_points) > 1:
      distance_list.append(
          distance_list[-1] +
          calculate_distance(
            geo_points[-2][0],
            geo_points[-2][1],
            geo_points[-1][0],
            geo_points[-1][1]
          )
      )
      speed_list.append(calculate_speed(time_points[-2], distance_list[-2],
          time_points[-1], distance_list[-1]))
    else:
      distance_list.append(0)
      speed_list.append(0)

  total_ascent = 0.0
  total_descent = 0.0

  prev_altitude = altitude_list[0]
  for i in altitude_list:
    altitude_delta = i - prev_altitude
    if altitude_delta >= 0:
      total_ascent += altitude_delta
    else:
      total_descent += altitude_delta * -1
    prev_altitude = i
  total_meters = sum(distance_list)
  total_time = time_points[-1]

  lap_record = {
    'total_meters' : total_meters,
    'total_rolling_time_seconds' : total_time,
    'starttime': start_time,
    'maximum_speed': max(speed_list) * 3.6,
    'average_speed': total_meters / total_time * 3.6,  # kph,
    'total_time_seconds': total_time,
    'endtime': start_time + datetime.timedelta(seconds=time_points[-1]),
    'geo_points' : geo_points,
    'speed_list' : [ '%.2f' % s for s in speed_list],
    'altitude_list' : altitude_list,
    'distance_list' : [ '%.2f' % s for s in distance_list],
    'timepoints' : time_points,
    'total_ascent' : total_ascent,
    'total_descent' : total_descent
    }
  return lap_record
