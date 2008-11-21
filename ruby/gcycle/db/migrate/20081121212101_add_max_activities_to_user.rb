class AddMaxActivitiesToUser < ActiveRecord::Migration
  def self.up
    add_column :users, :max_activities, :integer, :default => 100
  end

  def self.down
    remove_column :users, :max_activities
  end
end
