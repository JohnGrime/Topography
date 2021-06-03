# Author: John Grime
#
# General approach: we're probably combining multiple satellite image regions
# of different resolutions. To avoid weird overlaps due to different sampling
# locations in each data set, it's useful to sample all data on the same
# regular grid. Therefore, we define a basis grid for sampling on the whole
# topographical domain and try to ensure samples occur on grid points. As the
# edges of the satellite imagery almost certainly don't sit nicely on the grid
# points, we have to wrap extremal points onto the extents of the satellite
# imagery bounds. If these "off-lattice" points are interpolated consistently,
# we should still retain contiguous adjacent topography from satellite data at
# different resolutions and arbitrary (overlapping) regions provided they draw
# topographical data from the same underlying GeoTIFF (or whatever).
#

import sys, time, argparse

from util import Tee, latlon_degs_per_m
import geotiff

#
# Set up arguments
#

parser = argparse.ArgumentParser(description='', epilog='')

opts = parser.add_argument_group('Input options')

opts.add_argument('gtiff',
	help = 'GeotTIFF input file path')

opts = parser.add_argument_group('Output options')

opts.add_argument('-lat', required = True, type = float, nargs = 2,
	help = 'Min and max latitude in degrees (south pole at -90, north poles at +90)')

opts.add_argument('-lon', required = True, type = float, nargs = 2,
	help = 'Min and max longitude in degrees (-180 to +180, positive is east')

opts.add_argument('-n_samples_x', type = int,
	help = 'Number of samples on x (longitudinal) axis; if not specified, taken from GeoTIFF')

opts.add_argument('-n_samples_y', type = int,
	help = 'Number of samples on y (latitudinal axis; if not specified, taken from GeoTIFF')

opts.add_argument('-texture', type = str,
	help = 'Texture file (triggers use of texture coords etc in output file)')

opts.add_argument('-output', type = str, default = 'output',
	help = 'Output file prefix')

opts.add_argument('-z_scale', type = float, default = 1.0,
	help = 'Scaling applied to z axis (inferred from other dims if omitted)')

opts.add_argument('-x0', type = float, default = 0.0,
	help = 'Make x coords relative to this value')

opts.add_argument('-y0', type = float, default = 0.0,
	help = 'Make y coords relative to this value')

opts.add_argument('-z0', type = float, default = 0.0,
	help = 'Make z coords relative to this value')

opts.add_argument('-reorder', type = str, default = 'xyz',
	help = 'Reorder string for axes in output')

#
# Parse arguments and print some user information
#

if len(sys.argv)<2:
	parser.parse_args([sys.argv[0], '-h'])

args = parser.parse_args()
gti = geotiff.Interpolator(args.gtiff)

print()
print(f'Run at: {time.asctime()}')
print(f'Run as: {" ".join(sys.argv)}')

min_z, max_z = gti.data.min(), gti.data.max()

print()
print(f'GeoTIFF: {args.gtiff}')
print(f'  Bounds: {gti.bnd.left},{gti.bnd.bottom} -> {gti.bnd.right},{gti.bnd.top}')
print(f'  Dims: {gti.Nx} x {gti.Ny} ; Resolution: {gti.Lx/gti.Nx} x {gti.Ly/gti.Ny}')
print(f'  Z range is apparently {min_z} to {max_z}')

print()
if (args.n_samples_x != None):
	print(f'{args.n_samples_x} samples on global domain x (longitudinal) axis')
if (args.n_samples_y != None):
	print(f'{args.n_samples_y} samples on global domain y (latitudinal) axis')

#
# No z scaling specified? Scale to smaller of x or y span
#

if args.z_scale == None:
	z_scale = min(gti.Lx,gti.Ly) / float(max_z-min_z)
	print(f'Calculated z_scale as {z_scale} from smallest existing dataset dimension ...')
else:
	z_scale = args.z_scale

print()

#
# Write material file, if needed
#

if args.texture != None:
	print('Writing material file...')
	f = open(args.output + '.mtl', 'w')
	print('newmtl Default', file=f)
	print('  Ka 1.0 1.0 1.0', file=f) # ambient color
	print('  Kd 1.0 1.0 1.0', file=f) # diffuse color
	print('  Ks 0.0 0.0 0.0', file=f) # specular color
	print('   d 1.0', file=f)  # "dissolved" == opacity
	print('  Ni 1.0', file=f)  # optical density
	print('  illum 2', file=f) # illumination model
	print(f'  map_Ka {args.texture}', file=f) # ambient texture
	print(f'  map_Kd {args.texture}', file=f) # diffuse texture
	print(f'  map_Ks {args.texture}', file=f) # specular texture
	print(f'  map_Ns {args.texture}', file=f) # specular highlight texture
	f.close()

