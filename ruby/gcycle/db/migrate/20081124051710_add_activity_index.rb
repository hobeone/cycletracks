class AddActivityIndex < ActiveRecord::Migration
  def self.up
    add_index :activities, :user_id
  end

  def self.down
    remove_index :activities, :user_id
  end
end
