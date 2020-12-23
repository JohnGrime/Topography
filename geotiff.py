# Author: John Grime.

import requests
import rasterio
import numpy as np
from scipy import ndimage


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


# https://stackoverflow.com/questions/33259896/python-interpolation-2d-array-for-huge-arrays/33261924#33261924

class Interpolator:

	def __init__(self, fpath: str):
		with rasterio.open(fpath) as geotiff:
			self.bnd, self.res = geotiff.bounds, geotiff.res
			self.Nx, self.Ny = geotiff.width, geotiff.height
			self.data = geotiff.read(1) # only use first band

		self.min_z, self.max_z = self.data.min(), self.data.max()
		self.Lx = self.bnd.right - self.bnd.left
		self.Ly = self.bnd.top - self.bnd.bottom

#		print(f'{self.bnd} : {self.Nx} {self.Ny}')
#		print(f'{self.res} : {self.Lx/self.Nx} {self.Ly/self.Ny}')

	# scipy.interpolate is incredibly slow, so use ndimage.map_coordinates
	def interp(self, x: float, y: float, normalized_coords: bool = False, order: int = 1, output = np.float32):
		if (normalized_coords == True):
			col = x * (self.Nx-1)
			row = y * (self.Ny-1)
		else:
			col = (x-self.bnd.left) / self.Lx
			row = (y-self.bnd.bottom) / self.Ly
		return ndimage.map_coordinates(self.data, [[row],[col]], output=output, order=order)


