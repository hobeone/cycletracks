import os

from django.test import TestCase
from django.core.urlresolvers import reverse

from google.appengine.ext import db
from google.appengine.api import apiproxy_stub_map
from django.contrib.auth.models import User

from gcycle import models

class GeoPointTestModel(db.Model):
  geo_points = models.GeoPointList()


class TestGeoPointList(TestCase):
  def testProperty(self):
    geo_points = [[2.3, 4.5],[123.123,123.456]]

    g = GeoPointTestModel()
    g.geo_points = geo_points
    key = g.put()
    g = GeoPointTestModel.get(key)
    self.failUnlessEqual(geo_points, g.geo_points)
