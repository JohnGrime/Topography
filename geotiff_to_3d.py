# Author: John Grime

import sys, time, argparse

from util import Tee
import geotiff

#
# Check if point M is inside parallelogram defined by points A,B,C,D.
# https://stackoverflow.com/questions/2752725/finding-whether-a-point-lies-inside-a-rectangle-or-not
#
# Note: Points must be defined in CLOCKWISE order!
#
def inside_quadrilateral(A, B, C, D, m):
	v = lambda p1,p2 : [p2[0]-p1[0], -(p2[1]-p1[1])]
	f = lambda v1,v2 : (v1[1]*v2[0] + v1[0]*v2[1])

	AB, AD, BC, CD = v(A,B), v(A,D), v(B,C), v(C,D)
	C1, C2, C3, C4 = -f(AB,A), -f(AD,A), -f(BC,B), -f(CD,C)
	D1, D2, D3, D4 =  f(AB,m) + C1,  f(AD,m) + C2,  f(BC,m) + C3,  f(CD,m) + C4

	return (0 >= D1) and (0 >= D4) and (0 <= D2) and (0 >= D3)

#
# Handle command line arguments
#

tee_stdout = Tee('stdout.txt', 'w', 'stdout')
tee_stderr = Tee('stderr.txt', 'w', 'stderr')

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

opts.add_argument('-filter', type = float, nargs=8, default=None,
	help = 'Four lat & lon pairs (ordered CLOCKWISE) defining a quadrilateral filtering area')

opts.add_argument('-resample', type = float, default = None,
	help = 'Resample data accoring to this proportion (e.g. 0.5 = use half resolution)')

opts.add_argument('-algorithm', type = str, choices = ['cubic', 'bilinear', 'nearest'], default = 'cubic',
	help = 'Resampling algorithm')

opts.add_argument('-x0', type = float, required = False, default = 0.0,
	help = 'Make x coords relative to this value')

opts.add_argument('-y0', type = float, required = False, default = 0.0,
	help = 'Make y coords relative to this value')

opts.add_argument('-z0', type = float, required = False, default = 0.0,
	help = 'Make z coords relative to this value')

if len(sys.argv)<2:
	parser.parse_args([sys.argv[0], '-h'])

args = parser.parse_args()

if args.resample != None:
	gti = geotiff.Interpolator(args.gtiff, scale=args.resample, algorithm=args.algorithm)
else:
	gti = geotiff.Interpolator(args.gtiff)

Rx, Ry = gti.Lx/gti.Nx, gti.Ly/gti.Ny
min_z, max_z = gti.data.min(), gti.data.max()
Lz = float(max_z-min_z)

print()
print(f'Run at: {time.asctime()}')
print(f'Run as: {" ".join(sys.argv)}')
print()
print(f'Bounds: {gti.bnd.left},{gti.bnd.bottom} -> {gti.bnd.right},{gti.bnd.top}')
print(f'Dims: {gti.Nx} x {gti.Ny} ; Resolution: {Rx} x {Ry}')
print(f'Z range is apparently {min_z} to {max_z}')

if args.resample != None:
	print(f'Resampled to {args.resample} ({args.algorithm}); {gti.Nx_}x{gti.Ny_} => {gti.Nx}x{gti.Ny}')

# No z scaling specified? Scale to smaller of x or y span
if args.z_scale == None:
	z_scale = min(gti.Lx,gti.Ly) / Lz
	print(f'Calculated z_scale as {z_scale} from smallest existing dataset dimension ...')
else:
	z_scale = args.z_scale

print()

#
# Filter if needed, save as Wavefront .obj
# https://en.wikipedia.org/wiki/Wavefront_.obj_file
#

top, left = gti.bnd.top, gti.bnd.left

filtered = None

