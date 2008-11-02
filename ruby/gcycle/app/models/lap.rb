class Lap < ActiveRecord::Base
  belongs_to :activity
  serialize :bpm_list
  serialize :altitude_list
  serialize :speed_list
  serialize :distance_list
  serialize :cadence_list
  serialize :geopt_list
  serialize :time_list

  validates_presence_of :start_time, :end_time, :bpm_list,
    :altitude_list, :speed_list, :distance_list, :cadence_list, :geopt_list,
    :time_list

  validates_numericality_of :total_meters, :average_speed, :maximum_speed,
    :total_ascent, :total_descent

  validates_numericality_of :total_time_seconds, :total_rolling_time_seconds,
    :average_cadence, :maximum_cadence, :average_bpm, :maximum_bpm, :calories,
    :only_integer => true

  def validate
    if self.total_rolling_time_seconds > self.total_time_seconds
      errors.add('total_rolling_time_seconds',
        'is greater than total_time_seconds')
    end
  end

end
