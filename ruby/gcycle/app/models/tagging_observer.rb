class TaggingObserver < ActiveRecord::Observer
  def after_save(tagging)
    tagging.taggable.updated_at = Time.now.utc
    tagging.taggable.save
  end
end

