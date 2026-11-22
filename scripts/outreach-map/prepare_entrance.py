"""Prepare the measured campus shells and rectified entrance details for Blender."""

import json
from urllib.parse import urlencode

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

FOOTPRINTS = (
    'https://opendata.vancouver.ca/api/explore/v2.1/catalog/datasets/building-footprints-2009/exports/json'
)
PHOTO = (
    'https://upload.wikimedia.org/wikipedia/commons/8/85/Killarney_Secondary_School_southwest_entrance.jpg'
)


def prepare_entrance(folder, fetch):
    query = urlencode(
        {
            'where': "within_distance(geo_point_2d,geom'POINT(-123.0442 49.2256)',350m)",
            'select': 'id,bldgid,hgt_agl,avght_m,geom',
        }
    )
    footprints = fetch(FOOTPRINTS + '?' + query, folder / 'campus.json')
    if not any(row['id'] == 90483 for row in json.loads(footprints.read_text())):
        raise ValueError('Campus extract is missing the entrance wing')
    # Arnold C's photograph, used with attribution. Rectify each visible surface
    # independently so the windows, door recess and vent move in perspective.
    with Image.open(fetch(PHOTO, folder / 'southwest.jpg')) as photo:
        # Mask the skyline and pole out of the wall projection. The flag and pole
        # have their own geometry, so they can silhouette against the sky during takeoff.
        def pixels(points):
            return [(round(x * photo.width / 630), round(y * photo.height / 840)) for x, y in points]

        mask = Image.new('L', photo.size)
        draw = ImageDraw.Draw(mask)
        draw.polygon(
            pixels(
                [
                    (0, 204),
                    (43, 175),
                    (242, 254),
                    (243, 247),
                    (351, 212),
                    (429, 251),
                    (429, 324),
                    (475, 343),
                    (630, 295),
                    (630, 840),
                    (0, 840),
                ]
            ),
            fill=255,
        )
        draw.line(pixels([(484, 54), (504, 779)]), width=round(photo.width / 630 * 6), fill=0)
        detail = photo.convert('RGBA')
        detail.putalpha(mask.filter(ImageFilter.GaussianBlur(2)))
        detail.save(folder / 'entrance-projection.png')
        panels = {
            'corner-glass': ((480, 720), [(35, 244), (164, 280), (147, 528), (9, 518)]),
            'teal-vent': ((320, 520), [(351, 212), (429, 249), (424, 397), (340, 369)]),
            'entry-doors': ((560, 350), [(301, 624), (479, 608), (482, 706), (297, 721)]),
        }
        for name, (size, corners) in panels.items():
            a, b = [], []
            for (x, y), (u, v) in zip([(0, 0), (size[0], 0), size, (0, size[1])], corners):
                u, v = u * photo.width / 630, v * photo.height / 840
                a.extend([[x, y, 1, 0, 0, 0, -x * u, -y * u], [0, 0, 0, x, y, 1, -x * v, -y * v]])
                b.extend([u, v])
            coeffs = np.linalg.solve(a, b)
            panel = photo.transform(size, Image.Transform.PERSPECTIVE, coeffs, Image.Resampling.BICUBIC)
            panel.save(folder / (name + '.jpg'), quality=96)
