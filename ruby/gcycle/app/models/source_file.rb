class SourceFile < ActiveRecord::Base
  belongs_to :activity
  validates_presence_of :filename, :filedata
  def filedata=(filedata)
    write_attribute(:filedata, ActiveSupport::Gzip.compress(filedata))
  end
  def filedata
    ActiveSupport::Gzip.decompress(read_attribute(:filedata))
  end
end
