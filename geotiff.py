# Author: John Grime.

import requests

class Downloader:

	base_url = 'https://portal.opentopography.org/API/globaldem'

	sources = {
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

	outputs = {
		'AAIGrid': {
			'desc': 'Arc ASCII Grid',
			'suffix': 'asc',
		},

		'GTiff': {
			'desc': 'GeoTiff',
			'suffix': 'tiff',
		},
	}

	@staticmethod
	def get_request(src: str, lat0: float, lon0: float, lat1: float, lon1: float, out_fmt: str):
		return requests.get(Downloader.base_url, stream = True, params = {
			'demtype': src,
			'west': lon0,
			'east': lon1,
			'south': lat0,
			'north': lat1,
			'outputFormat': out_fmt,
			})


class Interpolator:

	def __init__(self, fpath: str, scale: float = None, how: str = 'cubic'):
		# Only require these modules if we actually need them; the geotiff downloader
		# class does not, but the interpolator does.
		import rasterio
		import numpy as np
		from scipy import ndimage

		with rasterio.open(fpath) as geotiff:
			# Store some info from the *original* file metadata for future
			# examination, if needed.
			self.res_ = geotiff.res
			self.Nx_, self.Ny_ = geotiff.width, geotiff.height # store ORIGINAL file dims

			print(f'File contains {geotiff.count} band(s), using first ...')
			self.bnd = geotiff.bounds

			if scale != None:
				algo = Resampling.nearest
				if how == 'bilinear':
					algo = Resampling.bilinear
				elif how == 'cubic':
					algo = Resampling.cubic
				else:
					print('Unknown resampling algorithm "{how}"; using cubic')
					algo = Resampling.cubic

				out_shape = (geotiff.count, int(Ny*scale), int(Nx*scale))
				data = geotiff.read(out_shape=out_shape, resampling=algo)
				self.data = data[0] # only use first band

				# Note: actual scaling performed may not exactly match that
				# requested due to integer row/width values.

			else:
				self.data = geotiff.read(1) # only use first band

		self.Ny, self.Nx = self.data.shape
		self.Lx = self.bnd.right - self.bnd.left
		self.Ly = self.bnd.top - self.bnd.bottom

	# scipy.interpolate is incredibly slow, so use ndimage.map_coordinates
	# https://stackoverflow.com/questions/33259896/python-interpolation-2d-array-for-huge-arrays/33261924#33261924
	def interpolate(self, x: float, y: float, normalized_coords: bool = False, order: int = 1):
		# Only require these modules if we actually need them; the geotiff downloader
		# class does not, but the interpolator does.
		import numpy as np
		from scipy import ndimage

		if (normalized_coords == True):
			col = (self.Nx-1) * x
			row = (self.Ny-1) * y
		else:
			col = (self.Nx-1) * (x-self.bnd.left)/self.Lx
			row = (self.Ny-1) * (y-self.bnd.bottom)/self.Ly
		return ndimage.map_coordinates(self.data, [[row],[col]], output=np.float32, order=order)


