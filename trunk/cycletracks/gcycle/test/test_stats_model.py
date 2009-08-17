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
from gcycle.test.monthly_user_stats_fixtures import MonthlyUserStatsData

from fixture import GoogleDatastoreFixture, DataSet
from fixture.style import NamedDataStyle

datafixture = GoogleDatastoreFixture(env=models, style=NamedDataStyle())

class TestStatsModel(TestCase):
  def setUp(self):
    apiproxy_stub_map.apiproxy.GetStub('datastore_v3').Clear()
    self.data = datafixture.data(UserData, ActivityData, LapData,
        SourceDataFileData, MonthlyUserStatsData)
    self.data.setup()

  def tearDown(self):
    self.data.teardown()

  def testFindByUserAndMonthReturnsNoneOnNoStats(self):
    u = User.all().filter('username =', 'joe').get()
    assert(u)
    s = models.MonthlyUserStats.find_by_user_and_month_offset(u, 0)
    self.assertEqual(s, None)

  def testFindByUserAndMonthReturnsRightMonthsStats(self):
    u = User.all().filter('username =', 'admin').get()
    assert(u)
    s = models.MonthlyUserStats.find_by_user_and_month_offset(u, 0)
    self.failIf(s is None)


  def testStatCalculation(self):
    a = models.Activity.all().get()
    u = a.user
    s = models.MonthlyUserStats.find_by_user_and_activity(u, a)
    self.assertEqual(s.is_saved(), False)
    s.update_from_activity(a)
    self.assertEqual(s.total_meters, a.total_meters)
    self.assertEqual(s.total_time, a.total_time)
