# Methods added to this helper will be available to all templates in the application.
module ApplicationHelper
  def seconds_to_human_readable(seconds)
    return Duration.new(seconds).format('%h:%m:%s')
  end

  def km_to_miles(km)
    return km * 0.621371192
  end

  def meters_to_feet(meters)
    return meters * 3.280
  end

  def use_metric
    use_metric = true
    if not current_user.nil?
      use_metric = current_user.metric
    end
    return use_metric
  end

  def prefered_distance_with_units(meters)
    dist = meters
    units = 'm'
    if dist > 1000
      dist = dist / 1000
      units = 'km'
      if not use_metric
        dist = km_to_miles(dist)
        units = 'mi'
      end
    else
      if not use_metric
        dist = meters_to_feet(dist)
        units = 'ft'
      end
    end
    return sprintf('%.2f %s', dist, units)
  end

  def meters_to_prefered_distance(meters)
    dist = meters / 1000.0
    dist = km_to_miles(dist) unless use_metric
    return sprintf('%.2f', dist)
  end

  def prefered_distance_units
    return 'km' if use_metric
    return 'mi'
  end

  def prefered_small_distance_units
    return 'm' if use_metric
    return 'ft'
  end

  def kph_to_prefered_speed_with_units(kph)
    dist = kph
    dist = km_to_miles(dist) unless use_metric
    return sprintf('%.2f %s', dist, prefered_speed_units)
  end

  def kph_to_prefered_speed(kph)
    dist = kph
    dist = km_to_miles(dist) unless use_metric
    return sprintf('%.2f', dist)
  end

  def prefered_speed_units
    return 'kph' if use_metric
    return 'mph'
  end
end
