class SourceFile < ActiveRecord::Base
  belongs_to :activity
  validates_presence_of :filename, :filedata
end
