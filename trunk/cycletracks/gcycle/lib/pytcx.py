import re
import os
import datetime
import sys
from gcycle.lib import glineenc
from gcycle.lib.average import *
from gcycle.lib.memoized import *

reopts = (re.MULTILINE | re.DOTALL)

def parse_zulu(s):
    return datetime.datetime(int(s[0:4]), int(s[5:7]), int(s[8:10]),
        int(s[11:13]), int(s[14:16]), int(s[17:19]))

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
  return re.compile("<%s>\s*?<Value>\s*?(\d+?)\s*?</Value>\s*?</%s>" %
      (tag,tag), reopts)

def getIntTagSubVal(string, tag, default=None):
  """Get an integer value from a tag: <tag><value>INT</value></tag>"""
  r = make_tag_val_regex(tag)
  m = r.search(string)
  if m:
    return int(m.group(1))
  else:
    return default

def encode_activity_points(laps_points):
  points = []
  for lap in laps_points:
    points.extend(lap.split(':'))
  newp = [ (float(p.split(',')[0]), float(p.split(',')[1])) for p in points]
  minlat, maxlat = 90,-90
  minlong, maxlong = 180,-180
  for pt in newp:
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

  pts, levs = glineenc.encode_pairs(newp)
  return {
      'encoded_points': pts,
      'encoded_levels': levs,
      'ne_point': '%s,%s' % (ne[0], ne[1]),
      'sw_point': '%s,%s' % (sw[0], sw[1]),
      'start_point': str(start_point),
      'mid_point': str(mid_point),
      'end_point': str(end_point)
      }

class TCXExpception(Exception):
  pass

class InvalidTCXFormat(TCXExpception):
  pass

def joinArrayOrNone(array, joinstr=','):
  """Return a string of the array joined by joinstr or None if the the array is
  empty"""

  if array:
    array = joinstr.join(array)
  else:
    array = None
  return array


def parse_lap(start_time, lap_string):
  lap = lap_string
  # weed out laps that are too short for distance or time
  total_meters = float(getTagVal(lap, 'DistanceMeters'))
  if total_meters < 10: return None

  total_time = int(float(getTagVal(lap, 'TotalTimeSeconds')))
  if total_time < 60: return None

  lap_record = {
    'total_meters': total_meters,
    'total_rolling_time_seconds' : total_time,
    'starttime': parse_zulu(start_time),
    'average_bpm': getIntTagSubVal(lap, 'AverageHeartRateBpm'),
    'maximum_bpm': getIntTagSubVal(lap, 'MaximumHeartRateBpm'),
    'calories': float(getTagVal(lap, 'Calories')),
    'maximum_speed': float(getTagVal(lap, 'MaximumSpeed')) * 3.6,
    'average_speed': total_meters / total_time * 3.6 # kph,
    }

  geo_points = []
  cadence_list = []
  bpm_list = []
  speed_list = []
  altitude_list = []
  timepoints = []
  starttime = None
  prev_time = None
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
    if starttime is None:
      starttime = point_time
      prev_time = point_time

    dist = getTagVal(trackpoint, 'DistanceMeters', None)
    timedelta = (point_time - prev_time).seconds

    if dist is None:
      # no distance delta == no speed
      speed_list.append(0)
      timepoints.append((point_time - starttime).seconds)
    else:
      dist = float(dist)
      dist_delta = dist - prev_distance
      if dist_delta == 0:
        speed_list.append(0)
        timepoints.append((point_time - starttime).seconds)
      else:
        if timedelta > 0:
          timepoints.append((point_time - starttime).seconds)
          speed_list.append(dist_delta / timedelta * 3.6) # for kph
        else:
          if timepoints:
            timepoints.append(timepoints[-1])
          else:
            timepoints.append(0)

      prev_distance = dist
    prev_time = point_time

    cad = getTagVal(trackpoint, 'Cadence', None)
    if cad:
      try:
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
      bpm_list.append(str(bpm))
    else:
      if bpm_list:
        bpm_list.append(bpm_list[-1])

    alt = getTagVal(trackpoint, 'AltitudeMeters', None)
    if alt:
      altitude_list.append(alt)
    else:
      if altitude_list:
        altitude_list.append(altitude_list[-1])

    lat = getTagVal(trackpoint, 'LatitudeDegrees', None)
    long = getTagVal(trackpoint, 'LongitudeDegrees', None)
    if lat and long:
      geo_points.append('%s,%s' % (lat,long))
    else:
      if geo_points:
        geo_points.append(geo_points[-1])

  max_cadence = 0
  if cadence_list:
    max_cadence = max(cadence_list)

  lap_record.update({
    'total_time_seconds': timepoints[-1],
    'endtime': endtime,
    'average_cadence': int(average(cadence_list)),
    'maximum_cadence': max_cadence,
    'bpm_list' : joinArrayOrNone(bpm_list),
    'geo_points' : joinArrayOrNone(geo_points,':'),
    'cadence_list' : joinArrayOrNone([str(c) for c in cadence_list]),
    'speed_list' : joinArrayOrNone([ '%.2f' % s for s in speed_list]),
    'altitude_list' : joinArrayOrNone(altitude_list),
    'timepoints' : joinArrayOrNone([str(t) for t in timepoints]),
    })
  return lap_record


def parse_tcx(filedata):
  acts = []

  r = re.compile('<Activity Sport="(\w+?)">(.*?)</Activity>',
      re.MULTILINE | re.DOTALL)
  for activity in r.finditer(filedata):
    r = re.compile('<Lap StartTime="(.*?)">(.*?)</Lap>',
        re.MULTILINE | re.DOTALL)
    lap_records = []
    activity_sport = activity.group(1)

    for l in r.finditer(activity.group()):
      # the idea with the lap is to grab or create a datapoint for every axis
      # we are interested in for each trackpoint (speed, cadence, bpm etc).
      # this way we should have an equal number of them and can match them up
      # to a the trackpoint time.
      lap_record = parse_lap(l.group(1), l.group(2))
      if lap_record:
        lap_records.append(lap_record)

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
        'total_calories': sum([l['calories'] for l in lap_records]),
        'laps': lap_records,
    }
    activity_record.update(encoded_activity)

    acts.append(activity_record)

  if not acts: raise InvalidTCXFormat("No activities found.")

  return acts
