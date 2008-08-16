from django.conf.urls.defaults import *

from gcycle import views

handler500 = 'gcycle.views.handle_view_exception'
urlpatterns = patterns('',
  (r'^$', 'gcycle.views.main'),
  (r'^mytracks/(\S+)?$', 'gcycle.views.dashboard'),
  (r'^upload/$', 'gcycle.views.upload'),
  (r'^about/$', 'gcycle.views.about'),
  (r'^admin/clean/$', 'gcycle.views.clean_broken_acts'),
  (r'^activity/show/(\S+)$', 'gcycle.activity.show'),
  (r'^activity/delete/$', 'gcycle.activity.delete'),
  (r'^activity/kml/(\S+)$', 'gcycle.activity.activity_kml'),
  (r'^activity/graph/(\S+)$', 'gcycle.activity.graph'),
  (r'^activity/update/$', 'gcycle.activity.update'),
  (r'^user/settings/$', 'gcycle.user.settings'),
  (r'^user/update/$', 'gcycle.user.update'),
)
