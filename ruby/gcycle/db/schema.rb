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

ActiveRecord::Schema.define(:version => 20081121212101) do

  create_table "activities", :force => true do |t|
    t.integer  "user_id"
    t.string   "name"
    t.float    "total_meters"
    t.datetime "start_time"
    t.datetime "end_time"
    t.integer  "total_time"
    t.integer  "rolling_time"
    t.float    "average_speed"
    t.float    "maximum_speed"
    t.integer  "average_cadence"
    t.integer  "maximum_cadence"
    t.integer  "average_bpm"
    t.integer  "maximum_bpm"
    t.integer  "total_calories"
    t.string   "comment"
    t.boolean  "public",                        :default => false
    t.text     "encoded_points"
    t.text     "encoded_levels"
    t.string   "sw_point"
    t.string   "ne_point"
    t.string   "start_point"
    t.string   "mid_point"
    t.string   "end_point"
    t.float    "total_ascent"
    t.float    "total_descent"
    t.string   "source_hash",     :limit => 40
    t.datetime "created_at"
    t.datetime "updated_at"
  end

  create_table "laps", :force => true do |t|
    t.integer  "activity_id"
    t.float    "total_meters"
    t.integer  "total_time_seconds"
    t.integer  "total_rolling_time_seconds"
    t.integer  "average_cadence",                                  :default => 0
    t.integer  "maximum_cadence",                                  :default => 0
    t.integer  "average_bpm",                                      :default => 0
    t.integer  "maximum_bpm",                                      :default => 0
    t.float    "average_speed"
    t.float    "maximum_speed"
    t.integer  "calories",                                         :default => 0
    t.datetime "start_time"
    t.datetime "end_time"
    t.float    "total_ascent",                                     :default => 0.0
    t.float    "total_descent",                                    :default => 0.0
    t.text     "bpm_list",                   :limit => 2147483647
    t.text     "altitude_list",              :limit => 2147483647
    t.text     "speed_list",                 :limit => 2147483647
    t.text     "distance_list",              :limit => 2147483647
    t.text     "cadence_list",               :limit => 2147483647
    t.text     "geopt_list",                 :limit => 2147483647
    t.text     "time_list",                  :limit => 2147483647
    t.datetime "created_at"
    t.datetime "updated_at"
  end

  create_table "source_files", :force => true do |t|
    t.integer  "activity_id"
    t.string   "filename"
    t.binary   "filedata",    :limit => 16777215
    t.datetime "created_at"
    t.datetime "updated_at"
  end

  create_table "taggings", :force => true do |t|
    t.integer  "tag_id"
    t.integer  "taggable_id"
    t.integer  "tagger_id"
    t.string   "tagger_type"
    t.string   "taggable_type"
    t.string   "context"
    t.datetime "created_at"
  end

  add_index "taggings", ["tag_id"], :name => "index_taggings_on_tag_id"
  add_index "taggings", ["taggable_id", "taggable_type", "context"], :name => "index_taggings_on_taggable_id_and_taggable_type_and_context"

  create_table "tags", :force => true do |t|
    t.string "name"
  end

  create_table "users", :force => true do |t|
    t.string   "login",                     :limit => 40
    t.string   "name",                      :limit => 100, :default => ""
    t.string   "email",                     :limit => 100
    t.string   "crypted_password",          :limit => 40
    t.string   "salt",                      :limit => 40
    t.string   "remember_token",            :limit => 40
    t.datetime "remember_token_expires_at"
    t.datetime "created_at"
    t.datetime "updated_at"
    t.boolean  "metric"
    t.boolean  "admin"
    t.string   "timezone",                  :limit => 40
    t.integer  "max_activities",                           :default => 100
  end

  add_index "users", ["login"], :name => "index_users_on_login", :unique => true

end
