from appengine_django.models import BaseModel
from appengine_django.auth.models import User

from google.appengine.ext import db
from google.appengine.api import datastore_types

from gcycle.lib import pytcx
from gcycle.lib import pygpx
from gcycle.lib.memoized import *
from gcycle.lib.average import *

from django.core.exceptions import ImproperlyConfigured
from django.db import models

import md5
import bz2
import datetime

# Monkey patch appengine supplied User model.
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


class BzipBlobProperty(db.BlobProperty):
  data_type = db.Blob
  def get_value_for_datastore(self, model_instance):
    value = super(BzipBlobProperty, self).get_value_for_datastore(
        model_instance)
    return db.Blob(bz2.compress(value))

  def make_value_from_datastore(self, value):
    return bz2.decompress(value)


class CsvListProperty(db.Property):
  data_type = datastore_types.Text

  def __init__(self, verbose_name=None, name=None, default=None,
               required=False, validator=None, choices=None, split_on=',',
               cast_type=str):
    super(CsvListProperty, self).__init__(verbose_name=None, name=None,
        default=None, required=False, validator=None, choices=None)
    self.cast_type = cast_type
    self.split_on = split_on

  def validate(self, value):
    if value is not None and not isinstance(value, list):
      try:
        if isinstance(value, str):
          value = self.make_value_from_datastore(value)
        else:
          value = list(value)
      except TypeError, err:
        raise BadValueError('Property %s must be convertible '
                            'to a list instance (%s)' % (self.name, err))

    if value is not None:
      value = map(self.cast_type,value)
    value = super(CsvListProperty, self).validate(value)
    if value is not None and not isinstance(value, list):
      raise BadValueError('Property %s must be a Text instance' % self.name)
    return value

  def get_value_for_datastore(self, model_instance):
    value = super(CsvListProperty, self).get_value_for_datastore(
        model_instance)
    if value is None or len(value) == 0:
      return None
    return datastore_types.Text(self.split_on.join(map(str,value)))

  def make_value_from_datastore(self, value):
    if value is None:
      return []
    return map(self.cast_type,value.split(self.split_on))


class AutoStringListProperty(db.StringListProperty):
  """Auto converts a csv value to a list before saving"""
  def validate(self, value):
    if value is not None and not isinstance(value, list):
      if isinstance(value, str) or isinstance(value, unicode):
        value = value.split(',')
        value = map(unicode, value)
        value = map(unicode.strip, value)
    value = super(AutoStringListProperty, self).validate(value)
    return value


class UserProfile(BaseModel):
  user = db.ReferenceProperty(User, required=True)
  use_imperial = db.BooleanProperty(default=False)
  tzoffset = db.IntegerProperty(default=0)
  total_meters = db.FloatProperty(default=0.0)
  total_time = db.IntegerProperty(default=0)
  rolling_time = db.IntegerProperty(default=0)
  average_speed = db.FloatProperty(default=0.0)
  maximum_speed = db.FloatProperty(default=0.0)
  average_cadence = db.IntegerProperty(default=0)
  maximum_cadence = db.IntegerProperty(default=0)
  average_bpm = db.IntegerProperty(default=0)
  maximum_bpm = db.IntegerProperty(default=0)
  total_ascent = db.FloatProperty(default=0.0)
  total_descent = db.FloatProperty(default=0.0)
  total_calories = db.FloatProperty(default=0.0)
  totals_updated_at = db.DateTimeProperty()

  @property
  def activity_count(self):
    query = Activity.all()
    query.filter('user = ', self)
    return query.count()

  def reset_totals(self):
    self.total_meters = 0.0
    self.total_time = 0
    self.rolling_time = 0
    self.average_speed = 0.0
    self.maximum_speed = 0.0
    self.average_cadence = 0
    self.maximum_cadence = 0
    self.average_bpm = 0
    self.maximum_bpm = 0
    self.total_ascent = 0.0
    self.total_descent = 0.0
    self.total_calories = 0.0

  def update_totals(self):
    query = Activity.all()
    query.filter('user = ', self.user)
    self.reset_totals()
    speeds = []
    cadences = []
    bpms = []
    self.totals_updated_at = datetime.datetime.utcnow()
    for activity in query:
      self.total_meters += activity.total_meters
      self.total_time += activity.total_time
      self.rolling_time += activity.rolling_time
      self.total_calories += activity.total_calories
      self.total_ascent += activity.total_ascent
      self.total_descent += activity.total_descent

      speeds.append(activity.average_speed)
      if activity.maximum_speed > self.maximum_speed:
        self.maximum_speed = activity.maximum_speed

      cadences.append(activity.average_cadence)
      if activity.maximum_cadence > self.maximum_cadence:
        self.maximum_cadence = activity.maximum_cadence

      bpms.append(activity.average_bpm)
      if activity.maximum_bpm > self.maximum_bpm:
        self.maximum_bpm = activity.maximum_bpm

    self.average_speed = average(speeds, 0.0)
    self.average_cadence = int(average(cadences))
    self.average_bpm = int(average(bpms))
    return self.put()


