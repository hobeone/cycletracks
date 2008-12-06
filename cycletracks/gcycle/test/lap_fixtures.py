from fixture import DataSet
import datetime

from gcycle.test.activity_fixtures import ActivityData

class LapData(DataSet):
  class activity_one_lap_one:
    activity = ActivityData.activity_one
    total_meters = 9.99
    total_time_seconds = 7200
    total_rolling_time_seconds = 7000
    average_speed = 9.99
    maximum_speed = 10.0
    average_cadence = 80
    maximum_cadence = 100
    average_bpm = 150
    maximum_bpm = 185
    calories = 2000.0
    starttime = datetime.datetime(2008,11,1,15,44,21)
    endtime = datetime.datetime(2008,11,1,17,44,21)
    bpm_list = '1,2,3'
    altitude_list = '0,10,20'
    speed_list = '1, 10, 10'
    distance_list = '0, 10, 20'
    cadence_list = '60, 80, 80'
    timepoints = '0, 1, 2'
