from appengine_django import models
from appengine_django import auth
from google.appengine.ext import db

def average(array):
  if len(array) == 0: return 0
  return (sum(array) / len(array))

class User(auth.models.User):
  def activity_count(self):
    query = Activity.all()
    query.ancestor(self)
    return query.count()

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
    query.ancestor(self)
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


class Activity(models.BaseModel):
  user = db.ReferenceProperty(User, required=True)
  name = db.StringProperty(required=True)
  sport = db.StringProperty(required=True)
  total_meters = db.FloatProperty(required=True)
  start_time = db.DateTimeProperty(required=True)
  end_time = db.DateTimeProperty(required=True)
  total_time = db.FloatProperty(required=True)
  rolling_time = db.FloatProperty(required=True)
  average_speed = db.FloatProperty(required=True)
  maximum_speed = db.FloatProperty(required=True)
  average_cadence = db.FloatProperty()
  maximum_cadence = db.FloatProperty()
  average_bpm = db.FloatProperty()
  maximum_bpm = db.FloatProperty()
  total_calories = db.FloatProperty()
  # A geographical point represented by floating-point
  # latitude and longitude coordinates.
  start_point = db.GeoPtProperty()
  end_point = db.GeoPtProperty()
  comment = db.StringProperty()
  public = db.BooleanProperty(default=False)

  def bpm_list(self):
    bpm_list = []
    for l in self.lap_set:
      bpm_list.extend(l.bpms())
    return bpm_list

  def cadence_list(self):
    cadence_list = []
    for l in self.lap_set:
      cadence_list.extend(l.cadences())
    return cadence_list

  def speed_list(self):
    speed_list = []
    for l in self.lap_set:
      speed_list.extend(l.speeds())
    return speed_list

  def altitude_list(self):
    altitude_list = []
    for l in self.lap_set:
      altitude_list.extend(l.altitudes())
    return altitude_list

class Lap(models.BaseModel):
  activity = db.ReferenceProperty(Activity, required=True)
  total_meters = db.FloatProperty(required=True)
  total_time_seconds = db.FloatProperty(required=True)
  total_rolling_time_seconds = db.FloatProperty(required=True)
  average_cadence = db.FloatProperty(required=True)
  maximum_cadence = db.FloatProperty(required=True)
  average_bpm = db.FloatProperty(required=True)
  maximum_bpm = db.FloatProperty(required=True)
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

  def speeds(self):
    return [int(float(b)) for b in self.speed_list.split(',') if b]

  def altitudes(self):
    return [int(float(b)) for b in self.altitude_list.split(',') if b]

  def cadences(self):
    return [int(float(b)) for b in self.cadence_list.split(',') if b]

  def bpms(self):
    return [int(float(b)) for b in self.bpm_list.split(',') if b]
