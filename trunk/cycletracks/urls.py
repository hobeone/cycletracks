from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
  (r'^$', 'gcycle.views.dashboard'),
  (r'^dashboard/(\w+)?/$', 'gcycle.views.dashboard'),
  (r'^upload/$', 'gcycle.views.upload'),
  (r'^activity/show/(\S+)$', 'gcycle.activity.show'),
  (r'^chart/$', 'gcycle.views.chart'),
  (r'^map/$', 'gcycle.views.map'),
  (r'^chart_bpm/(\S+)$', 'gcycle.views.chart_bpm'),
  (r'^chart_cadence/(\S+)$', 'gcycle.views.chart_cadence'),
  (r'^chart_speed/(\S+)$', 'gcycle.views.chart_speed'),
  (r'^chart_altitude/(\S+)$', 'gcycle.views.chart_altitude'),
)
