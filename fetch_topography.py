# Author: John Grime.

import sys, argparse, requests, time

from util import Tee, stream_to_file

import geotiff

sources = geotiff.Downloader.sources
outputs = geotiff.Downloader.outputs

src_arg_txt = ', '.join([f'{k} = {sources[k]["desc"]}' for k in sources])
out_arg_txt = ', '.join([f'{k} = {outputs[k]["desc"]}' for k in outputs])

tee_stdout = Tee('stdout.txt', 'w', 'stdout')
tee_stderr = Tee('stderr.txt', 'w', 'stderr')

parser = argparse.ArgumentParser( description='', epilog='' )

opts = parser.add_argument_group('Region of interest')

opts.add_argument('-src', required = False, type = str,
	default = 'SRTMGL1', choices = [k for k in sources],
	help = 'Source DEM data; ' + src_arg_txt)

opts.add_argument('-lat', required = True, type = float, nargs = 2,
	help = 'Min and max latitude in degrees (south pole at -90, north poles at +90)')

opts.add_argument('-lon', required = True, type = float, nargs = 2,
	help = 'Min and max longitude in degrees (-180 to +180, positive is east')

opts = parser.add_argument_group('Data sources, formats, etc')

opts.add_argument('-out_fmt', required = False, type = str,
	default = 'GTiff', choices = [k for k in outputs],
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

r = geotiff.Downloader.get_request(args.src,
	args.lat[0], args.lon[0],
	args.lat[1], args.lon[1],
	args.out_fmt)

if r.status_code == 404:
	print()
	print(f'{r.url} : not found! Stopping here.')
	print(r)
	print()
	sys.exit(-1)


out_path = args.file + '.' + outputs[args.out_fmt]['suffix']

print()
print(f'Run at: {time.asctime()}')
print(f'Run as: {" ".join(sys.argv)}')
print()
print(f'Fetching {outputs[args.out_fmt]["desc"]} from {sources[args.src]["desc"]} ...')
print(f'{r.url} => {out_path}')
print()

stream_to_file(r, out_path)

print('Done.')
