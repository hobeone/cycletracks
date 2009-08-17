import os

from django.test import TestCase
from django.core.urlresolvers import reverse

from google.appengine.ext import db
from google.appengine.api import apiproxy_stub_map
from django.contrib.auth.models import User

from gcycle import models
from gcycle.test.user_fixtures import UserData
from gcycle.test.activity_fixtures import ActivityData
from gcycle.test.lap_fixtures import LapData
from gcycle.test.sourcedatafile_fixtures import SourceDataFileData

from fixture import GoogleDatastoreFixture, DataSet
from fixture.style import NamedDataStyle

datafixture = GoogleDatastoreFixture(env=models, style=NamedDataStyle())

class TestLapModel(TestCase):
  def setUp(self):
    self.data = datafixture.data(UserData, ActivityData, LapData,
        SourceDataFileData)
    self.data.setup()

  def tearDown(self):
      self.data.teardown()

  def testGeoPointPropery(self):
    geo_points = [[2.3, 4.5],[123.123,123.456], [4,5]]

    l = models.Lap.all().get()
    l.geo_points = geo_points
    key = l.put()

    l = models.Lap.get(key)
    self.failUnlessEqual(geo_points, l.geo_points)

