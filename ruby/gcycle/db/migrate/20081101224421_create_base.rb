class CreateBase < ActiveRecord::Migration
  def self.up
    create_table "users", :force => true do |t|
      t.column :login,                     :string, :limit => 40
      t.column :name,                      :string, :limit => 100, :default => '', :null => true
      t.column :email,                     :string, :limit => 100
      t.column :crypted_password,          :string, :limit => 40
      t.column :salt,                      :string, :limit => 40
      t.column :created_at,                :datetime
      t.column :updated_at,                :datetime
      t.column :remember_token,            :string, :limit => 40
      t.column :remember_token_expires_at, :datetime
      t.column :activation_code,           :string, :limit => 40
      t.column :activated_at,              :datetime
      t.column :state,                     :string, :null => :no, :default => 'passive'
      t.column :deleted_at,                :datetime
    end
    add_index :users, :login, :unique => true

    create_table :activities do |t|
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
      t.float :total_ascent, :default => 0.0
      t.float :total_descent, :default => 0.0
      t.string :source_hash

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
      t.text :bpm_list
      t.text :altitude_list
      t.text :speed_list
      t.text :distance_list
      t.text :cadence_list
      t.text :geopt_list
      t.text :time_list
      t.timestamps
    end
  end

  def self.down
    drop_table :laps
    drop_table :activities
    drop_table "users"
  end
end
