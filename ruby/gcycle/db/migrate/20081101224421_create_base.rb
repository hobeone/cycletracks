class CreateBase < ActiveRecord::Migration
  def self.up
    create_table "users", :force => true do |t|
      t.string :login,                     :limit => 40
      t.string :name,                      :limit => 100, :default => '', :null => true
      t.string :email,                     :limit => 100
      t.string :crypted_password,          :limit => 40
      t.string :salt,                      :limit => 40
      t.string :remember_token,            :limit => 40
      t.column :remember_token_expires_at, :datetime
      t.timestamps

      # custom for gcycle
      t.boolean :metric
      t.string :timezone, :limit => 40
    end
    add_index :users, :login, :unique => true

    create_table :activities do |t|
      t.references :user
      t.string :name
      t.string :sport
      t.float :total_meters, :default => 0
      t.datetime :start_time
      t.datetime :end_time
      t.integer :total_time, :default => 0
      t.integer :rolling_time, :default => 0
      t.float :average_speed, :default => 0
      t.float :maximum_speed, :default => 0
      t.integer :average_cadence, :default => 0
      t.integer :maximum_cadence, :default => 0
      t.integer :average_bpm, :default => 0
      t.integer :maximum_bpm, :default => 0
      t.integer :total_calories, :default => 0
      t.string :comment
      t.boolean :public, :default => false
      t.text :encoded_points
      t.text :encoded_levels
      t.string :sw_point
      t.string :ne_point
      t.string :start_point
      t.string :mid_point
      t.string :end_point
      t.float :total_ascent, :default => 0.0
      t.float :total_descent, :default => 0.0
      t.string :source_hash, :limit => 40

      t.timestamps
    end

    create_table :laps do |t|
      t.references :activity
      t.float :total_meters, :default => 0.0
      t.integer :total_time_seconds, :default => 0
      t.integer :total_rolling_time_seconds, :default => 0
      t.integer :average_cadence, :default => 0
      t.integer :maximum_cadence, :default => 0
      t.integer :average_bpm, :default => 0
      t.integer :maximum_bpm, :default => 0
      t.float :average_speed, :default => 0.0
      t.float :maximum_speed, :default => 0.0
      t.integer :calories, :default => 0
      t.datetime :start_time
      t.datetime :end_time
      t.float :total_ascent, :default => 0.0
      t.float :total_descent, :default => 0.0
      t.text :bpm_list, :limit => 16777215
      t.text :altitude_list, :limit => 16777215
      t.text :speed_list, :limit => 16777215
      t.text :distance_list, :limit => 16777215
      t.text :cadence_list, :limit => 16777215
      t.text :geopt_list, :limit => 16777215
      t.text :time_list, :limit => 16777215
      t.timestamps
    end
  end

  def self.down
    drop_table :laps
    drop_table :activities
    drop_table :users
  end
end
