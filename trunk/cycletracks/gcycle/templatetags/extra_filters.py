import datetime
from django import template
register = template.Library()

def meters_to_miles(value):
  return km_to_miles(value / 1000)
register.filter('meters_to_miles', meters_to_miles)

def km_to_miles(value):
  return value * 0.621371192
register.filter('km_to_miles', km_to_miles)

def seconds_to_human_readable(seconds):
  return str(datetime.timedelta(0, seconds))
register.filter('seconds_to_human_readable', seconds_to_human_readable)


def seconds_to_hours(seconds):
  return seconds / 60 / 60
register.filter('seconds_to_hours', seconds_to_hours)
