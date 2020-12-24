# Author: John Grime

import sys, time, argparse

from util import Tee
import geotiff

parser = argparse.ArgumentParser(description='', epilog='')

opts = parser.add_argument_group('Input options')

opts.add_argument('gtiff',
	help = 'GeotTIFF input file path')

opts = parser.add_argument_group('Output options')

opts.add_argument('-output', type = str, default = 'output',
	help = 'Output file prefix')

opts.add_argument('-z_scale', type = float,
	help = 'Scaling applied to z axis (inferred from other dims if omitted)')

opts.add_argument('-texture', type = str,
	help = 'Texture file (triggers use of texture coords etc in output file)')

opts.add_argument('-lat', required = True, type = float, nargs = 2,
	help = 'Min and max latitude in degrees (south pole at -90, north poles at +90)')

opts.add_argument('-lon', required = True, type = float, nargs = 2,
	help = 'Min and max longitude in degrees (-180 to +180, positive is east')

opts.add_argument('-x0', type = float, required = False, default = 0.0,
	help = 'Make x coords relative to this value')

opts.add_argument('-y0', type = float, required = False, default = 0.0,
	help = 'Make y coords relative to this value')

opts.add_argument('-z0', type = float, required = False, default = 0.0,
	help = 'Make z coords relative to this value')

if len(sys.argv)<2:
	parser.parse_args([sys.argv[0], '-h'])

args = parser.parse_args()
gti = geotiff.Interpolator(args.gtiff)

print()
print(f'Run at: {time.asctime()}')
print(f'Run as: {" ".join(sys.argv)}')

Rx, Ry = gti.Lx/gti.Nx, gti.Ly/gti.Ny
min_z, max_z = gti.data.min(), gti.data.max()
Lz = float(max_z-min_z)

print()
print(f'GeoTIFF: {args.gtiff}')
print(f'  Bounds: {gti.bnd.left},{gti.bnd.bottom} -> {gti.bnd.right},{gti.bnd.top}')
print(f'  Dims: {gti.Nx} x {gti.Ny} ; Resolution: {Rx} x {Ry}')
print(f'  Z range is apparently {min_z} to {max_z}')

# No z scaling specified? Scale to smaller of x or y span
if args.z_scale == None:
	z_scale = min(gti.Lx,gti.Ly) / Lz
	print(f'Calculated z_scale as {z_scale} from smallest existing dataset dimension ...')
else:
	z_scale = args.z_scale

# Write material file, if needed
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

# Write .obj file
print('Writing .obj file...')
f = open(args.output + '.obj', 'w')

# Include material in obj file, if needed
if args.texture != None:
	print(f'mtllib {args.output + ".mtl"}', file=f)
	print(f'usemtl Default', file=f)

# Vertex positions
print('  vertex positions...')
x0, y0, z0 = args.x0, args.y0, args.z0

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

# CAPITAL LATTERS : global domain (i.e., whole topographical GeoTiff)

NX, NY = 1000, 1000 # discrete sampling points on entire domain

LON0, LON1 = gti.bnd.left, gti.bnd.right
LAT0, LAT1 = gti.bnd.bottom, gti.bnd.top
LX, LY = LON1-LON0, LAT1-LAT0

# Lower case letters : local domain (i.e., inside specified bounds)

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

# Note; we build the rows of vertices for the geometry from the "bottom" to
# the "top" of the domain, so our u,v texture coords are the same (v in u,v
# is relative to the bottom of the image)
for row in range(row0,row1):
	y = LAT0 + row * LY/NY     # "global" y pos
	y = min(max(lat0,y), lat1) # clamp onto "local" y bounds

	for col in range(col0,col1):
		x = LON0 + col * LX/NX     # "global" x pos
		x = min(max(lon0,x), lon1) # clamp onto "local" x bounds

		z = gti.interpolate(x, lat1-(y-lat0)) * z_scale
		x_, y_, z_ = x-x0, y-y0, float(z-z0)
		print(f'v {x_:.6f} {y_:.6f} {z_:.6f}', file=f)

		if (args.texture != None):
			# convert local position into normalized u,v coords
			x_, y_ = (x-lon0)/lx, (y-lat0)/ly
			u, y = x_ + 0.0, y_ + 0.0 # Note: v=0 is last texture row, not first
			print(f'vt {u:.6f} {v:.6f}', file=f)

# Triangular faces, including texture coords if needed
print('  faces...')
for row in range((row1-row0)-1):
	for col in range((col1-col0)-1):
		a = (row*(col1-col0)) + col
		b = a+1
		c = ((row+1)*(col1-col0)) + col
		d = c+1

		i1, j1, k1 = c+1, b+1, a+1 # triangle 1
		i2, j2, k2 = b+1, c+1, d+1 # triangle 2

		i1, j1, k1 = a+1, b+1, c+1 # triangle 1
		i2, j2, k2 = d+1, c+1, b+1 # triangle 2

		if args.texture != None:
			print(f'f {i1}/{i1} {j1}/{j1} {k1}/{k1}', file=f)
			print(f'f {i2}/{i2} {j2}/{j2} {k2}/{k2}', file=f)
		else:
			print(f'f {i1} {j1} {k1}', file=f)
			print(f'f {i2} {j2} {k2}', file=f)

print('Done.')
