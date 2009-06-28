import re
import os
import time
import datetime
import sys
import bz2
import md5
from gcycle.lib import glineenc
from gcycle.lib.average import *
from gcycle.lib.memoized import *
import array

reopts = (re.MULTILINE | re.DOTALL)

MINIMUM_LAP_DISTANCE = 10 # meters
MINIMUM_LAP_TIME = 60 # seconds
MAX_VALID_SPEED_PER_SECOND = 40 # 40 meters per second = ~90 mph,
                                # are you really going faster than that on
                                # your bike?

def parse_zulu(s):
    return datetime.datetime(int(s[0:4]), int(s[5:7]), int(s[8:10]),
        int(s[11:13]), int(s[14:16]), int(s[17:19]))

def seconds_delta(t1, t2):
  return int(time.mktime(t2.timetuple()) - time.mktime(t1.timetuple()))

@memoized
def make_tag_regex(tag, grouper = '.+?'):
  return re.compile("<%s>(%s)</%s>" % (tag,grouper,tag), reopts)

def getIntTagVal(string, tag, default=0):
  """Get the numeric text inside of a tag and convert it to an int"""
  val = getTagVal(string, tag, value_match='\d+?', default=default)
  return val

def getTagVal(string, tag, value_match = '.+?', default=None):
  r = make_tag_regex(tag)
  m = r.search(string)
  if m:
    return m.group(1).strip()
  return default

@memoized
def make_tag_val_regex(tag):
  return re.compile(r"<%s(?:.+)?>\s*?<Value>\s*?(\d+?)\s*?</Value>\s*?</%s>" %
      (tag,tag), reopts)

def getIntTagSubVal(string, tag, default=None):
  """Get an integer value from a tag: <tag><value>INT</value></tag>"""
  r = make_tag_val_regex(tag)
  m = r.search(string)
  if m:
    return int(m.group(1))
  else:
    return default

@memoized
def make_extension_tag_regex(value_name):
  return re.compile(r"<Extensions>\s*?<TPX(?:.+)?>\s*?<%s>\s*?(\d+?)\s*?</%s>\s*?</TPX>\s*?</Extensions>" %
      (value_name,value_name), reopts)

def getExtensionValue(string, ext_name, default=None):
  """Get an value from the extensions section of a trackpoint"""
  r = make_extension_tag_regex(ext_name)
  m = r.search(string)
  if m:
    return int(m.group(1))
  else:
    return default


def encode_activity_points(laps_points):
  points = []
  for lap in laps_points:
    points.extend(lap)
  minlat, maxlat = 90,-90
  minlong, maxlong = 180,-180
  for pt in points:
    lat,long = pt[0],pt[1]
    if lat > maxlat: maxlat = lat
    if lat < minlat: minlat = lat
    if long > maxlong: maxlong = long
    if long < minlong: minlong = long
  sw = (minlat, minlong)
  ne = (maxlat, maxlong)
  start_point = points[0]
  mid_point = points[len(points) / 2]
  end_point = points[-1]

  pts, levs = glineenc.encode_pairs(points)
  return {
      'encoded_points': pts,
      'encoded_levels': levs,
      'ne_point': '%f,%f' % ne,
      'sw_point': '%f,%f' % sw,
      'start_point': '%f,%f' % tuple(start_point),
      'mid_point': '%f,%f' % tuple(mid_point),
      'end_point': '%f,%f' % tuple(end_point),
      }

class TCXExpception(Exception):
  pass

class InvalidTCXFormat(TCXExpception):
  pass

class TrackTooShort(InvalidTCXFormat):
  pass

def joinArrayOrNone(array, joinstr=','):
  """Return a string of the array joined by joinstr or None if the the array is
  empty"""

  if array:
    array = joinstr.join(array)
  else:
    array = None
  return array

def fill_list(list, fill_data, amount):
  list.extend(
    [fill_data for i in xrange(0,amount)]
  )
  return list

