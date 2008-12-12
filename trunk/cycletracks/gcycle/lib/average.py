def average(array, default=0):
  if len(array) == 0: return default
  return (sum(array) / float(len(array)))


def movingAverage3(s):
  return map(lambda x,y,z: (x+y+z)/3.0, s[0:-2], s[1:-1], s[2:])
