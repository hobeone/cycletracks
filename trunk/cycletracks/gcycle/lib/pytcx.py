import re
import os
import datetime
import sys

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

def getTagSubVal(string, tag):
  r = make_tag_val_regex(tag)
  m = r.search(string)
  if m:
    return m.group(1)
  else:
    return '0'

def average(array):
  if len(array) == 0: return 0
  return (sum(array) / len(array))

class UnknownTCXExpception(Exception):
  pass

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
      lap = l.group(2)
      starttime = l.group(1)
      starttime = parse_zulu(starttime)
      total_time = float(getTagVal(lap, 'TotalTimeSeconds'))
      total_meters = float(getTagVal(lap, 'DistanceMeters'))
      max_speed = float(getTagVal(lap, 'MaximumSpeed')) * 3.6
      avg_speed = total_meters / total_time * 3.6 # kph
      calories = float(getTagVal(lap, 'Calories'))
      cadence = float(getTagVal(lap, 'Cadence'))
      max_bpm =  float(getTagSubVal(lap, 'MaximumHeartRateBpm'))
      avg_bpm = float(getTagSubVal(lap, 'AverageHeartRateBpm'))

      geo_points = []
      cadence_list = []
      bpm_list = []
      speed_list = []
      altitude_list = []
      timepoints = []
      prev_time = starttime
      prev_distance = 0

      r = re.compile('<Trackpoint>(.*?)</Trackpoint>',
          re.MULTILINE | re.DOTALL)
      for t in r.finditer(lap):
        trackpoint = t.group()
        point_time = getTagVal(trackpoint, 'Time')
        point_time = parse_zulu(point_time)


        dist = getTagVal(trackpoint, 'DistanceMeters', None)
        if dist != None:
          if point_time <= starttime:
            # sometimes the first points has a timestamp 1 second or more before
            # the lap timestamp
            timepoints.append(0)
          else:
            timepoints.append((point_time - starttime).seconds)

          dist = float(dist)
          tdelta = (point_time - prev_time).seconds
          if tdelta == 0:
            speed_list.append(0)
          else:
            speed = (dist - prev_distance) / tdelta
            speed = speed * 3.6 # kph from mps

            speed_list.append(speed)
          prev_distance = dist

        else:
          speed_list.append(0)
        prev_time = point_time

        cad = getTagVal(trackpoint, 'Cadence')
        if cad != None:
          cadence_list.append(int(cad))
        else:
          cadence_list.append(cadence_list[-1])

        alt = getTagVal(trackpoint, 'AltitudeMeters')
        if alt != None:
          altitude_list.append(alt)
        else:
          altitude_list.append(altitude_list[-1])

        lat = getTagVal(trackpoint, 'LatitudeDegrees', None)
        long = getTagVal(trackpoint, 'LongitudeDegrees', None)
        if lat and long:
          geo_points.append('%s, %s' % (lat,long))
        else:
          if geo_points:
            geo_points.append(geo_points[-1])

        bpm_list.append(getTagSubVal(trackpoint, 'HeartRateBpm'))

      endtime = prev_time
      max_cadence = 0.0
      if cadence_list:
        max_cadence = max(cadence_list)
      lap_record = {
        'total_meters': total_meters,
        'total_rolling_time_seconds' : total_time,
        'total_time_seconds': float(timepoints[-1]),
        'starttime': starttime,
        'endtime': endtime,
        'average_cadence': float(cadence),
        'maximum_cadence': float(max_cadence),
        'average_bpm': avg_bpm,
        'maximum_bpm': max_bpm,
        'calories': calories,
        'maximum_speed': max_speed,
        'average_speed': avg_speed,
        'bpm_list' : ','.join(bpm_list),
        'geo_points' : '\n'.join(geo_points),
        'cadence_list' : ','.join([str(c) for c in cadence_list]),
        'speed_list' : ','.join([ '%.2f' % s for s in speed_list]),
        'altitude_list' : ','.join(altitude_list),
        'timepoints' : ','.join([str(t) for t in timepoints]),
        }
      lap_records.append(lap_record)

    if not lap_records:
      raise UnknownTCXExpception("Activities must have at least 1 lap.")

    total_meters = [0 + l['total_meters'] for l in lap_records][0]
    total_time = [0 + l['total_time_seconds'] for l in lap_records][0]
    rolling_time = [0 + l['total_rolling_time_seconds'] for l in lap_records][0]
    activity_record = {
        'name': str(starttime),
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
        }
    acts.append(activity_record)
 
  if not acts:
    raise UnknownTCXExpception("No activities found.")

  return acts
