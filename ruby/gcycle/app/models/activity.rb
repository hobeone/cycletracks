require 'polyline_encoder'

class Activity < ActiveRecord::Base
  serialize :sw_point
  serialize :ne_point
  serialize :start_point
  serialize :mid_point
  serialize :end_point

  belongs_to :user
  has_one :source_file
  has_many :laps, :order => 'start_time', :dependent => :delete_all

  acts_as_taggable_on :tags

  validates_associated :laps, :user, :source_file

  validates_presence_of :name, :start_time, :end_time, :laps, :user,
    :rolling_time, :total_time

  # ints
  validates_numericality_of(:total_time, :rolling_time,
                            :average_cadence, :maximum_cadence, :average_bpm,
                            :maximum_bpm, :total_calories,
                            :only_integer => true)
  # floats
  validates_numericality_of(:total_meters, :average_speed, :maximum_speed,
                            :total_ascent, :total_descent)

  validates_uniqueness_of(:source_hash, :scope => :user_id)

  def validate_on_create
    if self.rolling_time and self.total_time
      if self.rolling_time > self.total_time
        errors.add("rolling_time", "is greater than total_time")
      end
    end

    if self.start_time and self.end_time
      if self.start_time > self.end_time
        errors.add('start_time', 'is later than end_time')
      end
    end

    if self.user and self.user.activities.count > self.user.max_activities
      errors.add(:user,
        "Too many activities for this user (#{self.user.activities.count}"+
        " > #{self.user.max_activities}).")
    end


    if self.maximum_speed != 0.0 and average_speed == 0.0
      errors.add(:average_speed,
        "Average speed can't be 0 if maximum speed is set")
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

  def self.create_from_file!(file, user)
    filedata = File.open(file).read()
    file_hash = OpenSSL::Digest::MD5.hexdigest(filedata)
    activities = TCXParser.new(filedata).parse
    activities.each do |activity|
      activity.user = user
      activity.name = File.basename(file)
      activity.source_hash = file_hash
      activity.source_file = SourceFile.new
      activity.source_file.filename = File.basename(file)
      activity.source_file.filedata = filedata
      activity.save!
    end
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

    self.average_speed = 0
    if self.rolling_time > 0
      self.average_speed = self.total_meters / self.rolling_time * 3.6
    end
    self.maximum_speed = laps.map{|l| l.maximum_speed}.max * 3.6

    self.average_cadence = laps.map{|l| l.average_cadence}.mean
    self.maximum_cadence = laps.map{|l| l.maximum_cadence}.max

    self.average_bpm = laps.map{|l| l.average_bpm}.mean
    self.maximum_bpm = laps.map{|l| l.maximum_bpm}.max
    points = []
    laps.each do |l|
      l.geopt_list.each do |pt|
        points << pt
      end
    end
    encoder = PolylineEncoder.new()
    encoder.dp_encode(points)
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
