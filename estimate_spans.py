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

# For a given latitude, how many degrees correspond to 1m?
def latlon_degs_per_m(lat_degs, earth_radius_m = 6.371e6):
	r = earth_radius_m

	# Metres per degree latitude is constant, regardless of latitude
	dLat = (1.0*180.0)/(math.pi*r)

	# radius of circle arc along the longitudinal span depends on the latitude.
	theta = lat_degs * (math.pi/180.0) # in radians
	r = earth_radius_m * math.cos(theta)
	dLon = (1.0*180.0)/(math.pi*r)

	return dLat, dLon

def basic(args):
	lat_degs = float(args[0])
	dLat, dLon = latlon_degs_per_m(lat_degs)
	print(f'degs lat,lon for 1m @ lat={lat_degs}: {dLat}, {dLon}')

def m_span_to_latlon(args):
	lat_degs = float(args[0])
	lon_degs = float(args[1])
	lat_span_m = float(args[2])
	lon_span_m = float(args[3])
	dLat, dLon = latlon_degs_per_m(lat_degs)
	dLat, dLon = lat_span_m*dLat, lon_span_m*dLon
	print(f'-lat {lat_degs-dLat/2} {lat_degs+dLat/2} -lon {lon_degs-dLon/2} {lon_degs+dLon/2}')

def latlon_span_to_m(args):
	lat0, lat1 = [float(x) for x in args[0:2]]
	lon0, lon1 = [float(x) for x in args[2:4]]
	lat_span, lon_span0, lon_span1 = span_in_m(lat0,lat1, lon0,lon1)
	print(f'lat span: {lat_span}, lon span at lat0: {lon_span0}, lon span at lat1: {lon_span1}')

def print_usage(prog):
		print()
		print('Usage:')
		print()
		print(f'[1]  python3 {sys.argv[0]} lat_degs')
		print(f'[2]  python3 {sys.argv[0]} to_deg lat_degs lon_degs lat_span_m lon_span_m')
		print(f'[3]  python3 {sys.argv[0]} to_m lat0 lat1 lon0 lon1')
		print()
		print('Where:')
		print()
		print(f'[1] : report estimated lat/lon intervals (degs) corresponding to 1m at specified latitude (degs)')
		print(f'[2] : report estimated span (m) corresponding to specified bounding box (degs)')
		print(f'[3] : report estimated lat/lon intervals (degs) corresponding to span_m around specified latitude (degs)')
		print()
		sys.exit(-1)

try:
	if len(sys.argv) < 2:
		print_usage(sys.argv[0])
	elif len(sys.argv) == 2:
		basic(sys.argv[1:])
	else:
		what = sys.argv[1]
		args = sys.argv[2:]
		if what == 'to_m':
			latlon_span_to_m(args)
		elif what == 'to_deg':
			m_span_to_latlon(args)
		else:
			print_usage(sys.argv[0])
except Exception as e:
	print(e)
	print_usage(sys.argv[0])
