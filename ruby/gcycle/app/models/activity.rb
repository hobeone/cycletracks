class Activity < ActiveRecord::Base
  has_many :laps, :dependent => :delete_all
  validates_associated :laps

  validates_presence_of :name, :start_time, :end_time

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
    self.maximum_speed = laps.map{|l| l.maximum_speed}.max

    self.average_cadence = laps.map{|l| l.average_cadence}.mean
    self.maximum_cadence = laps.map{|l| l.maximum_cadence}.max

    self.average_bpm = laps.map{|l| l.average_bpm}.mean
    self.maximum_bpm = laps.map{|l| l.maximum_bpm}.max
  end
end
