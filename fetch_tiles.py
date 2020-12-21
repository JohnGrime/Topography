import sys, math, os, time, argparse, requests

class TileSource:

	info = {
		'usgs': {
			'name': 'usgs',
			'url': 'https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile/{zoom}/{y}/{x}',
			'fmt': 'png',
			'tile_size': 256,
		},

		'google': {
			'name': 'google',
			'url': 'https://mt0.google.com/vt/lyrs=s&x={x}&y={y}&z={zoom}',
			'fmt': 'jpg',
			'tile_size': 256,
		}
	}

	def __init__(self, source_name):
		name = source_name.lower()
		if name not in TileSource.info:
			print(f'Unknown image source {source_name}')
			sys.exit(-1)

		self.info = TileSource.info[name]

	def get_url(self, x, y, zoom):
		url = self.info['url']
		p = {'x': x, 'y': y, 'zoom': zoom}
		return url.format(**p)

	def get_filepath(self, cache_dir, x, y, zoom):
		fpath = f'{self.info["name"]}_{zoom}_{x}_{y}.{self.info["fmt"]}'
		return os.path.join(cache_dir, fpath)

	def stream_to_file(self, x, y, zoom, out_path, chunk_bytes=512*1024, update_bytes=256*1024):
		url = self.get_url(x, y, zoom)

		r = requests.get(url, params={}, stream=True)
		if r.status_code == 404:
			print()
			print(f'{r.url} : not found! Stopping here.')
			print(r)
			print()
			sys.exit(-1)

		with open(out_path, 'wb') as fd:
			n_chunks, bytes_read, next_update = 0, 0, update_bytes
			for chunk in r.iter_content(chunk_size=chunk_bytes):
				fd.write(chunk)

				n_chunks += 1
				bytes_read += len(chunk)
				if bytes_read >= next_update:
					print(f'  Read {n_chunks} chunks, {bytes_read/(1024*1024):.2f} MiB')
					next_update += update_bytes

		return url, bytes_read



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
# https://en.wikipedia.org/wiki/Web_Mercator_projection
# https://en.wikipedia.org/wiki/Mercator_projection#Alternative_expressions
#
# This projection has problems at the poles; e.g. Google Maps cuts off above
# and below latitudes of +/- 85.051129.
#
# Returns: pixel (x,y) tuple describing the specified point; pixel coords are
# not neccessarily integers!
#
def web_mercator(lat_degs, lon_degs, zoom_level, tile_size):
	pi, twopi = math.pi, 2.0*math.pi
	log, tan = math.log, math.tan

	# Latitude and longitude in radians
	lat, lon = lat_degs * pi/180.0, lon_degs * pi/180.0

	prefactor = float(tile_size)/twopi * (2.0**zoom_level)
	pix_x = prefactor * (lon + pi)
	pix_y = prefactor * (pi - log(tan(pi/4 + lat/2)))

	return (pix_x, pix_y)


##########################
# Main code starts here. #
##########################

#
# Duplicate stdout/stderr to file, and deal with command line arguments
#

tee_stdout = Tee('stdout.txt', 'w', 'stdout')
tee_stderr = Tee('stderr.txt', 'w', 'stderr')

parser = argparse.ArgumentParser( description='', epilog='' )

opts = parser.add_argument_group('Region of interest')

opts.add_argument('-src', required = True, type = str,
	help = 'Source of satellite tile data',
	choices = TileSource.info.keys())

opts.add_argument('-lat', required = True, type = float, nargs = 2,
	help = 'Min and max latitude in degrees (south pole at -90, north poles at +90)')

opts.add_argument('-lon', required = True, type = float, nargs = 2,
	help = 'Min and max longitude in degrees (-180 to +180, positive is east')

opts.add_argument('-zoom', required = True, type = int,
	help = 'Zoom level (0 to 23, larger values include more detail)')

opts = parser.add_argument_group('Data caching')

opts.add_argument('-cache', required = False, type = str,
	default = 'cache',
	help = 'Directory name for cached tile data')

opts = parser.add_argument_group('Tile combination')

opts.add_argument('-combine', required = False,
	action = 'store_true',
	help = 'If specified, combine tiled data into single image')

if len(sys.argv)<2:
	parser.parse_args([sys.argv[0], '-h'])

args = parser.parse_args()

if args.lon[0] > args.lon[1]:
	print('Please enter longitudes in ASCENDING order.')
	sys.exit(-1)

if args.lat[0] > args.lat[1]:
	print('Please enter latitudes in ASCENDING order.')
	sys.exit(-1)

#
# Convert lat/lon to pixels (x_pix,y_pix), tiles (x_tile,y_tile),
# and pixel offsets into tiles (x_sub,y_sub).
#

tilesrc = TileSource(args.src)

