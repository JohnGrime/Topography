# Author: John Grime

import sys, math

#
# Duplicate data written to a file handle to another file. Works in a similar
# manner to e.g. the 'tee' shell command.
#
# https://stackoverflow.com/questions/616645/how-to-duplicate-sys-stdout-to-a-log-file
#
class Tee(object):

	def __init__(self, name, mode, what='stdout'):
		self.file = open(name, mode)
		self.what = what

		if self.what == 'stdout':
			self.stream = sys.stdout
			sys.stdout = self
		elif self.what == 'stderr':
			self.stream = sys.stderr
			sys.stderr = self
			# ensure file is unbuffered?
		else:
			print(f'Unknown Tee type "{self.what}"')
			sys.exit(-1)

	def __del__(self):
		if self.what == 'stdout':
			sys.stdout = self.stream
		elif self.what == 'stderr':
			sys.stderr = self.stream

		self.file.close()

	def write(self, data):
		self.file.write(data)
		self.stream.write(data)
		if self.what == 'stderr': self.flush()

	def flush(self):
		self.file.flush()

#
# Web Mercator projection, see:
#
# https://en.wikipedia.org/wiki/Web_Mercator_projection
# https://en.wikipedia.org/wiki/Mercator_projection#Alternative_expressions
#
# This projection has problems at the poles; e.g. Google Maps cuts off above
# and below latitudes of +/- 85.051129.
#
# Lat/lon input assumed to be in degrees
# World coords are normalized onto the whole global map
# Pixel values are valid only at the specified zoom level
#
class WebMercator:

	to_rad = math.pi/180.0
	to_deg = 180.0/math.pi

	@staticmethod
	def lonlat_to_world(lon: float, lat: float) -> (float, float):
		pi, twopi = math.pi, 2.0*math.pi
		lat, lon = lat*WebMercator.to_rad, lon*WebMercator.to_rad
		x = lon + pi
		y = pi - math.log(math.tan(pi/4 + lat/2))
		return x/twopi, y/twopi

	@staticmethod
	def world_to_lonlat(wx: float, wy: float) -> (float, float):
		pi, twopi = math.pi, 2.0*math.pi
		lon = wx*twopi - pi
		lat = 2.0*math.atan(math.exp(-(wy*twopi-pi))) - pi/2
		return lon*WebMercator.to_deg, lat*WebMercator.to_deg

	@staticmethod
	def lonlat_to_pix(lon: float, lat: float, zoom: int, tile_size: int = 256) -> (float, float):
		wx, wy = WebMercator.lonlat_to_world(lon,lat)
		return WebMercator.world_to_pix(wx, wy, zoom, tile_size)

	@staticmethod
	def pix_to_lonlat(px: float, py: float, zoom: int, tile_size: int = 256) -> (float, float):
		wx,wy = self.pix_to_world(px, py, zoom, tile_size)
		return WebMercator.world_to_lonlat(wx, wy)

	@staticmethod
	def world_to_pix(wx: float, wy: float, zoom: int, tile_size: int = 256) -> (float, float):
		C = float(tile_size) * (2**zoom)
		return wx*C, wy*C

	@staticmethod
	def pix_to_world(px: float, py: float, zoom: int, tile_size: int = 256) -> (float, float):
		C = float(tile_size) * (2**zoom)
		return px/C, py/C

#
# Convert latitude and longitude spans in degrees into spans in metres.
# Note that longitude span depends on latitude, but latitude span same
# for any longitude.
#
def latlon_span_in_m(
	lat_min_degs, lat_max_degs,
	lon_min_degs, lon_max_degs,
	earth_radius_m = 6.371e6):

	deg_to_m = lambda r: (2.0*math.pi*r)/360.0

	r = earth_radius_m
	lat_span_m = (lat_max_degs-lat_min_degs) * deg_to_m(r)

	# radius of circle arc along the longitudinal span depends on the latitude.

	theta = lat_min_degs * (math.pi/180.0) # in radians
	r = earth_radius_m * math.cos(theta)
	lon_span0_m = (lon_max_degs-lon_min_degs) * deg_to_m(r)

	theta = lat_max_degs * (math.pi/180.0) # in radians
	r = earth_radius_m * math.cos(theta)
	lon_span1_m = (lon_max_degs-lon_min_degs) * deg_to_m(r)

	return lat_span_m, lon_span0_m, lon_span1_m

#
# For a given latitude, how many lat/lon degrees correspond to 1m?
#
def latlon_degs_per_m(lat_degs, earth_radius_m = 6.371e6):
	r = earth_radius_m

	# Metres per degree latitude is constant, regardless of latitude
	dLat_degs = (1.0*180.0)/(math.pi*r)

	# radius of circle arc along the longitudinal span depends on the latitude.
	theta = lat_degs * (math.pi/180.0) # in radians
	r = earth_radius_m * math.cos(theta)
	dLon_degs = (1.0*180.0)/(math.pi*r)

	return dLat_degs, dLon_degs

#
# Stream data from request to specified file.
#
def stream_to_file(req, path: str, chunk_bytes: int = 512*1024, update_bytes: int = 256*1024) -> (int):
	with open(path, 'wb') as fd:
		n_chunks, bytes_read, next_update = 0, 0, update_bytes
		for chunk in req.iter_content(chunk_size=chunk_bytes):
			fd.write(chunk)
			n_chunks += 1
			bytes_read += len(chunk)

			if bytes_read >= next_update:
				print(f'Read {n_chunks} chunks, {bytes_read/(1024*1024):.2f} MiB')
				next_update += update_bytes
	return bytes_read
