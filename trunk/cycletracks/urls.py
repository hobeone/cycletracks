from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
  (r'^$', 'gcycle.views.dashboard'),
  (r'^dashboard/(\w+)?/?$', 'gcycle.views.dashboard'),
  (r'^dashboard_dojo/$', 'gcycle.views.dashboard_dojo'),
  (r'^upload/$', 'gcycle.views.upload'),
  (r'^activity/show/(\S+)$', 'gcycle.activity.show'),
  (r'^activity/graph/(\S+)$', 'gcycle.activity.graph'),
  (r'^chart/$', 'gcycle.views.chart'),
  (r'^map/$', 'gcycle.views.map'),
  (r'^dojango/', include('dojango.urls')),
  (r'^activity_name_set/$', 'gcycle.views.activity_name_set'),
  (r'^activity/update/$', 'gcycle.views.activity_update'),
  (r'^datastore.csv$', 'gcycle.views.datastore'),
)
