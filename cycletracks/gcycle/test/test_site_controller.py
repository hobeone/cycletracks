import os

from django.test import TestCase
from django.test.client import Client
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

class TestSiteController(TestCase):
  def setUp(self):
    self.data = datafixture.data(UserData, ActivityData, LapData,
        SourceDataFileData)
    self.data.setup()
    os.environ['USER_EMAIL'] = UserData.admin_user.user.email()

    host = 'django.testserver'
    self.client = Client(HTTP_HOST=host)

  def tearDown(self):
      self.data.teardown()

  def test_upload_renders_on_get(self):
    url = reverse('upload')
    response = self.client.get(url)
    self.assertContains(response, 'Upload', status_code=200)

  def test_upload_with_valid_upload_tcx(self):
    url = reverse('upload')
    tcx_file = open('gcycle/test/valid_multi_lap.tcx')
    response = self.client.post(url, {'tags' : 'test', 'file': tcx_file})
    self.failUnlessEqual(response.status_code, 302)

  def test_upload_with_valid_upload_gpx10(self):
    url = reverse('upload')
    gpx_file = open('gcycle/test/valid_single_segment_10.gpx')
    response = self.client.post(url, {'tags' : 'test', 'file': gpx_file})
    self.failUnlessEqual(response.status_code, 302)

  def test_upload_with_valid_upload_gpx11(self):
    url = reverse('upload')
    gpx_file = open('gcycle/test/valid_single_segment_11.gpx')
    response = self.client.post(url, {'tags' : 'test', 'file': gpx_file})
    self.failUnlessEqual(response.status_code, 302)

  def test_upload_with_valid_upload_gpx11_tpx(self):
    url = reverse('upload')
    gpx_file = open('gcycle/test/valid_single_segment_11_tpx.gpx')
    response = self.client.post(url, {'tags' : 'test', 'file': gpx_file})
    self.failUnlessEqual(response.status_code, 302)

  def test_upload_with_valid_upload_gpx_garmin_colorado(self):
    url = reverse('upload')
    gpx_file = open('gcycle/test/valid_single_segment_garmin_colorado.gpx')
    response = self.client.post(url, {'tags' : 'test', 'file': gpx_file})
    self.failUnlessEqual(response.status_code, 302)

  def test_upload_with_invalid_post(self):
    url = reverse('upload')
    response = self.client.post(url, {'tags' : 'test'})
    self.failUnlessEqual(response.status_code, 501)

  def test_upload_with_invalid_data(self):
    url = reverse('upload')
    tcx_file = open('gcycle/test/invalid_tcx.tcx')
    response = self.client.post(url, {'tags' : 'test', 'file': tcx_file})
    self.failUnlessEqual(response.status_code, 501)

  def test_upload_with_activity_limit(self):
    u = User.all().filter('username = ', UserData.admin_user.username).get()
    p = u.get_profile()
    p.total_allowed_activities = 0
    p.put()
    url = reverse('upload')
    tcx_file = open('gcycle/test/valid_multi_lap.tcx')
    response = self.client.post(url, {'file': tcx_file})
    self.failUnlessEqual(response.status_code, 501)
