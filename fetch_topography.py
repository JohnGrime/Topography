import sys, argparse, requests, time

#
# Example: python3 whatever.py -fmt AAIGrid -dem SRTMGL1 -file output -lon -119.25 -119 -lat 36.5 37
#

base_url = 'https://portal.opentopography.org/API/globaldem'

dem_map = {
	'SRTMGL1': {
		'desc': 'Shuttle Radar Topography Mission GL1 (Global 30m)',
	},

	'SRTMGL1_E': {
		'desc': 'Shuttle Radar Topography Mission GL1 ellipsoidal (Global 30m)',
	},

	'SRTMGL3': {
		'desc': 'Shuttle Radar Topography Mission GL3 (Global 90m)',
	},

	'AW3D30': {
		'desc': 'ALOS World 3D 30m',
	},

	'AW3D30_E': {
		'desc': 'ALOS World 3D ellipsoidal (30m)',
	},
}

out_map = {
	'AAIGrid': {
		'desc': 'Arc ASCII Grid',
		'suffix': 'asc',
	},

	'GTiff': {
		'desc': 'GeoTiff',
		'suffix': 'tiff',
	},
}

def stream_to_file(req, path, chunk_bytes=512*1024, update_bytes=256*1024):
	with open(path, 'wb') as fd:
		n_chunks, bytes_read, next_update = 0, 0, update_bytes
		for chunk in req.iter_content(chunk_size=chunk_bytes):
			fd.write(chunk)
			n_chunks += 1
			bytes_read += len(chunk)

			if bytes_read >= next_update:
				print(f'Read {n_chunks} chunks, {bytes_read/(1024*1024):.2f} MiB')
				next_update += update_bytes

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
# Command line argument handling
#

dem_arg_txt = ', '.join([f'{k} = {dem_map[k]["desc"]}' for k in dem_map])
out_arg_txt = ', '.join([f'{k} = {out_map[k]["desc"]}' for k in out_map])

tee_stdout = Tee('stdout.txt', 'w', 'stdout')
tee_stderr = Tee('stderr.txt', 'w', 'stderr')

parser = argparse.ArgumentParser( description='', epilog='' )

opts = parser.add_argument_group('Region of interest')

opts.add_argument('-lat', required = True, type = float, nargs = 2,
	help = 'Min and max latitude in degrees (south pole at -90, north poles at +90)')

opts.add_argument('-lon', required = True, type = float, nargs = 2,
	help = 'Min and max longitude in degrees (-180 to +180, positive is east')

opts = parser.add_argument_group('Data sources, formats, etc')

opts.add_argument('-dem', required = False, type = str,
	default = 'SRTMGL1', choices = [k for k in dem_map],
	help = 'Source DEM data; ' + dem_arg_txt)

opts.add_argument('-fmt', required = False, type = str,
	default = 'GTiff', choices = [k for k in out_map],
	help = 'Output file format; ' + out_arg_txt)

opts.add_argument('-file', required = False, type = str,
	default = 'output',
	help = 'Output file path prefix')

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
# Fetch elevation data
#

r = requests.get(base_url, stream = True, params = {
	'demtype': args.dem,
	'west': args.lon[0],
	'east': args.lon[1],
	'south': args.lat[0],
	'north': args.lat[1],
	'outputFormat': args.fmt,
	})

if r.status_code == 404:
	print()
	print(f'{r.url} : not found! Stopping here.')
	print(r)
	print()
	sys.exit(-1)


out_path = args.file + '.' + out_map[args.fmt]['suffix']

print()
print(f'Run at: {time.asctime()}')
print(f'Run as: {" ".join(sys.argv)}')
print()
print(f'Fetching {out_map[args.fmt]["desc"]} from {dem_map[args.dem]["desc"]} ...')
print(f'{r.url} => {out_path}')
print()

stream_to_file(r, out_path)

print('Done.')
