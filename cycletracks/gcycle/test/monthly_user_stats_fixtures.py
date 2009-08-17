from fixture import DataSet
import datetime

from gcycle.test.user_fixtures import UserData

class MonthlyUserStatsData(DataSet):
  class stats_one:
    user = UserData.admin_user
    number_of_activities = 0
    start_date = datetime.date(year=datetime.datetime.now().year,
        month=datetime.datetime.now().month,
        day=1)