def parse_lap(start_time, lap_string):
  lap = lap_string
  # weed out laps that are too short for distance or time
  total_meters = float(getTagVal(lap, 'DistanceMeters'))
  if total_meters < MINIMUM_LAP_DISTANCE:
    raise TrackTooShort('Lap is less than %i meters, ignoring' %
        MINIMUM_LAP_DISTANCE)

  total_time = int(float(getTagVal(lap, 'TotalTimeSeconds')))
  if total_time < MINIMUM_LAP_TIME:
    raise TrackTooShort('Lap is less than %i seconds' % MINIMUM_LAP_TIME)

  lap_record = {
    'total_meters': total_meters,
    'total_rolling_time_seconds' : total_time,
    'starttime': parse_zulu(start_time),
    'average_bpm': getIntTagSubVal(lap, 'AverageHeartRateBpm', 0),
    'maximum_bpm': getIntTagSubVal(lap, 'MaximumHeartRateBpm', 0),
    'calories': float(getTagVal(lap, 'Calories', 0)),
    'maximum_speed': float(getTagVal(lap, 'MaximumSpeed', 0)) * 3.6,
    'average_speed': total_meters / total_time * 3.6 # kph,
    }

  geo_points = []
  cadence_list = []
  bpm_list = []
  speed_list = []
  altitude_list = []
  timepoints = []
  distance_list = []
  power_list = []
  starttime = lap_record['starttime']
  prev_time = lap_record['starttime']
  endtime = starttime
  prev_distance = 0

  r = re.compile('<Trackpoint>(.*?)</Trackpoint>', re.MULTILINE | re.DOTALL)
  for t in r.finditer(lap):
    trackpoint = t.group()
    point_time = getTagVal(trackpoint, 'Time', None)
    if not point_time:
      raise InvalidTCXFormat("Trackpoint has no time attribute.")

    point_time = parse_zulu(point_time)
    endtime = point_time

    dist = getTagVal(trackpoint, 'DistanceMeters', None)
    timedelta = (point_time - prev_time).seconds

    if dist is None:
      # no distance delta == no speed
      speed_list.append(0)
      distance_list.append(distance_list[-1])
      timepoints.append(seconds_delta(starttime, point_time))
    else:
      dist = float(dist)
      dist_delta = dist - prev_distance
      distance_list.append(dist)
      if dist_delta == 0:
        speed_list.append(0)
        timepoints.append(seconds_delta(starttime, point_time))
      else:
        if timedelta > 0:
          timepoints.append(seconds_delta(starttime, point_time))
          raw_speed = dist_delta / timedelta
          if raw_speed > MAX_VALID_SPEED_PER_SECOND:
            if len(speed_list) > 0:
              speed_list.append(speed_list[-1])
            else:
              speed_list.append(0)
          else:
            speed_list.append(raw_speed * 3.6) # for kph
        else:
          speed_list.append(0)
          if timepoints:
            timepoints.append(timepoints[-1])
          else:
            timepoints.append(0)
      prev_distance = dist
    prev_time = point_time

    cad = getTagVal(trackpoint, 'Cadence', None)
    if cad:
      try:
        if len(cadence_list) == 0 and len(timepoints) > 0:
          cadence_list = fill_list(cadence_list, 0, len(timepoints)-1)
        cadence_list.append(int(cad))
      except ValueError, e:
        raise InvalidTCXFormat("Cadence must be an integer")
    else:
      if cadence_list:
        cadence_list.append(cadence_list[-1])
      else:
        cadence_list.append(0)

    bpm = getIntTagSubVal(trackpoint, 'HeartRateBpm', None)
    if bpm:
      if len(bpm_list) == 0 and len(timepoints) > 0:
        bpm_list = fill_list(bpm_list, 0, len(timepoints)-1)
      bpm_list.append(bpm)
    else:
      if bpm_list:
        bpm_list.append(bpm_list[-1])

    power = getExtensionValue(trackpoint, 'Watts', default=None)
    if power:
      if len(power_list) == 0 and len(timepoints) > 0:
        power_list = fill_list(power_list, 0, len(timepoints)-1)
      power_list.append(power)
    else:
      if power_list:
        power_list.append(power_list[-1])


    alt = getTagVal(trackpoint, 'AltitudeMeters', None)
    if alt:
      if len(altitude_list) == 0 and len(timepoints) > 0:
        altitude_list = fill_list(altitude_list, float(alt), len(timepoints)-1)
      altitude_list.append(float(alt))
    else:
      if altitude_list:
        altitude_list.append(altitude_list[-1])


    lat = getTagVal(trackpoint, 'LatitudeDegrees', None)
    long = getTagVal(trackpoint, 'LongitudeDegrees', None)
    if lat and long:
      if len(geo_points) == 0 and len(timepoints) > 0:
        geo_points = fill_list(geo_points,
            [float(lat),float(long)],
            len(timepoints)-1)
      geo_points.append([float(lat),float(long)])
    else:
      if geo_points:
        geo_points.append(geo_points[-1])

  max_cadence = 0
  if cadence_list:
    max_cadence = max(cadence_list)

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

  max_power = None
  if power_list:
    max_power = max(power_list)

  lap_record.update({
    'total_time_seconds': timepoints[-1],
    'endtime': endtime,
    'average_cadence': int(average(cadence_list)),
    'maximum_cadence': max_cadence,
    'bpm_list' : array.array('H', bpm_list),
    'power_list': array.array('H', power_list),
    'average_power': int(average(power_list)),
    'maximum_power': max_power,
    'geo_points' : geo_points,
    'cadence_list' : array.array('H', cadence_list),
    'speed_list' : array.array('f', speed_list),
    'altitude_list' :array.array('f',  altitude_list),
    'distance_list' : array.array('f', distance_list),
    'timepoints' : array.array('i',timepoints),
    'total_ascent' : total_ascent,
    'total_descent' : total_descent
    })
  return lap_record