tile_size = tilesrc.info['tile_size']

_x0, _y0 = web_mercator(args.lat[0], args.lon[0], args.zoom, tile_size)
_x1, _y1 = web_mercator(args.lat[1], args.lon[1], args.zoom, tile_size)

x_pix, y_pix   = [_x0, _x1], [_y0, _y1]

# If needed, swap orders to ensure ascending values
if x_pix[0] > x_pix[1]: x_pix.reverse()
if y_pix[0] > y_pix[1]: y_pix.reverse()

x_tile, y_tile = [int(x/tile_size) for x in x_pix], [int(y/tile_size) for y in y_pix]
x_sub, y_sub   = [int(x%tile_size) for x in x_pix], [int(y%tile_size) for y in y_pix]

#
# Give the user some feedback
#

print()
print(f'Run at: {time.asctime()}')
print(f'Run as: {" ".join(sys.argv)}')
print()
print('Inputs:')
print()
print(f'  Tile source          : {args.src}')
print(f'  Latitude (degrees)   : {args.lat[0]} to {args.lat[1]}')
print(f'  Longitude (degrees)  : {args.lon[0]} to {args.lon[1]}')
print(f'  Zoom level           : {args.zoom}')
print(f'  Tile cache directory : "{args.cache}"')
print()
print('Outputs')
print()
print(f'  Pixel (y0,y1) => (tile:subpixel,tile:subpixel) : ({y_pix[0]:.2f},{y_pix[1]:.2f}) => ({y_tile[0]}:{y_sub[0]},{y_tile[1]}:{y_sub[1]})')
print(f'  Pixel (x0,x1) => (tile:subpixel,tile:subpixel) : ({x_pix[0]:.2f},{x_pix[1]:.2f}) => ({x_tile[0]}:{x_sub[0]},{x_tile[1]}:{x_sub[1]})')
print()

#
# Download, cache, and combine tiles (latter optional)
#

if os.path.isdir(args.cache) == False:
	try:
		os.mkdir(args.cache)
	except OSError:
		print(f'Unable to create cache directory "{args.cache}"; halting here.');
		sys.exit(-1)
	else:
		print(f'Created missing cache directory "{args.cache}"')

# Tile spans on x and y axes
nx_tile = (x_tile[1]-x_tile[0]) + 1
ny_tile = (y_tile[1]-y_tile[0]) + 1

# How many pixels are the raw and cropped images?
nx_pix = int(x_pix[1]-x_pix[0])+1
ny_pix = int(y_pix[1]-y_pix[0])+1

reduction = 100.0 * (1.0 - (nx_pix*ny_pix)/(nx_tile*tile_size * ny_tile*tile_size))

print(f'Requires {nx_tile} x {ny_tile} tile set ({nx_tile*ny_tile} tiles total)')
print(f'Uncropped image is {nx_tile*tile_size} x {nx_tile*tile_size} pixels')
print(f'Cropped image is {nx_pix} x {ny_pix} pixels ({reduction:.2f}% reduction)')
print(f'Downloading...')

# Import Python Imaging Library (PIL), Pillow, or equivalent
if args.combine:
	from PIL import Image
	combined = Image.new("RGB", (nx_tile*tile_size, ny_tile*tile_size))

# Download tile sets, combining (if needed) into a single image as we go
n, N, checkpoint_, delta_checkpoint_ = 0, nx_tile*ny_tile, 1, 10
for dy in range(ny_tile):
	for dx in range(nx_tile):
		x, y = x_tile[0]+dx, y_tile[0]+dy
		n += 1
		out_path = tilesrc.get_filepath(args.cache, x, y, args.zoom)

		# Update user on progress every delta_checkpoint_ percent
		if ( (100*n)/N > (checkpoint_*delta_checkpoint_) ):
			print(f'  {out_path} : {n}/{N} ({(100.0*n)/N:.0f}%)')
			checkpoint_ += 1

		if os.path.isfile(out_path):
			# tile is already in the cache
			pass
		else:
			# fetch tile from remote server & save to file cache
			tilesrc.stream_to_file(x, y, args.zoom, out_path)

		if args.combine:
			img = Image.open(out_path)
			combined.paste(img, (dx*tile_size, dy*tile_size))

# Use PNG as output format
if args.combine:
	print()

	print(f'Saving combined.raw.png ...')
	combined.save("combined.raw.png");

	x0, y0 = x_sub[0], y_sub[0]
	x1, y1 = ((nx_tile-1)*tile_size)+x_sub[1], ((ny_tile-1)*tile_size)+y_sub[1]
	
	print(f'Cropping ...')
	combined = combined.crop( (x0,y0, x1,y1) )

	print(f'Saving combined.cropped.png ...')
	combined.save("combined.cropped.png");

print('Done.')
