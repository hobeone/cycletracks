from django.conf.urls.defaults import *

from gcycle import models
from django.views.generic import list_detail
from gcycle import views

activity_list_info = {
  'queryset' : models.Activity.all(),
  'template_name': 'bar.html',
  'allow_empty': True,
  'paginate_by' : 5,
  'extra_context' : {'user_totals' : views.getCurUserTotals}
}


urlpatterns = patterns('',
  (r'^$', 'gcycle.views.dashboard'),
  (r'^dashboard/(\w+)?/?$', 'gcycle.views.dashboard'),
  (r'^upload/$', 'gcycle.views.upload'),
  (r'^activity/show/(\S+)$', 'gcycle.activity.show'),
  (r'^activity/graph/(\S+)$', 'gcycle.activity.graph'),
  (r'^activity/update/$', 'gcycle.activity.update'),
  (r'mytracks/$', list_detail.object_list, activity_list_info),
  (r'^mytracks/page(?P<page>[0-9]+)/$', list_detail.object_list,
    activity_list_info)


)
