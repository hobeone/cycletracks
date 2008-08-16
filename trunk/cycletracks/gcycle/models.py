from appengine_django.models import BaseModel
from appengine_django.auth.models import User
from google.appengine.ext import db
from gcycle.lib import pytcx
from gcycle.lib.average import *

class UserProfile(BaseModel):
  user = db.ReferenceProperty(User, required=True)
  use_imperial = db.BooleanProperty(default=False)
  tzoffset = db.IntegerProperty(default=0)

  @property
  def activity_count(self):
    query = Activity.all()
    query.ancestor(self)
    return query.count()

  @property
  def totals(self):
    total_data = {
        'total_meters' : 0,
        'total_time' : 0,
        'rolling_time' : 0,
        'total_calories' : 0,
        'average_speed' : [],
        'maximum_speed' : 0,
        'average_cadence' : [],
        'maximum_cadence' : 0,
        'average_bpm' : [],
        'maximum_bpm' : 0,
        }
    query = Activity.all()
    query.ancestor(self.user)
    for activity in query:
      total_data['total_meters'] += activity.total_meters
      total_data['total_time'] += activity.total_time
      total_data['rolling_time'] += activity.rolling_time
      total_data['total_calories'] += activity.total_calories

      total_data['average_speed'].append(activity.average_speed)
      if activity.maximum_speed > total_data['maximum_speed']:
        total_data['maximum_speed'] = activity.maximum_speed

      total_data['average_cadence'].append(activity.average_cadence)
      if activity.maximum_cadence > total_data['maximum_cadence']:
        total_data['maximum_cadence'] = activity.maximum_cadence

      total_data['average_bpm'].append(activity.average_bpm)
      if activity.maximum_bpm > total_data['maximum_bpm']:
        total_data['maximum_bpm'] = activity.maximum_bpm


    total_data['average_speed'] = average(total_data['average_speed'])
    total_data['average_cadence'] = average(total_data['average_cadence'])
    total_data['average_bpm'] = average(total_data['average_bpm'])
    return total_data


class Activity(BaseModel):
  user = db.ReferenceProperty(User, required=True)
  name = db.StringProperty(required=True)
  sport = db.StringProperty(required=True)
  total_meters = db.FloatProperty(required=True)
  start_time = db.DateTimeProperty(required=True)
  end_time = db.DateTimeProperty(required=True)
  total_time = db.IntegerProperty(required=True)
  rolling_time = db.IntegerProperty(required=True)
  average_speed = db.FloatProperty(required=True)
  maximum_speed = db.FloatProperty(required=True)
  average_cadence = db.IntegerProperty(default=0)
  maximum_cadence = db.IntegerProperty(default=0)
  average_bpm = db.IntegerProperty(default=0)
  maximum_bpm = db.IntegerProperty(default=0)
  total_calories = db.FloatProperty(default=0.0)
  comment = db.StringProperty()
  public = db.BooleanProperty(default=False)
  encoded_points = db.TextProperty()
  encoded_levels = db.TextProperty()
  ne_point = db.GeoPtProperty()
  sw_point = db.GeoPtProperty()
  start_point = db.GeoPtProperty()
  mid_point = db.GeoPtProperty()
  end_point = db.GeoPtProperty()

  @property
  def safeuser(self):
    return db.get(self._user)

  @property
  def has_encoded_points(self):
    return (self.encoded_points and self.encoded_levels and
            self.ne_point and self.sw_point)

  @property
  def str_key(self):
    return str(self.key())

  @property
  def bpm_list(self):
    bpm_list = []
    for l in self.lap_set:
      bpm_list.extend(l.bpms)
    return bpm_list

  @property
  def cadence_list(self):
    cadence_list = []
    for l in self.lap_set:
      cadence_list.extend(l.cadences)
    return cadence_list

  @property
  def speed_list(self):
    speed_list = []
    for l in self.lap_set:
      speed_list.extend(l.speeds)
    return speed_list

  @property
  def altitude_list(self):
    altitude_list = []
    for l in self.lap_set:
      altitude_list.extend(l.altitudes)
    return altitude_list

  @property
  def time_list(self):
    time_list = []
    for t in self.lap_set:
      time_list.extend(t.times)
    return time_list

  def encode_activity_points(self):
    pts, levs, ne, sw, start_point, mid_point, end_point = \
        pytcx.encode_activity_points([l.geo_points for l in self.lap_set()])
    self.encoded_points = pts
    self.encoded_levels = levs
    self.start_point = start_point
    self.mid_point = mid_point
    self.end_point = end_point
    self.ne_point = ne
    self.sw_point = sw
    self.put()

  @property
  def to_kml(self):
    points = []
    for l in self.lap_set:
      points.extend(l.points_list)

    points =  ['%s,%s,0' % (l[1],l[0]) for l in [l.split(',') for l in points]]
    return ' '.join(points)




class Lap(BaseModel):
  activity = db.ReferenceProperty(Activity, required=True)
  total_meters = db.FloatProperty(required=True)
  total_time_seconds = db.IntegerProperty(required=True)
  total_rolling_time_seconds = db.IntegerProperty(required=True)
  average_cadence = db.IntegerProperty(required=True)
  maximum_cadence = db.IntegerProperty(required=True)
  average_bpm = db.IntegerProperty(required=True)
  maximum_bpm = db.IntegerProperty(required=True)
  average_speed = db.FloatProperty(required=True)
  maximum_speed = db.FloatProperty(required=True)
  calories = db.FloatProperty(required=True)
  starttime = db.DateTimeProperty(required=True)
  endtime = db.DateTimeProperty(required=True)
  bpm_list = db.TextProperty(required=True)
  altitude_list = db.TextProperty(required=True)
  speed_list = db.TextProperty(required=True)
  cadence_list = db.TextProperty(required=True)
  geo_points = db.TextProperty()
  timepoints = db.TextProperty(required=True)

  @property
  def speeds(self):
    return [float(b) for b in self.speed_list.split(',')]

  @property
  def altitudes(self):
    return [float(b) for b in self.altitude_list.split(',')]

  @property
  def cadences(self):
    return [int(b) for b in self.cadence_list.split(',')]

  @property
  def bpms(self):
    return [int(b) for b in self.bpm_list.split(',')]

  @property
  def times(self):
    return [int(b) for b in self.timepoints.split(',')]

  @property
  def points_list(self):
    return self.geo_points.split(':')
