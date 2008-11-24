class Lap < ActiveRecord::Base
  extend ActiveSupport::Memoizable

  belongs_to :activity

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
    if self.start_time > self.end_time
      errors.add('start_time', 'is later than end_time')
    end
  end

  def geopoints_to_kml_order
    return geopt_list.map{|pt| [pt[1],pt[0]]}
  end

  def bpm_list=(list_data)
    write_attribute(:bpm_list, list_data.flatten.join(','))
  end
  def bpm_list
    list = read_attribute(:bpm_list) || []
    list.split(',').map{|b| b.to_i}
  end
  memoize :bpm_list

  def altitude_list=(list_data)
    write_attribute(:altitude_list, list_data.flatten.join(','))
  end
  def altitude_list
    list = read_attribute(:altitude_list) || []
    list.split(',').map{|b| b.to_f}
  end
  memoize :altitude_list

  def speed_list=(list_data)
    write_attribute(:speed_list, list_data.flatten.join(','))
  end
  def speed_list
    list = read_attribute(:speed_list) || []
    list.split(',').map{|b| b.to_f}
  end
  memoize :speed_list

  def distance_list=(list_data)
    write_attribute(:distance_list, list_data.flatten.join(','))
  end
  def distance_list
    list = read_attribute(:distance_list) || []
    list.split(',').map{|b| b.to_f}
  end
  memoize :distance_list

  def cadence_list=(list_data)
    write_attribute(:cadence_list, list_data.flatten.join(','))
  end
  def cadence_list
    list = read_attribute(:cadence_list) || []
    list.split(',').map{|b| b.to_i}
  end
  memoize :cadence_list

  def geopt_list=(pts)
    write_attribute(:geopt_list, pts.map{|p| p.join(',')}.join(':'))
  end
  def geopt_list
    pts = read_attribute(:geopt_list) || []
    pts = pts.split(':')
    pts.map{|p| p.split(',').map{|t| t.to_f} }
  end
  memoize :geopt_list

  def time_list=(list_data)
    write_attribute(:time_list, list_data.flatten.join(','))
  end
  def time_list
    list = read_attribute(:time_list) || []
    list.split(',').map{|b| b.to_f}
  end
  memoize :time_list


end
