# Author: John Grime.

import sys, math, os, time, argparse, requests
from util import Tee, WebMercator, stream_to_file

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

	def make_url(self, x, y, zoom):
		url = self.info['url']
		p = {'x': x, 'y': y, 'zoom': zoom}
		return url.format(**p)

	def make_filepath(self, cache_dir, x, y, zoom):
		fpath = f'{self.info["name"]}_{zoom}_{x}_{y}.{self.info["fmt"]}'
		return os.path.join(cache_dir, fpath)

	def stream_to_file(self, x, y, zoom, out_path, chunk_bytes=512*1024, update_bytes=256*1024):
		url = self.make_url(x, y, zoom)

		r = requests.get(url, params={}, stream=True)
		if r.status_code == 404:
			print()
			print(f'{r.url} : not found! Stopping here.')
			print(r)
			print()
			sys.exit(-1)

		bytes_read = stream_to_file(r, out_path, chunk_bytes, update_bytes)
		return url, bytes_read

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

_x0, _y0 = WebMercator.lonlat_to_pix(args.lon[0], args.lat[0], args.zoom, tile_size)
_x1, _y1 = WebMercator.lonlat_to_pix(args.lon[1], args.lat[1], args.zoom, tile_size)

x_pix, y_pix   = [_x0, _x1], [_y0, _y1]

# If needed, swap orders to ensure ascending values. Redundant, but retained.
if x_pix[0] > x_pix[1]: x_pix.reverse()
if y_pix[0] > y_pix[1]: y_pix.reverse()

# 'ofs' is pixel offset into tile
x_tile, y_tile = [int(x/tile_size) for x in x_pix], [int(y/tile_size) for y in y_pix]
x_ofs, y_ofs   = [int(x%tile_size) for x in x_pix], [int(y%tile_size) for y in y_pix]

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
print(f'  Pixel y range => (tile:offset,tile:offset) : ({y_pix[0]:.2f},{y_pix[1]:.2f}) => ({y_tile[0]}:{y_ofs[0]},{y_tile[1]}:{y_ofs[1]})')
print(f'  Pixel x range => (tile:offset,tile:offset) : ({x_pix[0]:.2f},{x_pix[1]:.2f}) => ({x_tile[0]}:{x_ofs[0]},{x_tile[1]}:{x_ofs[1]})')
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
print()
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
		out_path = tilesrc.make_filepath(args.cache, x, y, args.zoom)

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

	x0, y0 = x_ofs[0], y_ofs[0]
	x1, y1 = ((nx_tile-1)*tile_size)+x_ofs[1], ((ny_tile-1)*tile_size)+y_ofs[1]
	
	print(f'Cropping ...')
	combined = combined.crop( (x0,y0, x1,y1) )

	print(f'Saving combined.cropped.png ...')
	combined.save("combined.cropped.png");

print('Done.')
