import sys, math

# Convert latitude and longitude spans in degrees into spans in metres.
# Note that longitude span depends on latitude, but latitude span same
# for any longitude.
def span_in_m(
	lat_min_degs, lat_max_degs,
	lon_min_degs, lon_max_degs,
	earth_radius_m = 6.371e6):

	deg_to_m = lambda r: (2.0*math.pi*r)/360.0

	r = earth_radius_m
	lat_span = (lat_max_degs-lat_min_degs) * deg_to_m(r)

	# radius of circle arc along the longitudinal span depends on the latitude.

	theta = lat_min_degs * (math.pi/180.0) # in radians
	r = earth_radius_m * math.cos(theta)
	lon_span0 = (lon_max_degs-lon_min_degs) * deg_to_m(r)

	theta = lat_max_degs * (math.pi/180.0) # in radians
	r = earth_radius_m * math.cos(theta)
	lon_span1 = (lon_max_degs-lon_min_degs) * deg_to_m(r)

	return lat_span, lon_span0, lon_span1

try:
	lat0, lat1 = [float(x) for x in sys.argv[1:3]]
	lon0, lon1 = [float(x) for x in sys.argv[3:5]]
except:
	print()
	print(f'Usage: python3 {sys.argv[0]} lat0 lat1 lon0 lon1')
	print()
	sys.exit(-1)

lat_span, lon_span0, lon_span1 = span_in_m(lat0,lat1, lon0,lon1)
print(f'lat span: {lat_span}, lon span at lat0: {lon_span0}, lon span at lat1: {lon_span1}')
