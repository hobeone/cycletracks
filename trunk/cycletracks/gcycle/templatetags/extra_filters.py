from django import template
register = template.Library()

def meters_to_miles(value):
  return km_to_miles(value / 1000)
register.filter('meters_to_miles', meters_to_miles)

def km_to_miles(value):
  return value * 0.621371192
register.filter('km_to_miles', km_to_miles)

def seconds_to_hours(seconds):
  return seconds / 60 / 60
register.filter('seconds_to_hours', seconds_to_hours)

def draw_chart(activity_id, kind, width=400, height=200):
  return { 'activity_id': activity_id, 'kind': kind,
           'width' : width, 'height': height}
register.inclusion_tag('chart.html')(draw_chart)
