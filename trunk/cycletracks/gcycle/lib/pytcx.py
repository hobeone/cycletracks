import xml.etree.cElementTree as ET
import time
import datetime
import StringIO
import md5
import array

from gcycle.lib.average import *
from gcycle.lib import glineenc

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

def fill_list(list, fill_data, amount):
  list.extend(
    [fill_data for i in xrange(0,amount)]
  )
  return list

def average_lap_values(key, laps):
  """Return the time weighted average for the given key over the list of laps.
  Averaged over the rolling time of the lap.

  Args:
  - key: string, name of data to average
  - laps: list of laps

  Returns:
  - average of values, float
  """
  total = 0
  total_time = 0
  average = 0
  for l in laps:
    total += l[key] * l['total_rolling_time_seconds']
    total_time += l['total_rolling_time_seconds']

  if total_time > 0:
    average = total / total_time

  return average

MAIN_NS = "{http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2}%s"
TRACK_EXT_NS = "{http://www.garmin.com/xmlschemas/ActivityExtension/v2}%s"
LAP_EXT_NS = "{http://www.garmin.com/xmlschemas/ActivityLapExtension/v2}%s"

tags = {
  'activity': MAIN_NS % "Activity",
  'lap': MAIN_NS % "Lap",
  'track': MAIN_NS % "Track",
  'time': MAIN_NS % "Time",
  'trackpoint': MAIN_NS % "Trackpoint",
  'altitude': MAIN_NS % "AltitudeMeters",
  'distance': MAIN_NS % "DistanceMeters",
  'cadence': MAIN_NS % "Cadence",
  'lat': MAIN_NS % "LatitudeDegrees",
  'long': MAIN_NS % "LongitudeDegrees",
  'heartrate': MAIN_NS % "HeartRateBpm",
  'value': MAIN_NS % "Value",
  'watts': TRACK_EXT_NS % "Watts",
  'avg_watts': LAP_EXT_NS % "AvgWatts",
  'total_time': MAIN_NS % "TotalTimeSeconds",
  'distance_meters': MAIN_NS % "DistanceMeters",
  'maximum_speed': MAIN_NS % "MaximumSpeed",
  'calories': MAIN_NS % "Calories",
  'avg_heart_rate': MAIN_NS % "AverageHeartRateBpm",
  'max_heart_rate': MAIN_NS % "MaximumHeartRateBpm",
  'start_time': MAIN_NS % "StartTime",
}

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

