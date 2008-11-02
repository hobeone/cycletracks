class Array
  def mean
    return 0 if size == 0
    inject(0){ |sum,x| x ? sum + x : sum + 0 } / size
  end
end
