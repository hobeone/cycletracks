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
  units = 'km'
  if use_imperial:
    dist = km_to_miles(dist)
    units = 'mi'
  dist = '%.2f %s' % (dist, units)
  return dist

@register.filter
def format_meters(meters, use_imperial):
  units = 'm'
  dist = meters
  if use_imperial:
    dist = meters_to_feet(dist)
    units = 'ft'
  dist = '%.2f %s' % (dist, units)
  return dist


@register.filter
def kph_to_prefered_speed(kph, use_imperial):
  speed = kph
  units = 'kph'
  if use_imperial:
    speed = km_to_miles(speed)
    units = 'mph'
  speed = '%.2f %s' % (speed, units)
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
def date_to_js_epoch(date):
  return int(date.strftime('%s')) * 1000

@register.filter
def value_or_zero(value):
  if not value:
    value = 0
  return value