# Filter points against quadrilateral
if args.filter != None:

	# Four points define filtering quadrilateral; reverse lat,lon to get x,y
	qa = [ args.filter[1], args.filter[0] ]
	qb = [ args.filter[3], args.filter[2] ]
	qc = [ args.filter[5], args.filter[4] ]
	qd = [ args.filter[7], args.filter[6] ]

	filtered = [] # (row,col) tuples for points that pass filtering

	for row in range(gti.Ny):
		y = top - row*Ry
		for col in range(gti.Nx):
			x = left + col*Rx
			if inside_quadrilateral(qa, qb, qc, qd, (x,y)):
				filtered.append( (row,col) )

	print(f'{len(filtered)}/{gti.Ny*gti.Nx} points passed filtering ({(100.0*len(filtered))/(gti.Ny*gti.Nx):.3} %).')

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
if filtered != None:
	for (row,col) in filtered:
		y = top - row*Ry
		x = left + col*Rx
		z = (gti.data[row][col] - min_z) * z_scale # relative to lowest z point in data
		x_, y_, z_ = x-x0, y-y0, z-z0
		print(f'v {x_:.6f} {y_:.6f} {z_:.6f}', file=f)
else:
	for row in range(gti.Ny):
		y = top - row*Ry
		for col in range(gti.Nx):
			x = left + col*Rx
			z = (gti.data[row][col] - min_z) * z_scale # relative to lowest z point in data
			x_, y_, z_ = x-x0, y-y0, z-z0
			print(f'v {x_:.6f} {y_:.6f} {z_:.6f}', file=f)

# Vertex texture coords, if needed
if args.texture != None:
	print('  vertex texture coords...')
	if filtered != None:
		for (row,col) in filtered:
			v = 1.0 - (1.0/gti.Ny * (0.5+row)) # pixel center. Note: v=0 is last texture row, not first
			u = 1.0/gti.Nx * (0.5+col)
			print(f'vt {u:.6f} {v:.6f}', file=f)
	else:
		for row in range(gti.Ny):
			v = 1.0 - (1.0/gti.Ny * (0.5+row)) # pixel center. Note: v=0 is last texture row, not first
			for col in range(gti.Nx):
				u = 1.0/gti.Nx * (0.5+col)
				print(f'vt {u:.6f} {v:.6f}', file=f)

# Triangular faces, including texture coords if needed
print('  faces...')
if filtered != None:

	# idx: map filtered indices into UNIT BASED vertex indices in obj file
	idx = {}
	for i,(row,col) in enumerate(filtered):
		idx[row*Nx + col] = i+1

	for row in range(gti.Ny-1):
		for col in range(gti.Nx-1):
			a = (row*gti.Nx) + col
			b = a+1
			c = ((row+1)*gti.Nx) + col
			d = c+1

			# Get actual indices (unit based) if passed filter, else 0
			a = idx[a] if a in idx else 0
			b = idx[b] if b in idx else 0
			c = idx[c] if c in idx else 0
			d = idx[d] if d in idx else 0

			# write triangle 1 if all points valid
			if ((a>0) and (b>0) and (c>0)):
				i, j, k = c, b, a
				if args.texture != None:
					print(f'f {i}/{i} {j}/{j} {k}/{k}', file=f)
				else:
					print(f'f {i} {j} {k}', file=f)

			# write triangle 2 if all points valid
			if ((b>0) and (c>0) and (d>0)):
				i, j, k = b, c, d
				if args.texture != None:
					print(f'f {i}/{i} {j}/{j} {k}/{k}', file=f)
				else:
					print(f'f {i} {j} {k}', file=f)
else:
	for row in range(gti.Ny-1):
		for col in range(gti.Nx-1):
			a = (row*gti.Nx) + col
			b = a+1
			c = ((row+1)*gti.Nx) + col
			d = c+1

			i1, j1, k1 = c+1, b+1, a+1 # triangle 1
			i2, j2, k2 = b+1, c+1, d+1 # triangle 2

			if args.texture != None:
				print(f'f {i1}/{i1} {j1}/{j1} {k1}/{k1}', file=f)
				print(f'f {i2}/{i2} {j2}/{j2} {k2}/{k2}', file=f)
			else:
				print(f'f {i1} {j1} {k1}', file=f)
				print(f'f {i2} {j2} {k2}', file=f)

print('Done.')
