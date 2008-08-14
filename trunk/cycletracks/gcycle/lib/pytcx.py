import re
import os
import datetime
import sys
from gcycle.lib import glineenc

reopts = (re.MULTILINE | re.DOTALL)

def parse_zulu(s):
    return datetime.datetime(int(s[0:4]), int(s[5:7]), int(s[8:10]),
        int(s[11:13]), int(s[14:16]), int(s[17:19]))

class memoized(object):
   """Decorator that caches a function's return value each time it is called.
   If called later with the same arguments, the cached value is returned, and
   not re-evaluated.
   """
   def __init__(self, func):
      self.func = func
      self.cache = {}
   def __call__(self, *args):
      try:
         return self.cache[args]
      except KeyError:
         self.cache[args] = value = self.func(*args)
         return value
      except TypeError:
         # uncachable -- for instance, passing a list as an argument.
         # Better to not cache than to blow up entirely.
         return self.func(*args)
   def __repr__(self):
      """Return the function's docstring."""
      return self.func.__doc__

@memoized
def make_tag_regex(tag):
  return re.compile("<%s>(.+?)</%s>" % (tag,tag), reopts)

def getTagVal(string, tag, default='0'):
  r = make_tag_regex(tag)
  m = r.search(string)
  if m:
    return m.group(1)
  return default

@memoized
def make_tag_val_regex(tag):
  return re.compile("<%s>\s*?<Value>(\d+?)</Value>\s*?</%s>" % (tag,tag),
      reopts)

def getTagSubVal(string, tag, default='0'):
  r = make_tag_val_regex(tag)
  m = r.search(string)
  if m:
    return m.group(1)
  else:
    return default

def average(array):
  if len(array) == 0: return 0
  return (sum(array) / len(array))

def encode_activity_points(laps_points):
  points = []
  for lap in laps_points:
    points.extend(lap.split('\n'))
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
  return pts, levs, ne, sw, start_point, mid_point, end_point

class UnknownTCXExpception(Exception):
  pass

def joinArrayOrNone(array, joinstr=','):
  if array:
    array = joinstr.join(array)
  else:
    array = None
  return array


def parse_lap(lap_match):
  lap = lap_match.group(2)
  # weed out laps that are too short for distance or time
  total_meters = float(getTagVal(lap, 'DistanceMeters'))
  if total_meters < 10: return None

  total_time = int(float(getTagVal(lap, 'TotalTimeSeconds')))
  if total_time < 60: return None

  lap_record = {
    'total_meters': total_meters,
    'total_rolling_time_seconds' : total_time,
    'starttime': parse_zulu(lap_match.group(1)),
    'average_bpm': float(getTagSubVal(lap, 'AverageHeartRateBpm')),
    'maximum_bpm': float(getTagSubVal(lap, 'MaximumHeartRateBpm')),
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
  starttime = lap_record['starttime']
  prev_time = starttime
  endtime = starttime
  prev_distance = 0

  r = re.compile('<Trackpoint>(.*?)</Trackpoint>', re.MULTILINE | re.DOTALL)
  for t in r.finditer(lap):
    trackpoint = t.group()
    point_time = getTagVal(trackpoint, 'Time', None)
    if not point_time:
      continue

    point_time = parse_zulu(point_time)
    endtime = point_time

    dist = getTagVal(trackpoint, 'DistanceMeters', None)

    if dist is None:
      # no distance delta == no speed
      speed_list.append(0)
    else:
      dist = float(dist)
      dist_delta = dist - prev_distance
      if dist_delta == 0:
        speed_list.append(0)
      else:
        timedelta = (point_time - prev_time).seconds
        if timedelta > 0:
          timepoints.append(int((point_time - starttime).seconds))
          speed_list.append(dist_delta / timedelta * 3.6) # for kph
        else:
          timepoints.append(0)

      prev_distance = dist
    prev_time = point_time

    cad = getTagVal(trackpoint, 'Cadence', None)
    if cad:
      try:
        cadence_list.append(int(cad))
      except ValueError, e:
        raise UnknownTCXExpception("Cadence must be an integer")
    else:
      if cadence_list:
        cadence_list.append(cadence_list[-1])
      else:
        cadence_list.append(0)

    bpm = getTagSubVal(trackpoint, 'HeartRateBpm', None)
    if bpm:
      bpm_list.append(bpm)
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
      geo_points.append('%s, %s' % (lat,long))
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
    'geo_points' : joinArrayOrNone(geo_points,'\n'),
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
      lap_record = parse_lap(l)
      if lap_record:
        lap_records.append(lap_record)

    if not lap_records:
      raise UnknownTCXExpception("Activities must have at least 1 lap over 10 meters or 2 minutes long.")

    total_meters = [0 + l['total_meters'] for l in lap_records][0]
    total_time = [0 + l['total_time_seconds'] for l in lap_records][0]
    rolling_time = [0 + l['total_rolling_time_seconds'] for l in lap_records][0]

    pts, levs, ne, sw, start_point, mid_point, end_point = encode_activity_points(
        [l['geo_points'] for l in lap_records])
    activity_record = {
        'name': '%s-%s' % (activity_sport, lap_records[0]['starttime']),
        'sport': activity_sport,
        'total_meters': total_meters,
        'start_time': lap_records[0]['starttime'],
        'end_time': lap_records[0]['endtime'],
        'total_time': total_time,
        'rolling_time': rolling_time,
        'average_speed': total_meters / rolling_time * 3.6,
        'maximum_speed': max([l['maximum_speed'] for l in lap_records]),
        'average_cadence': average([l['average_cadence'] for l in lap_records]),
        'maximum_cadence': average([l['maximum_cadence'] for l in lap_records]),
        'average_bpm': average([l['average_bpm'] for l in lap_records]),
        'maximum_bpm': max([l['maximum_bpm'] for l in lap_records]),
        'total_calories': [0 + l['calories'] for l in lap_records][0],
        'laps': lap_records,
        'start_point' : start_point,
        'mid_point' : mid_point,
        'end_point' : end_point,
        'encoded_points' : pts,
        'encoded_levels' : levs,
        'ne_point' : '%s,%s' % (ne[0], ne[1]),
        'sw_point' : '%s,%s' % (sw[0], sw[1]),
        }
    acts.append(activity_record)
 
  if not acts:
    raise UnknownTCXExpception("No activities found.")

  return acts
