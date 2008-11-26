class AddTotalsCacheToUser < ActiveRecord::Migration
  def self.up
    add_column :users, :total_meters, :float, :default => 0.0
    add_column :users, :total_time, :float, :default => 0.0
    add_column :users, :total_ascent, :float, :default => 0.0
    add_column :users, :rolling_time, :float, :default => 0.0
    add_column :users, :average_cadence, :integer, :default => 0
    add_column :users, :maximum_cadence, :integer, :default => 0
    add_column :users, :average_bpm, :integer, :default => 0
    add_column :users, :maximum_bpm, :integer, :default => 0
    add_column :users, :average_speed, :float, :default => 0.0
    add_column :users, :maximum_speed, :float, :default => 0.0
    add_column :users, :total_calories, :integer, :default => 0
  end

  def self.down
    remove_column :users, :total_meters
    remove_column :users, :total_time
    remove_column :users, :total_ascent
    remove_column :users, :rolling_time
    remove_column :users, :average_cadence
    remove_column :users, :maximum_cadence
    remove_column :users, :average_bpm
    remove_column :users, :maximum_bpm
    remove_column :users, :average_speed
    remove_column :users, :maximum_speed
    remove_column :users, :total_calories
  end
end
