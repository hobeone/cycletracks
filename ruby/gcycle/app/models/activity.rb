require 'polyline_encoder'
require 'pp'
 class Point
   attr_accessor :lat, :lng
   def initialize(lat, lng)
     @lat, @lng = lat, lng
   end
 end

class Activity < ActiveRecord::Base
  serialize :sw_point
  serialize :ne_point
  serialize :start_point
  serialize :mid_point
  serialize :end_point

  belongs_to :user
  has_one :source_file
  has_many :laps, :order => 'start_time', :dependent => :delete_all
  validates_associated :laps, :user, :source_file

  validates_presence_of :name, :start_time, :end_time, :laps, :user, :source_file

  # ints
  validates_numericality_of(:total_time, :rolling_time,
                            :average_cadence, :maximum_cadence, :average_bpm,
                            :maximum_bpm, :total_calories,
                            :only_integer => true)
  # floats
  validates_numericality_of(:total_meters, :average_speed, :maximum_speed,
                            :total_ascent, :total_descent)

  validates_uniqueness_of(:source_hash)

  def validate
    if self.rolling_time > self.total_time
      errors.add("rolling_time", "is greater than total_time")
    end
  end

  def time_list
    self.laps.map{|l| l.time_list}.flatten
  end
  def altitude_list
    self.laps.map{|l| l.altitude_list}.flatten
  end
  def speed_list
    self.laps.map{|l| l.speed_list}.flatten
  end
  def cadence_list
    self.laps.map{|l| l.cadence_list}.flatten
  end
  def distance_list
    self.laps.map{|l| l.distance_list}.flatten
  end
  def bpm_list
    self.laps.map{|l| l.bpm_list}.flatten
  end

  def compute_data_from_laps!
    self.total_meters = laps.map{|l| l.total_meters}.sum
    self.total_time = laps.map{|l| l.total_time_seconds}.sum
    self.rolling_time = laps.map{|l| l.total_rolling_time_seconds }.sum
    self.total_calories = laps.map{|l| l.calories}.sum
    self.total_ascent = laps.map{|l| l.total_ascent}.sum
    self.total_descent = laps.map{|l| l.total_descent}.sum

    self.start_time = laps[0].start_time
    self.end_time = laps[-1].end_time

    self.average_speed = self.total_meters / self.rolling_time * 3.6
    self.maximum_speed = laps.map{|l| l.maximum_speed}.max * 3.6

    self.average_cadence = laps.map{|l| l.average_cadence}.mean
    self.maximum_cadence = laps.map{|l| l.maximum_cadence}.max

    self.average_bpm = laps.map{|l| l.average_bpm}.mean
    self.maximum_bpm = laps.map{|l| l.maximum_bpm}.max
    points = []
    point_objs = []
    laps.each do |l|
      l.geopt_list.each do |pt|
        points << pt
        point_objs << Point.new(pt[0], pt[1])
      end
    end
    encoder = PolylineEncoder.new()
    encoder.dp_encode(point_objs)
    self.encoded_points = encoder.encoded_points
    self.encoded_levels = encoder.encoded_levels
    minlat, maxlat = 90,-90
    minlong, maxlong = 180,-180
    points.each do |lat,long|
      maxlat = lat if lat > maxlat
      minlat = lat if lat < minlat
      maxlong = long if long > maxlong
      minlong = long if long < minlong
    end
    self.sw_point = [minlat, minlong]
    self.ne_point = [maxlat, maxlong]
    self.start_point = points[0]
    self.mid_point = points[points.length / 2]
    self.end_point = points[-1]
    return self
  end
end
