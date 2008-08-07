import xml.etree.cElementTree as ET
import datetime

def average(array):
  if len(array) == 0: return 0
  return (sum(array) / len(array))

main_ns = '{http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2}'
def find_child_tag_data(parent, tag, ns=main_ns, default=0):
  childtag = parent.find('.//%s%s' % (ns,tag))
  if childtag == None:
    return default
  return childtag.text

def find_child_tag_value(parent, tag, ns=main_ns, default=0):
  childtag = parent.find('.//%s%s' % (ns,tag))
  if childtag == None:
    return default
  return childtag[0].text


def parse_to_kml(filedata):
  et=ET.parse(filedata).getroot()
  activities = et.findall('.//%sActivity' % main_ns)
  for activity in activities:
    trackpoints = activity.findall('*//%sTrackpoint' % main_ns)
    for point in trackpoints:
      alt = point.find('%sAltitudeMeters' % main_ns).text
      try:
        lat = point.find('*/%sLatitudeDegrees' % main_ns).text
        lon = point.find('*/%sLongitudeDegrees' % main_ns).text
      except AttributeError:
        continue
      print '%s,%s,%s' % (lon,lat,alt)


def parse_tcx(filedata):
  et=ET.parse(filedata).getroot()
  acts = []
  activities = et.findall('.//%sActivity' % main_ns)
  for activity in activities:
    laps = activity.findall('%sLap' % main_ns)
    lap_records = []
    for lap in laps:
      total_meters = float(find_child_tag_data(lap, 'DistanceMeters'))
      total_time = float(find_child_tag_data(lap, 'TotalTimeSeconds'))
      calories = float(find_child_tag_data(lap, 'Calories'))
      cadence = float(find_child_tag_data(lap, 'Cadence'))
      max_speed = float(find_child_tag_data(lap, 'MaximumSpeed')) * 3.6
      avg_bpm = float(find_child_tag_value(lap, 'AverageHeartRateBpm'))
      max_bpm = float(find_child_tag_value(lap, 'MaximumHeartRateBpm'))
      starttime = lap.get('StartTime')
      starttime = datetime.datetime.strptime(starttime, '%Y-%m-%dT%H:%M:%SZ')
      avg_speed = total_meters / total_time * 3.6 # kph

      trackpoints = lap.findall('*/%sTrackpoint' % main_ns)
      endtime = None
      geo_points = []
      cadence_list = []
      bpm_list = []
      speed_list = []
      altitude_list = []

      prev_time = starttime
      prev_distance = 0
      for point in trackpoints:
        point_time = point.find('%sTime' % main_ns).text
        point_time = datetime.datetime.strptime(point_time,'%Y-%m-%dT%H:%M:%SZ')

        dist = point.find('%sDistanceMeters' % main_ns)
        if dist != None:
          dist = float(dist.text)
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

        cad = point.find('%sCadence' % main_ns)
        if cad != None:
          cadence_list.append(float(cad.text))
        else:
          cadence_list.append(0.0)

        alt = point.find('%sAltitudeMeters' % main_ns)
        if alt != None:
          altitude_list.append(alt.text)

        bpm_list.append(str(find_child_tag_value(point, 'HeartRateBpm')))

        try:
          lat = point.find('*/%sLatitudeDegrees' % main_ns).text
          lon = point.find('*/%sLongitudeDegrees' % main_ns).text
          geo_points.append('%s, %s' % (lat,lon))
        except AttributeError:
          continue



      endtime = prev_time
      max_cadence = 0.0
      if cadence_list:
        max_cadence = max(cadence_list)
      lap_record = {
        'total_meters': total_meters,
        'total_time_seconds': total_time,
        'starttime': starttime,
        'endtime': endtime,
        'average_cadence': cadence,
        'maximum_cadence': max_cadence,
        'average_bpm': avg_bpm,
        'maximum_bpm': max_bpm,
        'calories': calories,
        'maximum_speed': max_speed,
        'average_speed': avg_speed,
        'bpm_list' : ','.join(bpm_list),
        'geo_points' : '\n'.join(geo_points),
        'cadence_list' : ','.join([str(c) for c in cadence_list]),
        'speed_list' : ','.join([str(s) for s in speed_list]),
        'altitude_list' : ','.join(altitude_list),
        }
      lap_records.append(lap_record)

    total_meters = [0 + l['total_meters'] for l in lap_records][0]
    rolling_time = [0 + l['total_time_seconds'] for l in lap_records][0]
    activity_record = {
        'name': activity.findall('%sId' % main_ns)[0].text,
        'sport': activity.get('Sport'),
        'total_meters': total_meters,
        'start_time': lap_records[0]['starttime'],
        'end_time': lap_records[0]['endtime'],
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
    return acts
