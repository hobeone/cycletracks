def average(array, default=0):
  if len(array) == 0: return default
  return (sum(array) / float(len(array)))