def parse_lap(lap):
  total_time = int(float(lap.findtext(tags['total_time'])))
  total_meters = float(lap.findtext(tags['distance_meters']))

  if total_meters < MINIMUM_LAP_DISTANCE:
    raise TrackTooShort('Lap is less than %i meters, ignoring' %
        MINIMUM_LAP_DISTANCE)

  if total_time < MINIMUM_LAP_TIME:
    raise TrackTooShort('Lap is less than %i seconds' % MINIMUM_LAP_TIME)

  lap_record = {
    'total_meters': total_meters,
    'total_rolling_time_seconds' : total_time,
    'starttime': parse_zulu(lap.get('StartTime')),
    'average_bpm': int(lap.findtext(tags['avg_heart_rate']+'/'+tags['value'], 0)),
    'maximum_bpm': int(lap.findtext(tags['max_heart_rate']+'/'+tags['value'], 0)),
    'calories': float(lap.findtext(tags['calories'], 0)),
    'maximum_speed': float(lap.findtext(tags['maximum_speed'], 0)) * 3.6,
    'average_speed': total_meters / total_time * 3.6 # kph,
    }

  geo_points = []
  cadence_list = array.array('H')
  bpm_list = array.array('H')
  speed_list = array.array('f')
  altitude_list = array.array('f')
  timepoints = array.array('i')
  distance_list = array.array('f')
  power_list = array.array('H')
  starttime = lap_record['starttime']
  prev_time = lap_record['starttime']
  endtime = starttime
  prev_distance = 0
  total_ascent = 0.0
  total_descent = 0.0

  for track in lap.findall(tags['track']):
    for point in track.findall(tags['trackpoint']):
      point_time = point.findtext(tags['time'])
      if not point_time:
        raise InvalidTCXFormat("Trackpoint has no time attribute.")

      point_time = parse_zulu(point_time)
      endtime = point_time

      dist = point.findtext(tags['distance'])
      timedelta = (point_time - prev_time).seconds

      if dist is None:
        # no distance delta == no speed
        speed_list.append(0)
        distance_list.append(distance_list[-1])
        timepoints.append((point_time - starttime).seconds)
      else:
        dist = float(dist)
        dist_delta = dist - prev_distance
        distance_list.append(dist)
        if dist_delta == 0:
          speed_list.append(0)
          timepoints.append((point_time - starttime).seconds)
        else:
          if timedelta > 0:
            timepoints.append((point_time - starttime).seconds)
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

      cad = point.findtext(tags['cadence'])
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

      bpm = point.findtext(tags['heartrate']+'/'+tags['value'])
      if bpm:
        if len(bpm_list) == 0 and len(timepoints) > 0:
          bpm_list = fill_list(bpm_list, 0, len(timepoints)-1)
        bpm_list.append(int(bpm))
      else:
        if bpm_list:
          bpm_list.append(bpm_list[-1])

      power = point.findtext('.//'+tags['watts'])
      if power:
        if len(power_list) == 0 and len(timepoints) > 0:
          power_list = fill_list(power_list, 0, len(timepoints)-1)
        power_list.append(int(power))
      else:
        if power_list:
          power_list.append(power_list[-1])

      alt = point.findtext(tags['altitude'])
      if alt:
        alt = float(alt)
        if len(altitude_list) == 0:
          prev_altitude = alt
          if len(timepoints) > 0:
            altitude_list = fill_list(altitude_list, alt, len(timepoints)-1)
        altitude_list.append(alt)

        altitude_delta = alt - prev_altitude
        if altitude_delta >= 0:
          total_ascent += altitude_delta
        else:
          total_descent += altitude_delta * -1
        prev_altitude = alt
      else:
        if altitude_list:
          altitude_list.append(altitude_list[-1])

      lat = point.findtext('*/'+tags['lat'])
      long = point.findtext('*/'+tags['long'])
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

    max_power = None
    if power_list:
      max_power = max(power_list)

    lap_record.update({
      'total_time_seconds': timepoints[-1],
      'endtime': endtime,
      'average_cadence': int(average(cadence_list)),
      'maximum_cadence': max_cadence,
      'bpm_list' : bpm_list,
      'power_list': power_list,
      'average_power': int(average(power_list)),
      'maximum_power': max_power,
      'geo_points' : geo_points,
      'cadence_list' : cadence_list,
      'speed_list' : speed_list,
      'altitude_list' : altitude_list,
      'distance_list' : distance_list,
      'timepoints' : timepoints,
      'total_ascent' : total_ascent,
      'total_descent' : total_descent
      })
  return lap_record

def parse_tcx(filedata):
  et=ET.parse(StringIO.StringIO(filedata))
  acts = []

  for activity in et.findall("//"+tags['activity']):
    lap_records = []
    parse_errors = []
    lap_count = 1
    activity_sport = activity.get("Sport")

    for lap in activity.findall(tags['lap']):
      try:
        lap_records.append(parse_lap(lap))
      except TCXExpception, e:
        parse_errors.append("Lap %i couldn't be parsed: %s" % (lap_count, e))

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
        'average_cadence': int(average_lap_values('average_cadence',
          lap_records)),
        'maximum_cadence': max([l['maximum_cadence'] for l in lap_records]),
        'average_bpm': int(average_lap_values('average_bpm', lap_records)),
        'maximum_bpm': max([l['maximum_bpm'] for l in lap_records]),
        'average_power': int(average_lap_values('average_power', lap_records)),
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
