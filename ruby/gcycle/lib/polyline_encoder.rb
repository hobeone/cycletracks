# polyline_encoder.rb by George Lantz August 2007
# This is line by line exactly the same as the 
# javascript class from Mark McClure except
# I have taken out what is not needed, see below.
#
# PolylineEncoder.js by Mark McClure  April/May 2007
# 
# This module defines a PolylineEncoder class to encode
# polylines for use with Google Maps together with a few
# auxiliary functions.
#
# Google map reference including encoded polylines:
#   http://www.google.com/apis/maps/documentation/
#
# Details on the algorithm used here:
#   http://facstaff.unca.edu/mcmcclur/GoogleMaps/EncodePolyline/
#
# Constructor:
#   polylineEncoder = PolylineEncoder.new(numLevels?, 
#     zoom_factor?, very_small?, force_endpoints?)
# where num_levels and zoom_factor indicate how many 
# different levels of magnification the polyline has
# and the change in magnification between those levels,
# very_small indicates the length of a barely visible 
# object at the highest zoom level, force_endpoints 
# indicates whether or not the  endpoints should be 
# visible at all zoom levels.  force_endpoints is 
# optional with a default value of true.  Probably 
# should stay true regardless.
#
# MODIFIED BY HOBE:
# take a 2d array rather than array of Point()
#
#
# Main methods:
# PolylineEncoder.dp_encode(points)
# Accepts an array of objects (see below)
# Returns an encoded polyline that may
#  be directly overlayed on a Google Map
#
# Usage Example:
# -------------------------------------------------------------
# A simple point class example:
# You will probably want to use something different
# Remember dp_encode accepts an array of objects
#
#
# points = Array.new
# points << [36.97005, -93.29783]
# points << [36.97005,  -93.29410000000001]
#
# polyline_encoder = PolylineEncoder.new
# polyline_encoder.dp_encode(points)
#
# polyline_encoder.encoded_points
# polyline_encoder.encoded_levels
#
# Also I added a decoder as well:
# polyline_encoder = PolylineEncoder.new
# polyline_encoder.dp_encode(encoded_polyline)
#---------------------------------------------------------------

class PolylineEncoder
  attr_reader :encoded_points, :encoded_levels, :encoded_points_literal

  def initialize(options = {})
    @num_levels = options[:num_levels] || 18
    @zoom_factor = options[:zoom_factor] || 2
    @very_small = options[:very_small] || 0.00001
    @force_endpoints = options[:force_endpoints] || true
    @zoom_level_breaks = Array.new
    for i in 0 .. @num_levels do
      @zoom_level_breaks[i] = @very_small * (@zoom_factor ** (@num_levels-i-1))
    end
  end

  # The main function.  Essentially the Douglas-Peucker
  # algorithm, adapted for encoding. Rather than simply
  # eliminating points, we record their distance from the
  # segment which occurs at that recursive step.  These
  # distances are then easily converted to zoom levels.
  def dp_encode(points)
    abs_max_dist = 0
    stack = Array.new
    dists = Array.new
    max_dist, max_loc, temp, first, last, current = 0

    if points.length > 2
      stack.push([0, points.length-1])
      while stack.length > 0 
        current = stack.pop
        max_dist = 0

        i = current[0]+1
        while i < current[1]
          temp = distance(points[i], 
                          points[current[0]], points[current[1]])
          if temp > max_dist
            max_dist = temp
            max_loc = i
            if max_dist > abs_max_dist
              abs_max_dist = max_dist
            end
          end
          i += 1
        end

        if max_dist > @very_small
          dists[max_loc] = max_dist
          stack.push([current[0], max_loc])
          stack.push([max_loc, current[1]])
        end
      end
    end
    @encoded_points = create_encodings(points, dists)
    @encoded_levels = encode_levels(points, dists, abs_max_dist)
    @encoded_points_literal = @encoded_points.gsub("\\", "\\\\\\\\")
  end

  private

  # distance(p0, p1, p2) computes the distance between the point p0
  # and the segment [p1,p2].  This could probably be replaced with
  # something that is a bit more numerically stable.
  def distance(p0,p1,p2)
    p0lat, p0long = p0
    p1lat, p1long = p1
    p2lat, p2long = p2
    if p1lat == p2lat and p1long == p2long
      out = Math.sqrt(((p2lat - p0lat)**2) + ((p2long - p0long)**2))
    else
      u = ((p0lat - p1lat)*(p2lat - p1lat)+(p0long - p1long)*(p2long - p1long))/
        (((p2lat - p1lat)**2) + ((p2long - p1long)**2))
      if u <= 0
        out = Math.sqrt( ((p0lat - p1lat)**2 ) + ((p0long - p1long)**2) )
      end
      if u >= 1
        out = Math.sqrt(((p0lat - p2lat)**2) + ((p0long - p2long)**2))
      end
      if 0 < u and u < 1
        out = Math.sqrt( ((p0lat-p1lat-u*(p2lat-p1lat))**2) +
          ((p0long-p1long-u*(p2long-p1long))**2) )
      end
    end
    return out
  end

  # The createEncodings function is very similar to Google's
  # http://www.google.com/apis/maps/documentation/polyline.js
  # The key difference is that not all points are encoded, 
  # since some were eliminated by Douglas-Peucker.
  def create_encodings(points, dists)
    plat = 0
    plng = 0
    encoded_points = ""
     for i in 0 .. points.length do
      if !dists[i].nil? || i == 0 || i == points.length-1 
        point = points[i]
        lat = point[0]
        lng = point[1]
        late5 = (lat * 1e5).floor
        lnge5 = (lng * 1e5).floor
        dlat = late5 - plat
        dlng = lnge5 - plng
        plat = late5
        plng = lnge5
        encoded_points << encode_signed_number(dlat) + 
          encode_signed_number(dlng)
      end
    end
    return encoded_points
  end

  # This computes the appropriate zoom level of a point in terms of it's 
  # distance from the relevant segment in the DP algorithm.  Could be done
  # in terms of a logarithm, but this approach makes it a bit easier to
  # ensure that the level is not too large.
  def compute_level(dd)
    lev = 0
    if dd > @very_small
      while dd < @zoom_level_breaks[lev]
        lev += 1
      end
      return lev
    end
  end

  # Now we can use the previous function to march down the list
  # of points and encode the levels.  Like create_encodings, we
  # ignore points whose distance (in dists) is undefined.
  def encode_levels(points, dists, absMaxDist)
    encoded_levels = ""
    if @force_endpoints
      encoded_levels << encode_number(@num_levels-1)
    else
      encoded_levels << encode_number(@num_levels-compute_level(abs_max_dist)-1)
    end
    for i  in 1 .. points.length-1
      if !dists[i].nil?
        encoded_levels << encode_number(@num_levels-compute_level(dists[i])-1)
      end
    end
    if @force_endpoints
      encoded_levels << encode_number(@num_levels-1)
    else
      encoded_levels << this.encode_number(@num_levels-compute_level(abs_max_dist)-1)
    end
    return encoded_levels
  end

  # This function is very similar to Google's, but I added
  #some stuff to deal with the double slash issue.
  def encode_number(num)
    encode_string = ""
    while num >= 0x20
      next_value = (0x20 | (num & 0x1f)) + 63
      encode_string << next_value.chr
      num >>= 5
    end
    final_value = num + 63
    encode_string << final_value.chr
    return encode_string
  end

  # This one is Google's verbatim.
  def encode_signed_number(num)
    sgn_num = num << 1
    if num < 0
      sgn_num = ~(sgn_num)
    end
    return encode_number(sgn_num)
  end
end
