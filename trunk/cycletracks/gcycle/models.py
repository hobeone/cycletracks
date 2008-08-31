from appengine_django.models import BaseModel
from appengine_django.auth.models import User
from google.appengine.ext import db
from gcycle.lib import pytcx
from gcycle.lib.average import *
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from gcycle.lib.memoized import *

def new_getprofile(self):
    """
    Returns site-specific profile for this user. Raises
    SiteProfileNotAvailable if this site does not allow profiles.

    When using the App Engine authentication framework, users are created
    automatically.
    """
    from django.contrib.auth.models import SiteProfileNotAvailable
    if not hasattr(self, '_profile_cache'):
      from django.conf import settings
      if not hasattr(settings, "AUTH_PROFILE_MODULE"):
        raise SiteProfileNotAvailable
      try:
        app_label, model_name = settings.AUTH_PROFILE_MODULE.split('.')
        model = models.get_model(app_label, model_name)
        self._profile_cache = model.all().filter("user =", self).get()
        if not self._profile_cache:
          self._profile_cache = model(user = self)
          self._profile_cache.put()
      except (ImportError, ImproperlyConfigured):
        raise SiteProfileNotAvailable
    return self._profile_cache

User.get_profile = new_getprofile


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
        'total_ascent' : 0,
        'total_descent' : 0
        }
    query = Activity.all()
    query.ancestor(self.user)
    for activity in query:
      total_data['total_meters'] += activity.total_meters
      total_data['total_time'] += activity.total_time
      total_data['rolling_time'] += activity.rolling_time
      total_data['total_calories'] += activity.total_calories
      total_data['total_ascent'] += activity.total_ascent
      total_data['total_descent'] += activity.total_descent

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
  # verify rolling time > 0
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
  total_ascent = db.FloatProperty(default=0.0)
  total_descent = db.FloatProperty(default=0.0)

  def safe_delete(self):
    to_del = [self]
    to_del.extend(self.lap_set)
    return db.delete(to_del)

  @property
  def safeuser(self):
    return db.get(self._user)

  @property
  def str_key(self):
    return str(self.key())

  @property
  @memoized
  def bpm_list(self):
    bpm_list = []
    for l in self.lap_set:
      bpm_list.extend(l.bpms)
    return bpm_list

  @property
  @memoized
  def cadence_list(self):
    cadence_list = []
    for l in self.lap_set:
      cadence_list.extend(l.cadences)
    return cadence_list

  @property
  @memoized
  def speed_list(self):
    speed_list = []
    for l in self.lap_set:
      speed_list.extend(l.speeds)
    return speed_list

  @property
  @memoized
  def altitude_list(self):
    altitude_list = []
    for l in self.lap_set:
      altitude_list.extend(l.altitudes)
    return altitude_list

  @property
  @memoized
  def time_list(self):
    time_list = []
    max_time = 0
    for lap in self.lap_set:
      time_list.extend([t + max_time for t in lap.times])
      max_time = time_list[-1]
    return time_list

  @property
  @memoized
  def distance_list(self):
    dl = []
    for d in self.lap_set:
      dl.extend(d.distances)
    return dl

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

  def __add__(self, other):
    if not isinstance(other, self.__class__):
      raise NotImplemented, ('%s only supports addition to %s' %
          (self.__class__, self.__class))
    added = {}
    for p in ['average_bpm', 'average_cadence', 'average_speed']:
      added[p] = self._add_averages(other, p)
    added['start_point'] = other.start_point
    added['end_point'] = other.end_point
    added['mid_point'] = other.start_point

    added['start_time'] = self.start_time
    added['end_time'] = other.end_time
    added['sport'] = self.sport
    added['name'] = self.name
    added['user'] = self.user

    for p in ['maximum_bpm', 'maximum_speed', 'maximum_cadence']:
      added[p] = max([getattr(self,p), getattr(other,p)])

    for p in ['rolling_time', 'total_calories', 'total_meters', 'total_time']:
      added[p] = sum([getattr(self,p), getattr(other,p)])

    return Activity(**added)


  def _add_averages(self,other,prop):
    """Add averages weighted by rolling time"""
    return (getattr(self,prop) * self.rolling_time + getattr(other,prop) * other.rolling_time) / (self.rolling_time + other.rolling_time)



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
  distance_list = db.TextProperty(required=True)
  cadence_list = db.TextProperty(required=True)
  geo_points = db.TextProperty()
  timepoints = db.TextProperty(required=True)
  total_ascent = db.FloatProperty(default=0.0)
  total_descent = db.FloatProperty(default=0.0)

  @property
  @memoized
  def speeds(self):
    return [float(b) for b in self.speed_list.split(',')]

  @property
  @memoized
  def altitudes(self):
    return [float(b) for b in self.altitude_list.split(',')]

  @property
  @memoized
  def cadences(self):
    return [int(b) for b in self.cadence_list.split(',')]

  @property
  @memoized
  def bpms(self):
    return [int(b) for b in self.bpm_list.split(',')]

  @property
  @memoized
  def times(self):
    return [int(b) for b in self.timepoints.split(',')]

  @property
  @memoized
  def points_list(self):
    return self.geo_points.split(':')

  @property
  @memoized
  def distances(self):
    return [float(b) for b in self.distance_list.split(',')]

  @property
  @memoized
  def to_kml(self):
    points = ['%s,%s,0' % (l[1],l[0]) for l in [l.split(',') for l in self.points_list]]
    return ' '.join(points)
