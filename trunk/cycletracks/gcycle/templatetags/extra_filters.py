import datetime
from django import template
register = template.Library()

@register.filter
def meters_to_miles(value):
  return km_to_miles(value / 1000)

@register.filter
def meters_to_feet(meters):
  return meters * 3.2808399

@register.filter
def km_to_miles(value):
  return value * 0.621371192

@register.filter
def seconds_to_human_readable(seconds):
  return str(datetime.timedelta(0, seconds))

@register.filter
def seconds_to_hours(seconds):
  return seconds / 60 / 60

@register.filter
def meters_to_prefered_distance(meters, use_imperial):
  dist = meters / 1000
  if use_imperial:
    dist = km_to_miles(dist)
  dist = '%.2f' % (dist)
  return dist

def meters_or_feet(meters, use_imperial):
  dist = meters
  if use_imperial:
    dist = meters_to_feet(dist)
  return dist

@register.filter
def meters_or_feet_units(use_imperial):
  if use_imperial:
    return 'ft'
  return 'm'

@register.filter
def miles_or_km_units(use_imperial):
  if use_imperial:
    return 'mi'
  return 'km'

@register.filter
def mph_or_kph_units(use_imperial):
  if use_imperial:
    return 'mph'
  return 'kph'

@register.filter
def format_meters(meters, use_imperial):
  dist = meters
  if use_imperial:
    dist = meters_to_feet(dist)
  dist = '%.2f' % (dist)
  return dist


@register.filter
def kph_to_prefered_speed(kph, use_imperial):
  speed = kph
  if use_imperial:
    speed = km_to_miles(speed)
  speed = '%.2f' % (speed)
  return speed

@register.filter
def time_to_offset(time, offset):
  timedelta = datetime.timedelta(hours=offset)
  return time + timedelta

@register.filter
def minlist(list):
  return min(list)

@register.filter
def maxlist(list):
  return max(list)

@register.filter
def ziplist(l, otherlist):
  return map(list,zip(l,otherlist))

@register.filter
def format_date(date, formatstring):
  return date.strftime(formatstring)

@register.filter
def value_or_zero(value):
  if not value:
    value = 'null'
  return value