def parse_tcx(filedata):
  acts = []

  r = re.compile(r'<Activity Sport="(\w+?)">(.*?)</Activity>',
      re.MULTILINE | re.DOTALL)
  for activity in r.finditer(filedata):
    r = re.compile('<Lap StartTime="(.*?)">(.*?)</Lap>',
        re.MULTILINE | re.DOTALL)
    lap_records = []
    parse_errors = []
    lap_count = 1
    activity_sport = activity.group(1)

    for l in r.finditer(activity.group()):
      # the idea with the lap is to grab or create a datapoint for every axis
      # we are interested in for each trackpoint (speed, cadence, bpm etc).
      # this way we should have an equal number of them and can match them up
      # to a the trackpoint time.
      try:
        lap_records.append(parse_lap(l.group(1), l.group(2)))
      except TCXExpception, e:
        parse_errors.append("Lap %i couldn't be parsed: %s" % (lap_count, e))

      lap_count += 1

    if not lap_records:
      raise InvalidTCXFormat(
          "Activities must have at least 1 lap over 10 meters or 2 minutes.")

    encoded_activity =  encode_activity_points(
        [l['geo_points'] for l in lap_records])

    total_meters = sum([l['total_meters'] for l in lap_records])
    total_time = sum([l['total_time_seconds'] for l in lap_records])
    rolling_time = sum([l['total_rolling_time_seconds'] for l in lap_records])

    activity_record = {
        'name': '%s-%s' % (activity_sport, lap_records[0]['starttime']),
        'sport': activity_sport,
        'total_meters': total_meters,
        'start_time': lap_records[0]['starttime'],
        'end_time': lap_records[-1]['endtime'],
        'total_time': total_time,
        'rolling_time': rolling_time,
        'average_speed': total_meters / rolling_time * 3.6,
        'maximum_speed': max([l['maximum_speed'] for l in lap_records]),
        'average_cadence':
          int(average([l['average_cadence'] for l in lap_records])),
        'maximum_cadence': max([l['maximum_cadence'] for l in lap_records]),
        'average_bpm': int(average([l['average_bpm'] for l in lap_records])),
        'maximum_bpm': max([l['maximum_bpm'] for l in lap_records]),
        'average_power': int(average([l['average_power'] for l in lap_records])),
        'maximum_power': max([l['maximum_power'] for l in lap_records]),
        'total_calories': sum([l['calories'] for l in lap_records]),
        'total_ascent': sum([l['total_ascent'] for l in lap_records]),
        'total_descent': sum([l['total_descent'] for l in lap_records]),
        'laps': lap_records,
        'source_hash': md5.new(filedata).hexdigest(),
        'tcxdata': filedata,
        'parse_errors': parse_errors,
    }
    activity_record.update(encoded_activity)

    acts.append(activity_record)

  if not acts: raise InvalidTCXFormat("No activities found.")

  return acts