#
# Write .obj file, including reference to material file if needed
#

print('Writing .obj file...')
f = open(args.output + '.obj', 'w')

if args.texture != None:
	print(f'mtllib {args.output + ".mtl"}', file=f)
	print(f'usemtl Default', file=f)

#
# Generate .obj file
#

print('  vertex positions...')

x0, y0, z0 = args.x0, args.y0, args.z0 # to set local origin, if specified

# Global domain information (i.e., from entire GeoTiff) in CAPITAL LATTERS
NX, NY = gti.Nx, gti.Ny
if args.n_samples_x != None: NX = args.n_samples_x
if args.n_samples_y != None: NY = args.n_samples_y

LON0, LON1 = gti.bnd.left, gti.bnd.right
LAT0, LAT1 = gti.bnd.bottom, gti.bnd.top
LX, LY = LON1-LON0, LAT1-LAT0

# Local domain information (i.e., from local satellite image) in lower case letters

lat0, lat1 = args.lat[0], args.lat[1]
lon0, lon1 = args.lon[0], args.lon[1]
lx, ly = lon1-lon0, lat1-lat0

# Start and end columns into discretized GLOBAL domain that cover the
# local region. Int truncation ensures we encompass the start point,
# +1 to the end column to ensure we encompass end points. 

col0 = int( NX * (lon0-LON0)/LX )
col1 = int( NX * (lon1-LON0)/LX ) + 1

row0 = int( NY * (lat0-LAT0)/LY )
row1 = int( NY * (lat1-LAT0)/LY ) + 1

# Estimate conversion from degs to metres using central latitude. This is not
# formally correct, as the longitudinal (i.e., x) scaling changes with
# latitude (y)!
dLat_degs_per_m, dLon_degs_per_m = latlon_degs_per_m((lat0+lat1)/2)
dLat_m_per_deg = 1.0/dLat_degs_per_m
dLon_m_per_deg = 1.0/dLon_degs_per_m

#
# Determine axis mapping
#

axis_order, axis_id = [0,1,2], {'x': 0, 'y': 1, 'z': 2}

if len(args.reorder) != 3:
		print(f'Bad axis remap string "{args.reorder}"')
		sys.exit(-1)

for i,axis in enumerate(args.reorder):
	if axis in axis_id: axis_order[i] = axis_id[axis]
	else:
		print(f'Unknown axis identifier "{axis}"')
		sys.exit(-1)

#
# Generate vertex positions
#
# Note; we build the rows of vertices for the geometry from the "bottom" to
# the "top" of the domain, so our u,v texture coords are the same (i.e., v in
# u,v is relative to the bottom of the image)
#

x_idx, y_idx, z_idx = axis_order

clamp = lambda x, x0, x1: min(max(x0,x),x1)

for row in range(row0,row1):
	y = clamp(LAT0 + row * LY/NY, lat0, lat1) # clamp global y pos onto local bounds

	for col in range(col0,col1):
		x = clamp(LON0 + col * LX/NX, lon0, lon1) # clamp global x pos onto local bounds

		z = gti.interpolate(x, lat1-(y-lat0))

		r = ( (x-x0)*dLon_m_per_deg, (y-y0)*dLat_m_per_deg, float(z-z0)*z_scale )
		print(f'v {r[x_idx]:.6f} {r[y_idx]:.6f} {r[z_idx]:.6f}', file=f)

		if (args.texture != None):
			# local position => normalized u,v coords into texture
			u, v = (x-lon0)/lx, (y-lat0)/ly # y-lat0 as v=0 is texture bottom
			print(f'vt {u:.6f} {v:.6f}', file=f)

#
# Triangular faces, including texture coords if needed
#

print('  faces...')
for row in range((row1-row0)-1):
	for col in range((col1-col0)-1):
		a = (row*(col1-col0)) + col
		b = a+1
		c = ((row+1)*(col1-col0)) + col
		d = c+1

		i1, j1, k1 = a+1, b+1, c+1 # triangle 1
		i2, j2, k2 = d+1, c+1, b+1 # triangle 2

		if args.texture != None:
			print(f'f {i1}/{i1} {j1}/{j1} {k1}/{k1}', file=f)
			print(f'f {i2}/{i2} {j2}/{j2} {k2}/{k2}', file=f)
		else:
			print(f'f {i1} {j1} {k1}', file=f)
			print(f'f {i2} {j2} {k2}', file=f)

print('Done.')
