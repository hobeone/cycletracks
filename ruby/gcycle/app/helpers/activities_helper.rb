module ActivitiesHelper
  def activity_google_map_link(activity)
    return '<a href="http://maps.google.com/maps?q='+activity_url(activity)+'.kml&t=p">Bigger Map</a>'
  end
end
