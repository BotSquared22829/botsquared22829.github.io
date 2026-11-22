"""Prepare attributed geographic textures for the offline Blender render."""
import argparse
import json
import math
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image
from prepare_entrance import prepare_entrance
from rasterio.transform import from_bounds
from rasterio.warp import reproject, Resampling

CAMPUS = (-123.0441757, 49.2255942)
CITY = 'https://tiles.arcgis.com/tiles/qrcTTRTwUoS8N47o/arcgis/rest/services/Orthophotos_2022/MapServer/tile'
NASA = ('https://assets.science.nasa.gov/content/dam/science/esd/eo/images/bmng/'
        'bmng-topography-bathymetry/july/world.topo.bathy.200407.3x21600x10800.jpg')
SCENES = [('DV', '20240817'), ('DV', '20240830'), ('EV', '20240817')]
Image.MAX_IMAGE_PIXELS = 250_000_000


def fetch(url, path):
    if not path.exists():
        request = urllib.request.Request(url, headers={
            'User-Agent': 'BotSquaredWebsite/1.0 (+https://botsquared22829.github.io/)'
        })
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request, timeout=60) as response:
                    data = response.read()
                path.write_bytes(data)
                break
            except OSError:
                if attempt == 2:
                    raise
                time.sleep(1 + attempt)
    return path


def tile_lat(y, n):
    return math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))


def municipal(folder, zoom, count):
    n = 2 ** zoom
    lon, lat = CAMPUS
    left = int((lon + 180) / 360 * n) - count // 2
    top = int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n) - count // 2
    mosaic = Image.new('RGB', (256 * count, 256 * count))

    def get_tile(offset):
        x, y = offset
        filename = folder / f'city-{zoom}-{left+x}-{top+y}.jpg'
        fetch(f'{CITY}/{zoom}/{top+y}/{left+x}', filename)
        with Image.open(filename) as tile:
            return (x*256, y*256), tile.convert('RGB')

    with ThreadPoolExecutor(6) as pool:
        for pos, tile in pool.map(get_tile, [(x, y) for y in range(count) for x in range(count)]):
            mosaic.paste(tile, pos)
    # The last z15 column crosses the city's eastern imagery boundary.
    columns = count - 1 if zoom == 15 else count
    mosaic = mosaic.crop((0, 0, 256*columns, 256*count))
    name = f'city-{zoom}.jpg'
    mosaic.save(folder / name, quality=96, subsampling=0)
    return dict(file=name, bounds=[left/n*360-180, tile_lat(top+count, n),
                                   (left+columns)/n*360-180, tile_lat(top, n)], mercator=True)


def sentinel(folder):
    # Warp both UTM granules to the same geographic grid. Ignore the swath's nodata wedges.
    bounds = [-123.60, 48.94, -122.53, 49.55]
    width, height = 4096, 3500
    mosaic = np.zeros((3, height, width), dtype='uint8')
    for tile, date in SCENES:
        name = f'S2A_10U{tile}_{date}_0_L2A'
        url = f'https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/10/U/{tile}/2024/8/{name}/TCI.tif'
        with rasterio.open(fetch(url, folder / f'{name}.tif')) as src:
            for i in range(3):
                reproject(rasterio.band(src, i+1), mosaic[i], dst_transform=from_bounds(*bounds, width, height),
                          dst_crs='EPSG:4326', src_nodata=0, dst_nodata=0, init_dest_nodata=False,
                          resampling=Resampling.bilinear, num_threads=3)
    if np.any(np.all(mosaic == 0, axis=0)):
        raise ValueError('Regional image contains uncovered pixels')
    Image.fromarray(np.moveaxis(mosaic, 0, 2)).save(folder / 'sentinel.png')
    return dict(file='sentinel.png', bounds=bounds)


def prepare(folder):
    folder.mkdir(parents=True, exist_ok=True)
    prepare_entrance(folder, fetch)
    layers = []
    with Image.open(fetch(NASA, folder / 'bmng-source.jpg')) as earth:
        earth.resize((8192, 4096), Image.Resampling.LANCZOS).save(folder / 'earth.jpg', quality=94)
        west, south, east, north = -152, 37, -102, 65
        box = ((west+180)*60, (90-north)*60, (east+180)*60, (90-south)*60)
        earth.crop(box).save(folder / 'northwest.jpg', quality=97)
        layers.append(dict(file='northwest.jpg', bounds=[west, south, east, north]))
    coast_url = ('https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi?SERVICE=WMS&VERSION=1.1.1'
                 '&REQUEST=GetMap&LAYERS=MODIS_Terra_CorrectedReflectance_TrueColor&SRS=EPSG:4326'
                 '&TIME=2024-08-31&WIDTH=2400&HEIGHT=2100&BBOX=-128,46.5,-118,52.5&FORMAT=image/jpeg&STYLES=')
    fetch(coast_url, folder / 'coast-20240831.jpg')
    layers.append(dict(file='coast-20240831.jpg', bounds=[-128,46.5,-118,52.5]))
    layers.append(sentinel(folder))
    for zoom, count in [(15, 8), (17, 8), (19, 12)]:
        layers.append(municipal(folder, zoom, count))
    (folder / 'layers.json').write_text(json.dumps(layers, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    prepare(parser.parse_args().folder)
