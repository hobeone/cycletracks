import sys
import os
import xml.etree.cElementTree as ET
import string
import math
import datetime
import StringIO
import md5
import array

from geopy import distance

from gcycle.lib import glineenc
from gcycle.lib import pytcx
from gcycle.lib.average import *

EARTH_RADIUS = 6370000 # meters
PAUSED_MIN_SPEED = 1.34112 # meters per second
MINIMUM_LAP_DISTANCE = 10 # meters
MINIMUM_LAP_TIME = 10 # seconds

class GPXExpception(Exception):
  pass

class InvalidGPXFormat(GPXExpception):
  pass

class TrackTooShort(GPXExpception):
  pass

def calculate_speed(start_time, start_distance, end_time, end_distance):
  tdelta = end_time - start_time
  if tdelta == 0: return 0
  return (end_distance - start_distance) / tdelta * 3.6

def parse_segment(segment, tags, starting_dist = 0.0):
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
  for wpt in segment.findall(tags['wpt']):
    geo_points.append([float(wpt.get("lat")),float(wpt.get("lon"))])
    waypoint_time = pytcx.parse_zulu(wpt.findtext(tags['time']))
    if start_time is None:
      start_time = waypoint_time
    time_points.append((waypoint_time - start_time).seconds)
    if not delta_time:
      delta_time.append(0)
    else:
      delta_time.append((waypoint_time - prev_time).seconds)
    prev_time = waypoint_time
    altitude_list.append(float(wpt.findtext(tags['elevation'])))
    if len(geo_points) > 1:
      distance_list.append(
          distance_list[-1] +
          distance.distance(geo_points[-2], geo_points[-1]).meters
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

  if len(speed_list) < 3:
    # movingAverage3 needs at least 3 points
    raise TrackTooShort('Too few points in lap')

  if len(distance_list) < 2:
    # ignore segments less than 2 points or 10 meters total movement.
    # Garmin eTrex create these sometimes when warming up.
    raise TrackTooShort('Too few points in lap')

  d = distance_list[-1] - starting_dist
  if d < MINIMUM_LAP_DISTANCE:
    # Silently ignore segments less than 2 points or 10 meters total movement.
    # Garmin eTrex create these sometimes when warming up.
    raise TrackTooShort('lap too short: (%i < %i meters)' %
        (d, MINIMUM_LAP_DISTANCE))


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

  if total_time < MINIMUM_LAP_TIME:
    raise TrackTooShort('track to short (less than %s seconds)' %
        MINIMUM_LAP_TIME)

  # Weight the speeds by how long we were at that speed
  avg = sum([ row[0] * row[1] for row in map(None, speed_list, delta_time)])
  average_speed = avg / total_time

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
    'speed_list' : array.array('f', speed_list),
    'altitude_list' :array.array('f',  altitude_list),
    'distance_list' : array.array('f', distance_list),
    'timepoints' : array.array('i',time_points),
    'total_ascent' : total_ascent,
    'total_descent' : total_descent
    }
  return lap_record

def parse_gpx(filedata, version):
  """Return a dict representing an activity record."""
  et=ET.parse(StringIO.StringIO(filedata))
  mainNS=string.Template("{http://www.topografix.com/GPX/%s}$tag" % version)

  tags = {
    'wpt': mainNS.substitute(tag="trkpt"),
    'time': mainNS.substitute(tag="time"),
    'elevation': mainNS.substitute(tag="ele"),
    'segment': mainNS.substitute(tag="trkseg")
  }

  lap_records = []
  parse_errors = []
  lap_count = 1
  dist = 0.0
  for lap in et.findall("//"+tags['segment']):
    try:
      lap_records.append(parse_segment(lap, tags, starting_dist = dist))
    except GPXExpception, e:
      parse_errors.append("Lap %i couldn't be parsed: %s" % (lap_count, e))
    lap_count += 1

  dist = sum([l['total_meters'] for l in lap_records])
  if not lap_records:
    raise InvalidGPXFormat(
      "Activity does not appear to contain any useful tracks.")

  encoded_activity = pytcx.encode_activity_points(
      [l['geo_points'] for l in lap_records])
  total_meters = sum([l['total_meters'] for l in lap_records])
  total_time = sum([l['total_time_seconds'] for l in lap_records])

  average_speeds = [l['average_speed'] for l in lap_records]
  times = [l['total_rolling_time_seconds'] for l in lap_records]
  rolling_time = sum(times)

  if rolling_time < 1:
    raise InvalidGPXFormat(
      "Activity has total rolling time less than 1 second.")

  avg = sum([ row[0] * row[1] for row in map(None, average_speeds, times)])
  average_speed = avg / rolling_time

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
      'tcxdata': filedata,
      'parse_errors': parse_errors
  }
  activity_record.update(encoded_activity)

  return activity_record

