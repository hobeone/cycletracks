class AddLapActivityIndex < ActiveRecord::Migration
  def self.up
    add_index :laps, :activity_id
  end

  def self.down
    remove_index :laps, :activity_id
  end
end
