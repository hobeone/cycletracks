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

class TimeDeltaTooSmall(GPXExpception):
  pass


def parse_segment(segment, tags, starting_dist = 0.0):
  # TODO: error on no time data
  # record time as total delta since start in seconds

  # A segment is a list of location and time points. From the gpx make a list
  # of (lat, lon) tuples, a list of elevation in meters and a list of times in
  # seconds relative to the first time in the segment.
  start_time = None
  time_points = []
  geo_points = []
  altitude_list = []
  cadence_list = []
  bpm_list = []
  for wpt in segment.findall(tags['wpt']):
    geo_points.append([float(wpt.get("lat")),float(wpt.get("lon"))])
    waypoint_time = pytcx.parse_zulu(wpt.findtext(tags['time']))
    if start_time is None:
      start_time = waypoint_time
    time_points.append((waypoint_time - start_time).seconds)
    altitude_list.append(float(wpt.findtext(tags['elevation'])))
    for extensions in wpt.findall(tags['extensions']):
      for tpx in extensions.findall(tags['TrackPointExtension']):
        cad = tpx.findtext(tags['cadence'])
        if cad:
          try:
            if len(cadence_list) == 0 and len(time_points) > 0:
              cadence_list = pytcx.fill_list(cadence_list, 0,
                  len(time_points)-1)
            cadence_list.append(int(cad))
          except ValueError, e:
            raise InvalidGPXFormat("Cadence must be an integer")
        else:
          if cadence_list:
            cadence_list.append(cadence_list[-1])
          else:
            cadence_list.append(0)

        bpm = tpx.findtext(tags['heartrate'])
        if bpm:
          try:
            if len(bpm_list) == 0 and len(time_points) > 0:
              bpm_list = pytcx.fill_list(bpm_list, int(bpm), len(time_points)-1)
            bpm_list.append(int(bpm))
          except ValueError, e:
            raise InvalidGPXFormat("Heartrate must be an integer")
        else:
          # If there are entries in the list, repeat the last valid value until
          # we get some new data.
          if bpm_list:
            bpm_list.append(bpm_list[-1])
          # Otherwise, leave bpm_list empty so that it can be backfilled with
          # the first valid heartrate we get.

  # Only the first element of time_points may be 0. Remove extra points
  # from the start so this is true.
  if time_points[-1] == 0:
    raise TimeDeltaTooSmall('No time change found')
  i = 1
  while time_points[i] == 0:
    i += 1
  if i > 1:
    time_points = time_points[i - 1:]
    geo_points = geo_points[i - 1:]
    altitude_list = altitude_list[i - 1:]
    cadence_list = cadence_list[i - 1:]
    bpm_list = bpm_list[i - 1:]

  # From the location and time points calculate derived measurements.
  distance_list = [starting_dist]
  paused_time = 0
  # Speed from geo_points[i - 1] to geo_points[i], 0 if less than
  # PAUSED_MIN_SPEED and speed_list[i - 1] if speed_list[i] is not defined.
  # speed_list[0] will be fixed later.
  speed_list = [None]
  # Preserve speed between iterations.
  speed = None
  for i in xrange(1, len(geo_points)):
    distance_delta = distance.distance(geo_points[i], geo_points[i - 1]).meters
    time_delta = time_points[i] - time_points[i - 1]
    if time_delta > 0:
      # Some time has passed so calculate a new speed in km/h. If time_delta is
      # 0 the speed from the previous iteration is used again.
      speed = distance_delta / time_delta * 3.6
    if speed < PAUSED_MIN_SPEED:
      paused_time += time_delta
      distance_list.append(distance_list[-1])
      speed_list.append(0)
    else:
      distance_list.append(distance_list[-1] + distance_delta)
      speed_list.append(speed)

  if len(speed_list) < 3:
    # movingAverage3 needs at least 3 points
    raise TrackTooShort('Too few points in lap')
  
  # speed_list[1] is guaranteed to have a float value because time_points
  # starts with [0, a value > 0, ...].
  speed_list[0] = speed_list[1]

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

  rolling_time = total_time - paused_time
  average_speed = (total_meters - starting_dist) / rolling_time * 3.6

  max_cadence = 0
  if cadence_list:
    max_cadence = max(cadence_list)

  max_bpm = 0
  if bpm_list:
    max_bpm = max(bpm_list)

  lap_record = {
    'total_meters' : total_meters - starting_dist,
    'total_time_seconds': total_time,
    'total_rolling_time_seconds' : rolling_time,
    'starttime': start_time,
    'maximum_speed': max(movingAverage3(speed_list)),
    'average_speed': average_speed,
    'average_cadence': int(average(cadence_list)),
    'maximum_cadence': max_cadence,
    'average_bpm': int(average(bpm_list)),
    'maximum_bpm': max_bpm,
    'endtime': start_time + datetime.timedelta(seconds=time_points[-1]),
    'geo_points' : geo_points,
    'speed_list' : array.array('f', speed_list),
    'altitude_list' :array.array('f',  altitude_list),
    'distance_list' : array.array('f', distance_list),
    'cadence_list' : array.array('H', cadence_list),
    'bpm_list' : array.array('H', bpm_list),
    'timepoints' : array.array('i',time_points),
    'total_ascent' : total_ascent,
    'total_descent' : total_descent
    }
  return lap_record

def parse_gpx(filedata, version):
  """Return a dict representing an activity record."""
  et=ET.parse(StringIO.StringIO(filedata))
  mainNS=string.Template("{http://www.topografix.com/GPX/%s}$tag" % version)
  tpxNS=string.Template("{http://www.garmin.com/xmlschemas/TrackPointExtension/v1}$tag")

  tags = {
    'wpt': mainNS.substitute(tag="trkpt"),
    'time': mainNS.substitute(tag="time"),
    'elevation': mainNS.substitute(tag="ele"),
    'segment': mainNS.substitute(tag="trkseg"),
    'extensions': mainNS.substitute(tag="extensions"),
    'TrackPointExtension': tpxNS.substitute(tag="TrackPointExtension"),
    'heartrate': tpxNS.substitute(tag="hr"),
    'cadence': tpxNS.substitute(tag="cad"),
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

  times = [l['total_rolling_time_seconds'] for l in lap_records]
  rolling_time = sum(times)

  if rolling_time < 1:
    raise InvalidGPXFormat(
      "Activity has total rolling time less than 1 second.")

  average_speed = pytcx.average_lap_values('average_speed', lap_records)

  activity_record = {
      'name': '%s' % (lap_records[0]['starttime']),
      'total_meters': total_meters,
      'start_time': lap_records[0]['starttime'],
      'end_time': lap_records[-1]['endtime'],
      'total_time': total_time,
      'rolling_time': rolling_time,
      'average_speed': average_speed,
      'maximum_speed': max([l['maximum_speed'] for l in lap_records]),
      'average_cadence':
        int(pytcx.average_lap_values('average_cadence', lap_records)),
      'maximum_cadence': max([l['maximum_cadence'] for l in lap_records]),
      'average_bpm': int(pytcx.average_lap_values('average_bpm', lap_records)),
      'maximum_bpm': max([l['maximum_bpm'] for l in lap_records]),
      'total_ascent': sum([l['total_ascent'] for l in lap_records]),
      'total_descent': sum([l['total_descent'] for l in lap_records]),
      'laps': lap_records,
      'source_hash': md5.new(filedata).hexdigest(),
      'tcxdata': filedata,
      'parse_errors': parse_errors
  }
  activity_record.update(encoded_activity)

  return activity_record
