import os

from django.test import TestCase
from django.core.urlresolvers import reverse

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

class TestActivityModel(TestCase):
  def setUp(self):
    self.data = datafixture.data(UserData, ActivityData, LapData,
        SourceDataFileData)
    self.data.setup()

  def tearDown(self):
      self.data.teardown()

  def testPermalink(self):
    a = models.Activity.all().get()
    url = reverse('activity_show', args=[a.key().id()])
    self.failUnlessEqual(url, a.get_absolute_url())

  def testCreateFromTcx(self):
    testfile = open('gcycle/test/valid_multi_lap.tcx').read()
    a = models.Activity.create_from_tcx(testfile, models.User.all().get())
    assert(a.lap_set.count() == 2)

  def test_safe_user(self):
    a = models.Activity.all().get()
    db.delete(a.user)
    a = models.Activity.get(a.key())
    self.assert_(a)
    self.assertRaises(db.Error, getattr, a, 'user')
    self.assertEqual(None, a.safeuser)

  def testActivityTags(self):
    query = db.GqlQuery("SELECT * from Activity WHERE tags = 'foo'")
    self.failUnlessEqual(query.count(), 0)
    a = models.Activity.all().get()
    a.tags = "foo, bar"
    a.put()
    act = query.get()
    self.failUnlessEqual(a.key(), act.key())