class Activity(BaseModel):
  user = db.ReferenceProperty(User, required=True)
  name = db.StringProperty(required=True)
  sport = db.StringProperty()
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
  total_ascent = db.FloatProperty(default=0.0)
  total_descent = db.FloatProperty(default=0.0)
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

  source_type = db.StringProperty(default='tcx')
  source_hash = db.StringProperty(required=True)
  tags = AutoStringListProperty()

  created_at = db.DateTimeProperty(auto_now_add=True)
  updated_at = db.DateTimeProperty(auto_now=True)
  parsed_at = db.DateTimeProperty(auto_now_add=True)

  @classmethod
  def hash_exists(cls, source_hash, user):
    q = Activity.all()
    q.filter('source_hash =', source_hash)
    q.filter('user =', user)
    activity_count = q.count(1)
    return activity_count > 0

  def is_valid(self):
    # TODO: when app engine bigtable libs pull their heads out, add real
    # validation
    if not self.is_saved():
      if Activity.hash_exists(self.source_hash, self.user):
        raise db.NotSavedError(
          "An activity with the same source hash already exists")
    if self.rolling_time > self.total_time:
      raise db.NotSavedError("rolling time > total_time(%i != %i)" %
        (self.rolling_time, self.total_time)
      )

  def put(self):
    self.is_valid()
    return_status = super(Activity, self).put()
    return return_status


  def delete(self):
    to_del = [self]
    to_del.extend(self.lap_set)
    to_del.extend(self.sourcedatafile_set)
    return db.delete(to_del)


  def reparse(self):
    source = self.sourcedatafile_set.get()
    if source is None:
      raise db.NotSavedError('no source file to reparse')

    laps = self.lap_set.fetch(self.lap_set.count())
    return db.run_in_transaction(self._reparse, source, laps)

  def _reparse(self, source, laps):
    activity_dict = pytcx.parse_tcx(source.data)[0]
    for k,v in activity_dict.iteritems():
      if k in self.fields():
        setattr(self,k,v)
    self.parsed_at = datetime.datetime.utcnow()
    self.put()

    db.delete(laps)
    for lap_dict in activity_dict['laps']:
      lap = Lap(activity = self, **lap_dict)
      lap.put()


  @classmethod
  def create_from_tcx(self, tcx_data, user, tags = []):
    return db.run_in_transaction(
        self._create_from_tcx, tcx_data, user, tags
    )

  @classmethod
  def _create_from_tcx(self, tcx_data, user, tags = []):
    act_dict = pytcx.parse_tcx(tcx_data)[0]
    activity = Activity(user = user, **act_dict)
    activity.source_type = 'tcx'
    activity.put()
    d = SourceDataFile(
        parent = activity,
        data = tcx_data,
        activity = activity
    )
    d.put()
    for lap_dict in act_dict['laps']:
      lap = Lap(
        parent = activity,
        activity = activity,
        **lap_dict
      )
      lap.put()
    return activity

  @classmethod
  def create_from_gpx(self, gpx_data, user, tags = []):
    return db.run_in_transaction(self._create_from_gpx, gpx_data, user, tags)

  @classmethod
  def _create_from_gpx(self, gpx_data, user, tags = []):
    act_dict = pygpx.parse_gpx(gpx_data)
    activity = Activity(user = user, **act_dict)
    activity.source_type = 'gpx'
    activity.put()
    d = SourceDataFile(
        parent = activity,
        data = gpx_data,
        activity = activity
    )
    d.put()
    for lap_dict in act_dict['laps']:
      lap_dict['geo_points'] = (
          ['%f,%f' % tuple(i) for i in lap_dict['geo_points']])
      lap = Lap(
        parent = activity,
        activity = activity,
        **lap_dict
      )
      lap.put()
    return activity


  @models.permalink
  def get_absolute_url(self):
    return ("activity_show", [self.key().id()])

  @property
  def safeuser(self):
    return db.get(self._user)

  @property
  @memoized
  def bpm_list(self):
    bpm_list = []
    for l in self.lap_set:
      bpm_list.extend(l.bpm_list)
    return bpm_list

  @property
  @memoized
  def cadence_list(self):
    cadence_list = []
    for l in self.lap_set:
      cadence_list.extend(l.cadence_list)
    return cadence_list

  @property
  @memoized
  def speed_list(self):
    speed_list = []
    for l in self.lap_set:
      speed_list.extend(l.speed_list)
    return speed_list

  @property
  @memoized
  def altitude_list(self):
    altitude_list = []
    for l in self.lap_set:
      altitude_list.extend(l.altitude_list)
    return altitude_list

  @property
  @memoized
  def time_list(self):
    time_list = []
    max_time = 0
    for lap in self.lap_set:
      time_list.extend([t + max_time for t in lap.timepoints])
      max_time = time_list[-1]
    return time_list

  @property
  @memoized
  def distance_list(self):
    dl = []
    for d in self.lap_set:
      dl.extend(d.distance_list)
    return dl

  @property
  def to_kml(self):
    points = []
    for l in self.lap_set:
      points.extend(l.geo_points)

    points =  ['%s,%s,0' % (l[1],l[0]) for l in [l.split(',') for l in points]]
    return ' '.join(points)



