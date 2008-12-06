import os
import pprint
pp = pprint.PrettyPrinter(indent=2)

from django.test import TestCase
from django.test.client import Client

from google.appengine.ext import db
from google.appengine.api import apiproxy_stub_map
from appengine_django.auth.models import User

from gcycle import models
from gcycle.test.user_fixtures import UserData
from gcycle.test.activity_fixtures import ActivityData
from gcycle.test.lap_fixtures import LapData
from gcycle.test.sourcedatafile_fixtures import SourceDataFileData

from fixture import GoogleDatastoreFixture, DataSet
from fixture.style import NamedDataStyle

datafixture = GoogleDatastoreFixture(env=models, style=NamedDataStyle())

class TestActivityController(TestCase):
  def setUp(self):
    self.data = datafixture.data(UserData, ActivityData, LapData,
        SourceDataFileData)
    self.data.setup()
    os.environ['USER_EMAIL'] = UserData.admin_user.user.email()

    host = 'django.testserver'
    self.client = Client(HTTP_HOST=host)

  def tearDown(self):
      self.data.teardown()

  def test_index_shows_activity_if_exists(self):
    response = self.client.get("/mytracks/")
    self.assertContains(response, 'ActivityOne', status_code=200)
    self.assertTemplateUsed(response, 'dashboard.html')


  def test_shows_activity_on_valid_id(self):
    activity = models.Activity.all().get()
    response = self.client.get("/activity/show/%i" % activity.key().id())
    self.assertContains(response, 'ActivityOne', status_code=200)


  def test_activity_kml_on_valid_id(self):
    # TODO: validate kml
    activity = models.Activity.all().get()
    response = self.client.get("/activity/kml/%i" % activity.key().id())
    self.assertContains(response,
        '<name>CycleTrack Lap 1</name>', status_code=200)


  def test_activity_data_on_valid_id(self):
    activity = models.Activity.all().get()
    response = self.client.get("/activity/data/%i" % activity.key().id())
    self.assertContains(response, '2008-11-01T15:44:21', status_code=200)


  def test_show_public_activity_with_no_user(self):
    os.environ['USER_EMAIL'] = ''
    activity = models.Activity.all().get()

    assert(activity.public == False)
    response = self.client.get("/activity/public/%i" % activity.key().id())
    self.failUnlessEqual(response.status_code, 403)

    activity.public = True
    activity.put()
    response = self.client.get("/activity/public/%i" % activity.key().id())
    self.assertContains(response, 'ActivityOne', status_code=200)


  def test_show_source_activity_with_valid_id(self):
    activity = models.Activity.all().get()
    activity.public = True
    activity.put()
    expected_content = SourceDataFileData.activity_one_sourcedatafile.data
    response = self.client.get("/activity/source/%i" % activity.key().id())
    self.assertContains(response, expected_content, status_code=200)


  def test_show_source_gives_404_when_no_source_exists(self):
    activity = models.Activity.all().get()
    activity.public = True
    db.delete(activity.sourcedatafile_set.get())
    activity.put()

    response = self.client.get("/activity/source/%i" % activity.key().id())
    self.failUnlessEqual(response.status_code, 404)



  def test_shows_errror_on_invalid_id(self):
    for action in ['show', 'kml', 'data', 'public', 'source']:
      response = self.client.get("/activity/%s/-1" % action)
      self.failUnlessEqual(response.status_code, 404)


