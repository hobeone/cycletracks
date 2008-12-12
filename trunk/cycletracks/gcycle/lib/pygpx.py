import sys
import os
import xml.etree.cElementTree as ET
import string
import math
import datetime
import StringIO
import md5

from gcycle.lib import glineenc
from gcycle.lib import pytcx
from gcycle.lib.average import *
import pprint
pp = pprint.PrettyPrinter(indent=2)

mainNS=string.Template("{http://www.topografix.com/GPX/1/0}$tag")

wptTag=mainNS.substitute(tag="trkpt")
timeTag=mainNS.substitute(tag="time")
elevationTag=mainNS.substitute(tag="ele")
segmentTag=mainNS.substitute(tag="trkseg")


EARTH_RADIUS = 6371 # km

PAUSED_MIN_SPEED = 1.34112 # meters per second

def parse_zulu(s):
    return datetime.datetime(int(s[0:4]), int(s[5:7]), int(s[8:10]),
        int(s[11:13]), int(s[14:16]), int(s[17:19]))

# http://www.movable-type.co.uk/scripts/latlong.html
def calculate_distance(start_lat, start_long, end_lat, end_long):

  d = math.acos(
        math.sin(math.radians(start_lat)) *
        math.sin(math.radians(end_lat)) +
        math.cos(math.radians(start_lat)) *
        math.cos(math.radians(end_lat)) *
        math.cos(math.radians(end_long - start_long))
      ) * EARTH_RADIUS;

  return d * 1000

def calculate_speed(start_time, start_distance, end_time, end_distance):
  tdelta = end_time - start_time
  if tdelta == 0: return 0
  return (end_distance - start_distance) / tdelta

def parse_segment(segment, starting_dist = 0):
  time_points = []
  delta_time = []
  geo_points = []
  altitude_list = []
  distance_list = []
  speed_list = []
  paused_time = 0

  # TODO: error on no time data
  # record time as total delta since start in seconds

  start_time = None
  prev_time = None
  for wpt in segment.findall(wptTag):
    geo_points.append([float(wpt.get("lat")),float(wpt.get("lon"))])
    waypoint_time = parse_zulu(wpt.findtext(timeTag))
    if start_time is None:
      start_time = waypoint_time
    time_points.append((waypoint_time - start_time).seconds)
    if not delta_time:
      delta_time.append(0)
    else:
      delta_time.append((waypoint_time - prev_time).seconds)
    prev_time = waypoint_time
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
      if speed_list[-1] < PAUSED_MIN_SPEED:
        paused_time += time_points[-1] - time_points[-2]
        distance_list[-1] = distance_list[-2]
        speed_list[-1] = 0.0
    else:
      distance_list.append(starting_dist)
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
  total_meters = distance_list[-1]
  total_time = time_points[-1]

  # Weight the speeds by how long we were at that speed
  avg = sum([ row[0] * row[1] for row in map(None,speed_list, delta_time)])
  average_speed = avg / sum(delta_time) * 3.6

  rolling_time = total_time - paused_time
  lap_record = {
    'total_meters' : total_meters - starting_dist,
    'total_time_seconds': total_time,
    'total_rolling_time_seconds' : rolling_time,
    'starttime': start_time,
    'maximum_speed': max(movingAverage3(speed_list)),
    'average_speed': average_speed,
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

def parse_gpx(filedata):
  et=ET.parse(StringIO.StringIO(filedata))

  lap_records = []
  dist = 0
  for lap in et.findall("//"+segmentTag):
    lap_records.append(parse_segment(lap, starting_dist = dist))
    dist = sum([l['total_meters'] for l in lap_records])

  if not lap_records:
    raise InvalidTCXFormat(
      "Activities must have at least 1 lap over 10 meters or 2 minutes.")

  encoded_activity = pytcx.encode_activity_points(
      [l['geo_points'] for l in lap_records])
  total_meters = sum([l['total_meters'] for l in lap_records])
  total_time = sum([l['total_time_seconds'] for l in lap_records])

  average_speeds = [l['average_speed'] for l in lap_records]
  times = [l['total_rolling_time_seconds'] for l in lap_records]

  avg = sum([ row[0] * row[1] for row in map(None, average_speeds, times)])
  average_speed = avg / sum(times)

  rolling_time = sum(times)

  activity_record = {
      'name': '%s' % (lap_records[0]['starttime']),
      'total_meters': total_meters,
      'start_time': lap_records[0]['starttime'],
      'end_time': lap_records[-1]['endtime'],
      'total_time': total_time,
      'rolling_time': rolling_time,
      'average_speed': average_speed,
      'maximum_speed': max([l['maximum_speed'] for l in lap_records]),
      'total_ascent': sum([l['total_ascent'] for l in lap_records]),
      'total_descent': sum([l['total_descent'] for l in lap_records]),
      'laps': lap_records,
      'source_hash': md5.new(filedata).hexdigest(),
      'tcxdata': filedata
  }
  activity_record.update(encoded_activity)

  return activity_record

