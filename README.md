# Topography Tools

A set of simple Python scripts to download and combine digital elevation data and satellite imagery to generate 3D topographical models.

The package consists of three scripts:

- `fetch_topography.py` : download digital elevation data for a given latitude and longitude bounding box
- `fetch_tiles.py` : download (and combine) satellite images from the [U.S. Geological Survey](https://www.usgs.gov/) as a 3D model texture
- `geotiff_to_3d.py` : combine digital elevation and texture data to create a 3D model.


## `fetch_topography.py`

Downloads digital elevation data from the [OpenTopography](https://opentopography.org/) servers.

### Prerequisites:

- Python 3
- [`requests`](https://pypi.org/project/requests/2.7.0/) module (via e.g., `pip3 install requests`)


### Usage

```
$ python3 fetch_topography.py
usage: fetch_topography.py [-h] -lat LAT LAT -lon LON LON [-dem {SRTMGL1,SRTMGL1_E,SRTMGL3,AW3D30,AW3D30_E}] [-fmt {AAIGrid,GTiff}] [-file FILE]

optional arguments:
  -h, --help            show this help message and exit

Region of interest:
  -lat LAT LAT          Min and max latitude in degrees (south pole at -90, north poles at +90)
  -lon LON LON          Min and max longitude in degrees (-180 to +180, positive is east

Data sources, formats, etc:
  -dem {SRTMGL1,SRTMGL1_E,SRTMGL3,AW3D30,AW3D30_E}
                        Source DEM data; SRTMGL1 = Shuttle Radar Topography Mission GL1 (Global 30m), SRTMGL1_E = Shuttle Radar Topography Mission GL1 ellipsoidal (Global 30m), SRTMGL3 = Shuttle Radar Topography Mission GL3 (Global 90m), AW3D30 = ALOS World 3D 30m,
                        AW3D30_E = ALOS World 3D ellipsoidal (30m)
  -fmt {AAIGrid,GTiff}  Output file format; AAIGrid = Arc ASCII Grid, GTiff = GeoTiff
  -file FILE            Output file path prefix
```

### Example

## `fetch_tiles.py`

Downloads (and caches) satellite map tile imagery from the [U.S. Geological Survey](https://www.usgs.gov). The local cache directory is checked for existing data before each tile is downloaded.

### Prerequisites

- Python 3
- [`requests`](https://pypi.org/project/requests/2.7.0/) module (via e.g., `pip3 install requests`)

### Usage

```
$ python3 fetch_tiles.py
usage: fetch_tiles.py [-h] -lat LAT LAT -lon LON LON -zoom ZOOM [-cache CACHE] [-combine]

optional arguments:
  -h, --help    show this help message and exit

Region of interest:
  -lat LAT LAT  Min and max latitude in degrees (south pole at -90, north poles at +90)
  -lon LON LON  Min and max longitude in degrees (-180 to +180, positive is east
  -zoom ZOOM    Zoom level (0 to 23, larger values include more detail)

Data caching:
  -cache CACHE  Directory name for cached tile data

Tile combination:
  -combine      If specified, combine tiled data into single image
```

### Example


## `geotiff_to_3d.py`

Combine digital elevation data (in the form of a [GeoTIFF](https://earthdata.nasa.gov/esdis/eso/standards-and-references/geotiff) file) with an optional texture to create a 3D object in the common [Wavefront .obj](https://en.wikipedia.org/wiki/Wavefront_.obj_file) format.

### Prerequisites

- Python 3
- [`rasterio`](https://pypi.org/project/rasterio/0.13.2/) module (via e.g., `pip3 install rasterio`)

### Usage

```
$ python3 geotiff_to_3d.py
usage: geotiff_to_3d.py [-h] [-output OUTPUT] [-z_scale Z_SCALE] [-texture TEXTURE] [-filter FILTER FILTER FILTER FILTER FILTER FILTER FILTER FILTER] [-resample RESAMPLE] [-method {nearest,bilinear,cubic}] gtiff

optional arguments:
  -h, --help            show this help message and exit

Input options:
  gtiff                 GeotTiff input file path

Output options:
  -output OUTPUT        Output file prefix
  -z_scale Z_SCALE      Scaling applied to z axis (inferred from other dims if omitted)
  -texture TEXTURE      Texture file (triggers use of texture coords etc in output file)
  -filter FILTER FILTER FILTER FILTER FILTER FILTER FILTER FILTER
                        Four lat & lon pairs (ordered CLOCKWisE) defining a quadrilateral filtering area
  -resample RESAMPLE    Resample data scaling factor (see also "method")
  -method {nearest,bilinear,cubic}
                        Resampling method
```

### Example
