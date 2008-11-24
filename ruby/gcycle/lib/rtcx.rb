require 'libxml_helper'
class Float
  def precision(pre)
    mult = 10 ** pre
    (self * mult).truncate.to_f / mult
  end
end


class TCXParser
  @@lap_tags = {
    'TotalTimeSeconds'    => [:total_rolling_time_seconds, :to_i],
    'DistanceMeters'      => [:total_meters, :to_f],
    'MaximumSpeed'        => [:maximum_speed, :to_f],
    'Calories'            => [:calories, :to_i],
    'AverageHeartRateBpm' => [:average_bpm, :to_i],
    'MaximumHeartRateBpm' => [:maximum_bpm, :to_i],
    'Cadence'             => [:average_cadence, :to_i],
  }

  @@trackpt_attrs = {
    'AltitudeMeters'                => :altitude,
    'DistanceMeters'                => :distance,
    'HeartRateBpm/tcd:Value'        => :bpm
  }

  def initialize(data)
    @data = data
  end

  def parse_zulu(s)
    return Time.utc(s[0..3].to_i, s[5..6].to_i, s[8..9].to_i,
        s[11..12].to_i, s[14..15].to_i, s[17..18].to_i)
  end

  def parse_trackpoints(trackpoints)
    track_data = {
      :bpm_list      => [],
      :altitude_list => [],
      :speed_list    => [],
      :distance_list => [],
      :cadence_list  => [],
      :geopt_list    => [],
      :time_list     => [],
    }
    start_time = nil
    trackpoints.each do |trackpoint|
      trackpoint.register_default_namespace("tcd")

      time = parse_zulu(trackpoint.at('tcd:Time').content)
      start_time ||= time
      time_delta = time - start_time
      track_data[:time_list] << time_delta

      latitude = trackpoint.at('tcd:Position/tcd:LatitudeDegrees')
      longitude = trackpoint.at('tcd:Position/tcd:LongitudeDegrees')
      if latitude.nil? or longitude.nil?
        if not track_data[:geopt_list].empty?
          track_data[:geopt_list] << track_data[:geopt_list][-1]
        end
      else
        track_data[:geopt_list] << [
          latitude.content.to_f,
          longitude.content.to_f
        ]
      end

      altitude = trackpoint.at('tcd:AltitudeMeters')
      if altitude.nil?
       altitude = track_data[:altitude_list][-1] || 0.0
      else
       altitude = altitude.content.to_f
      end
      track_data[:altitude_list] << altitude

      distance = trackpoint.at('tcd:DistanceMeters')
      if distance.nil?
        distance = track_data[:distance_list][-1] || 0.0
      else
        distance = distance.content.to_f
      end
      track_data[:distance_list] << distance

      bpm = trackpoint.at('tcd:HeartRateBpm/tcd:Value')
      if bpm.nil?
        bpm = track_data[:bpm_list][-1] || 0
      else
        bpm = bpm.content.to_i
      end
      track_data[:bpm_list] << bpm
      cadence = trackpoint.at('tcd:Cadence')
      if cadence.nil?
        cadence = track_data[:cadence_list][-1] || 0
      else
        cadence = cadence.content.to_i
      end
      track_data[:cadence_list] << cadence

      # compute speed
      if track_data[:distance_list].length >= 2
        time_delta = track_data[:time_list][-1] - track_data[:time_list][-2]
        dist_delta = track_data[:distance_list][-1] -
          track_data[:distance_list][-2]
        if time_delta == 0
          track_data[:speed_list] << 0.0
        else
          track_data[:speed_list] << (dist_delta / time_delta).precision(3)
        end
      else
        track_data[:speed_list] << 0.0
      end

    end
    return track_data
  end

  def parse_laps(laps)
    lap_records = []
    laps.each do |lap|
      lap_record = Lap.new()

      lap.register_default_namespace("tcd")
      @@lap_tags.each do |tag,record_info|
        tag_instance = lap.at('tcd:'+tag)
        if not tag_instance.nil?
          lap_record[record_info[0]] = tag_instance.content.send(record_info[1])
        end
      end

      trackpoints = parse_trackpoints(lap.search('//tcd:Trackpoint'))
      trackpoints.each do |k,v|
        lap_record.send(k.to_s+'=', v)
      end

      lap_record.start_time = parse_zulu(lap['StartTime'])
      lap_record.end_time = lap_record.start_time + lap_record.time_list[-1]
      lap_record.average_speed = lap_record.total_meters / (lap_record.end_time - lap_record.start_time) * 3.6

      lap_record.total_time_seconds = lap_record.time_list[-1].to_i
      lap_record.average_cadence = lap_record.cadence_list.mean
      lap_record.maximum_cadence = lap_record.cadence_list.max

      prev_altitude = lap_record.altitude_list[0]
      lap_record.total_ascent = 0
      lap_record.total_descent = 0
      lap_record.altitude_list.each do |i|
        altitude_delta = i - prev_altitude
        if altitude_delta >= 0
          lap_record.total_ascent += altitude_delta
        else
          lap_record.total_descent += altitude_delta * -1
        end
        prev_altitude = i
      end
      lap_records << lap_record
    end
    return lap_records
  end

  def parse
    doc = XML::Parser.new
    doc.string = @data
    doc = doc.parse
    root = doc.root
    root.register_default_namespace("tcd")

    activity_records = []

    root.search('tcd:Activities').each do |activities|
      activities.register_default_namespace("tcd")
      activities.search('tcd:Activity').each do |activity|
        activity.register_default_namespace("tcd")
        laps = parse_laps(activity.search('tcd:Lap'))
        activity_record = Activity.new()
        activity_record.laps = laps
        activity_record.compute_data_from_laps!
        activity_records << activity_record
      end # activity
    end # activities
    return activity_records
  end
end