class SourceDataFile(BaseModel):
  activity = db.ReferenceProperty(Activity, required=True)
  data = BzipBlobProperty(required=True)


class Lap(BaseModel):
  activity = db.ReferenceProperty(Activity, required=True)
  total_meters = db.FloatProperty(required=True)
  total_time_seconds = db.IntegerProperty(required=True)
  total_rolling_time_seconds = db.IntegerProperty(required=True)
  average_cadence = db.IntegerProperty()
  maximum_cadence = db.IntegerProperty()
  average_bpm = db.IntegerProperty()
  maximum_bpm = db.IntegerProperty()
  average_speed = db.FloatProperty(required=True)
  maximum_speed = db.FloatProperty(required=True)
  calories = db.FloatProperty()
  starttime = db.DateTimeProperty(required=True)
  endtime = db.DateTimeProperty(required=True)
  bpm_list = CsvListProperty(cast_type=int)
  altitude_list = CsvListProperty(required=True, cast_type=float)
  speed_list = CsvListProperty(required=True, cast_type=float)
  distance_list = CsvListProperty(required=True, cast_type=float)
  cadence_list = CsvListProperty(cast_type=int)
  geo_points = CsvListProperty(split_on=':')
  timepoints = CsvListProperty(required=True, cast_type=int)
  total_ascent = db.FloatProperty(default=0.0)
  total_descent = db.FloatProperty(default=0.0)

  # God, Django sucks monkey nuts:
  def is_valid(self):
    data_len = len(self.timepoints)
    if self.bpm_list and len(self.bpm_list) != 0 and len(self.bpm_list) != data_len:
      raise db.NotSavedError(
          "bpm_list has the wrong number of entries (%i != %i)" %
          (len(self.bpm_list), data_len)
       )

    if self.altitude_list and len(self.altitude_list) != data_len:
      raise db.NotSavedError(
          "altitude_list has the wrong number of entries (%i != %i)" %
          (len(self.altitude_list), data_len)
      )

    if self.speed_list and len(self.speed_list) != data_len:
      raise db.NotSavedError(
          "speed_list has the wrong number of entries (%s != %s)" % (
            len(self.speed_list), data_len))

    if self.distance_list and len(self.distance_list) != data_len:
      raise db.NotSavedError(
          "distance_list has the wrong number of entries (%i != %i)" %
          (len(self.distance_list), data_len)
      )

    if self.cadence_list and len(self.cadence_list) != data_len:
      raise db.NotSavedError(
          "cadence_list has the wrong number of entries (%i != %i)" %
          (len(self.cadence_list), data_len)
      )

    if self.geo_points and len(self.geo_points) != data_len:
      raise db.NotSavedError(
          "geo_points has the wrong number of entries (%i != %i)" %
          (len(self.geo_points), data_len)
      )

    return self

  def put(self):
    self.is_valid()
    return super(Lap, self).put()

  @property
  @memoized
  def to_kml(self):
    pts = (l.split(',') for l in self.geo_points)
    points = ['%s,%s,0' % (l[1],l[0]) for l in pts]
    return ' '.join(points)


