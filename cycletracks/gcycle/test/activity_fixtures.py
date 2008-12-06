from fixture import DataSet
import datetime

from gcycle.test.user_fixtures import UserData

class ActivityData(DataSet):
  class activity_one:
    user = UserData.admin_user
    name = 'ActivityOne'
    sport = 'biking'
    total_meters = 9.99
    start_time = datetime.datetime(2008,11,1,15,44,21)
    end_time = datetime.datetime(2008,11,1,17,44,21)
    total_time = 7200
    rolling_time = 7000
    average_speed = 9.99
    maximum_speed = 10.0
    average_cadence = 80
    maximum_cadence = 100
    average_bpm = 150
    maximum_bpm = 185
    total_calories = 2000.0
    comment = 'MyString'
    public = False
    encoded_points = 'MyText'
    encoded_levels = 'MyText'
    total_ascent = 9.99
    total_descent = 9.99
    source_hash = 'MyString'
