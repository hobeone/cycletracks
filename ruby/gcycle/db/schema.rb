# This file is auto-generated from the current state of the database. Instead of editing this file, 
# please use the migrations feature of Active Record to incrementally modify your database, and
# then regenerate this schema definition.
#
# Note that this schema.rb definition is the authoritative source for your database schema. If you need
# to create the application database on another system, you should be using db:schema:load, not running
# all the migrations from scratch. The latter is a flawed and unsustainable approach (the more migrations
# you'll amass, the slower it'll run and the greater likelihood for issues).
#
# It's strongly recommended to check this file into your version control system.

ActiveRecord::Schema.define(:version => 20081101235805) do

  create_table "activities", :force => true do |t|
    t.string   "name"
    t.string   "sport"
    t.float    "total_meters",    :default => 0.0
    t.datetime "start_time"
    t.datetime "end_time"
    t.integer  "total_time",      :default => 0
    t.integer  "rolling_time",    :default => 0
    t.float    "average_speed",   :default => 0.0
    t.float    "maximum_speed",   :default => 0.0
    t.integer  "average_cadence", :default => 0
    t.integer  "maximum_cadence", :default => 0
    t.integer  "average_bpm",     :default => 0
    t.integer  "maximum_bpm",     :default => 0
    t.integer  "total_calories",  :default => 0
    t.string   "comment"
    t.boolean  "public",          :default => false
    t.text     "encoded_points"
    t.text     "encoded_levels"
    t.float    "total_ascent",    :default => 0.0
    t.float    "total_descent",   :default => 0.0
    t.string   "source_hash"
    t.datetime "created_at"
    t.datetime "updated_at"
  end

  create_table "laps", :force => true do |t|
    t.integer  "activity_id"
    t.float    "total_meters",               :default => 0.0
    t.integer  "total_time_seconds",         :default => 0
    t.integer  "total_rolling_time_seconds", :default => 0
    t.integer  "average_cadence",            :default => 0
    t.integer  "maximum_cadence",            :default => 0
    t.integer  "average_bpm",                :default => 0
    t.integer  "maximum_bpm",                :default => 0
    t.float    "average_speed",              :default => 0.0
    t.float    "maximum_speed",              :default => 0.0
    t.integer  "calories",                   :default => 0
    t.datetime "start_time"
    t.datetime "end_time"
    t.float    "total_ascent",               :default => 0.0
    t.float    "total_descent",              :default => 0.0
    t.text     "bpm_list"
    t.text     "altitude_list"
    t.text     "speed_list"
    t.text     "distance_list"
    t.text     "cadence_list"
    t.text     "geopt_list"
    t.text     "time_list"
    t.datetime "created_at"
    t.datetime "updated_at"
  end

  create_table "users", :force => true do |t|
    t.string   "login",                     :limit => 40
    t.string   "name",                      :limit => 100, :default => ""
    t.string   "email",                     :limit => 100
    t.string   "crypted_password",          :limit => 40
    t.string   "salt",                      :limit => 40
    t.datetime "created_at"
    t.datetime "updated_at"
    t.string   "remember_token",            :limit => 40
    t.datetime "remember_token_expires_at"
    t.string   "activation_code",           :limit => 40
    t.datetime "activated_at"
    t.string   "state",                                    :default => "passive"
    t.datetime "deleted_at"
    t.string   "time_zone"
  end

  add_index "users", ["login"], :name => "index_users_on_login", :unique => true

end
