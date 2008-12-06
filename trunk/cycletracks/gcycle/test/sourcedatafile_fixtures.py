from fixture import DataSet
import datetime

from gcycle.test.activity_fixtures import ActivityData

class SourceDataFileData(DataSet):
  class activity_one_sourcedatafile:
    activity = ActivityData.activity_one
    data = 'foobar'
