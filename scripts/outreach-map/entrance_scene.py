"""Street-height geometry for the west wing on Killarney Street. Units are metres."""

import json
import math
import random
from array import array
from collections import defaultdict

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

# Southwest corner of City roof section 90483. Local x points east and y north.
CORNER = (-123.04538425586281, 49.22527916608267)
GROUND_KM = 0.00134  # the highest municipal orthophoto patch sits at 1.32 m
METRES_LAT = 6371000 * math.pi / 180
METRES_LON = METRES_LAT * math.cos(math.radians(CORNER[1]))


def rgb(hex_color):
    def linear(v):
        v = int(v, 16) / 255
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4

    return (*[linear(hex_color[i : i + 2]) for i in (0, 2, 4)], 1)


def build(scene, folder, origin, bounds):
    root = bpy.data.objects.new('Killarney Street | local metres', None)
    scene.collection.objects.link(root)
    root.location = origin + Vector((0, 0, GROUND_KM))
    root.scale = (0.001,) * 3
    buffers = defaultdict(lambda: ([], [], []))
    paints = {
        'cladding': 'd9d9d3',
        'concrete': 'a4a399',
        'joint': '86867d',
        'teal': '17787c',
        'frame': '23524f',
        'glass': '365b60',
        'glass-light': '658184',
        'ledge': 'e7e7de',
        'canopy': 'aaaeb0',
        'white': 'ece9de',
        'metal': 'b9bdb9',
        'bark': '655c4b',
        'leaves': '657844',
        'sun-leaves': '879657',
        'dark-leaves': '40563c',
        'shrubs': 'a6a15b',
        'wall': 'b1ada4',
        'home-wall': 'aaa395',
    }
    photos = {
        'corner-glass': 'corner-glass.jpg',
        'teal-vent': 'teal-vent.jpg',
        'entry-doors': 'entry-doors.jpg',
        'flag-photo': 'southwest.jpg',
        'roof': 'city-19.jpg',
    }

    def face(mat, pts, uv=None):
        verts, faces, values = buffers[mat]
        start = len(verts)
        verts.extend(pts)
        faces.append(tuple(range(start, start + len(pts))))
        if uv is not None:
            values.extend(uv)

    def box(mat, x, y, z, w, d, h):
        a, b, c, e = (x, y, z), (x + w, y, z), (x + w, y + d, z), (x, y + d, z)
        top = [(u, v, k + h) for u, v, k in (a, b, c, e)]
        for i, (v1, v2) in enumerate(zip([a, b, c, e], [b, c, e, a])):
            face(mat, [v1, v2, top[(i + 1) % 4], top[i]])
        face(mat, top)

    def south(mat, x1, x2, y, z1, z2):
        pts = [(x1, y, z1), (x2, y, z1), (x2, y, z2), (x1, y, z2)]
        face(mat, pts, [(0, 0), (1, 0), (1, 1), (0, 1)] if mat in photos else None)

    def rod(mat, start, end, radius, tip=None):
        a, b = Vector(start), Vector(end)
        axis = (b - a).normalized()
        side = axis.cross(Vector((0, 1, 0)) if abs(axis.y) < 0.9 else Vector((0, 0, 1))).normalized()
        up = axis.cross(side)
        rings = []
        for pt, r in [(a, radius), (b, radius if tip is None else tip)]:
            rings.append(
                [
                    tuple(pt + r * (side * math.cos(i * math.tau / 8) + up * math.sin(i * math.tau / 8)))
                    for i in range(8)
                ]
            )
        for i in range(8):
            j = (i + 1) % 8
            face(mat, [rings[0][i], rings[0][j], rings[1][j], rings[1][i]])

    west, south_bound, east, north = bounds

    def roof_uv(x, y, h):
        # The aerial camera sees the roofs slightly northwest of their base outlines.
        lon = CORNER[0] + (x - 0.13 * h) / METRES_LON
        lat = CORNER[1] + (y + 0.11 * h) / METRES_LAT
        return ((lon - west) / (east - west), (lat - south_bound) / (north - south_bound))

    for rec in json.loads((folder / 'campus.json').read_text()):
        h = rec['hgt_agl'] or 3
        pts = [
            ((lon - CORNER[0]) * METRES_LON, (lat - CORNER[1]) * METRES_LAT)
            for lon, lat in rec['geom']['geometry']['coordinates'][0][:-1]
        ]
        if not pts or any(not (0 < u < 1 and 0 < v < 1) for u, v in [roof_uv(x, y, h) for x, y in pts]):
            continue
        roof = [(x, y, h) for x, y in pts]
        face('roof', roof, [roof_uv(x, y, h) for x, y in pts])
        for (x, y), (xx, yy) in zip(pts, pts[1:] + pts[:1]):
            wall = 'wall' if rec['bldgid'] == 38248 else 'home-wall'
            if rec['id'] == 90483:
                wall = 'cladding'
            if rec['id'] == 94548 and max(x, xx) < 14 and min(y, yy) < -5:
                wall = 'white'
                for height in (1.2, 3.2, 5.2, 7.2, 9.2, 11.2):
                    face(
                        'joint',
                        [
                            (x - 0.02, y, height),
                            (xx - 0.02, yy, height),
                            (xx - 0.02, yy, height + 0.027),
                            (x - 0.02, y, height + 0.027),
                        ],
                    )
            if rec['id'] == 91351:
                wall = 'teal'
            face(wall, [(x, y, 0), (xx, yy, 0), (xx, yy, h), (x, y, h)])
            # The school's other classroom blocks have rows of dark windows.
            length = math.hypot(xx - x, yy - y)
            if rec['bldgid'] == 38248 and rec['id'] not in (90483, 91351, 91352) and length > 7:
                dx, dy = (xx - x) / length, (yy - y) / length
                for floor in range(int(h / 3.5)):
                    for i in range(int(length / 3.4)):
                        a, b = 1 + i * 3.4, 3.25 + i * 3.4
                        q = (x + dx * a + 0.05 * dy, y + dy * a - 0.05 * dx)
                        r = (x + dx * b + 0.05 * dy, y + dy * b - 0.05 * dx)
                        z = 1 + 3.4 * floor
                        face('glass', [(*q, z), (*r, z), (*r, z + 1.6), (*q, z + 1.6)])

    # Projecting corner glass, west classroom windows and the recessed entry.
    # The roof section heights and placement come directly from the City extract.
    box('concrete', -0.14, -0.14, 0, 8, 0.19, 3.65)
    south('corner-glass', -0.12, 4.8, -0.21, 4.05, 12.12)
    box('ledge', -0.42, -0.53, 12.24, 8.3, 0.7, 0.2)
    box('concrete', 7.6, 0.43, 0, 15, 0.45, 13.45)
    for z in (3.7, 6.95, 10.1, 13.33):
        south('joint', 7.62, 22.5, 0.413, z, z + 0.055)
    for x in (8, 11.2, 14.45, 17.7, 20.95):
        box('joint', x, 0.402, 0, 0.045, 0.035, 13.33)
    # The tall teal vent projects down across the concrete facade.
    box('teal', 10.35, 0.19, 9.6, 4.69, 0.8, 6.51)
    south('teal-vent', 10.35, 15.04, 0.177, 9.6, 16.11)
    south('entry-doors', 8.0, 16.75, 0.372, 0.05, 4.02)
    box('canopy', 7.7, -5.69, 4.30, 11, 6.15, 0.32)
    box('metal', 7.69, -5.76, 4.60, 11.04, 0.13, 0.15)
    # The municipal connector outline includes its open entry canopy.
    # Put the visible doors along the recessed west wall below its roof.
    west_entry = [(7.66, -5.65, 0.05), (7.66, 0.15, 0.05), (7.66, 0.15, 4.26), (7.66, -5.65, 4.26)]
    face('entry-doors', west_entry, [(1, 0), (0, 0), (0, 1), (1, 1)])
    for floor, z in enumerate((0.95, 5.08, 9.08)):
        for i in range(9):
            y = 0.10 + 4.55 * i
            box('frame', -0.28, y, z, 0.32, 3.46, 2.07)
            for pane in range(3):
                box(
                    'glass-light' if (i + floor + pane) % 5 == 0 else 'glass',
                    -0.303,
                    y + 0.075 + 1.13 * pane,
                    z + 0.075,
                    0.027,
                    1.07,
                    1.9,
                )
            box('frame', -0.321, y, z + 1.38, 0.035, 3.46, 0.07)
            if floor:
                box('ledge', -0.57, y - 0.06, z + 2.03, 0.60, 3.60, 0.14)
    box('teal', -0.34, -0.17, 4.04, 0.4, 0.25, 8.02)
    for z in (3.7, 7.7, 13.27):
        box('joint', -0.13, 0.05, z, 0.16, 42, 0.085)
    for i in range(80):
        box('ledge', -0.06, 0.36 + i * 0.53, 12.37, 0.08, 0.045, 0.8)

    rng = random.Random(22829)

    def foliage(center, radius, count, leaf_size, materials):
        cx, cy, cz = center
        for _ in range(count):
            angle = rng.random() * math.tau
            t = rng.uniform(-1, 1)
            rad = radius * rng.random() ** (1 / 3)
            planar = rad * math.sqrt(1 - t * t)
            x, y, z = cx + planar * math.cos(angle), cy + planar * math.sin(angle), cz + rad * t * 0.76
            a = rng.random() * math.tau
            dx, dy = math.cos(a) * leaf_size, math.sin(a) * leaf_size
            face(
                rng.choice(materials),
                [
                    (x - dx, y - dy, z),
                    (x - dy * 0.45, y + dx * 0.45, z + 0.04),
                    (x + dx, y + dy, z + rng.uniform(-0.08, 0.08)),
                    (x + dy * 0.47, y - dx * 0.47, z - 0.03),
                ],
            )

    for x, y, height in [
        (-3, 1.9, 3.9),
        (-3.5, 11, 4.6),
        (-4, 20, 5),
        (-4, 31, 4.8),
        (-4.2, 40, 5.6),
        (-7, -10, 4),
        (-18, 55, 7),
        (23, -31, 6),
        (36, -29, 6.5),
    ]:
        rod('bark', (x, y, 0.05), (x + 0.1, y, height), height * 0.014, 0.024)
        for i in range(19):
            a = i * 2.4
            r = rng.uniform(0.55, 1.35) * height / 4
            z = height * (0.44 + 0.50 * i / 19)
            end = (x + r * math.cos(a), y + r * math.sin(a), z + 0.45)
            rod('bark', (x, y, z - 0.52), end, 0.036, 0.012)
            foliage(end, height * 0.14, 100, 0.115, ['leaves', 'sun-leaves', 'dark-leaves'])
    for i in range(32):
        x = 4.6 + rng.uniform(-2, 2.0)
        y = -6.1 + rng.uniform(-1.1, 1.1)
        foliage((x, y, 0.46), 0.57, 90, 0.095, ['shrubs', 'leaves', 'sun-leaves'])
    # Use the photographed flag's silhouette, registered to the pole foot.
    eye = PHOTO_EYE * 1000
    forward, right, up = photo_axes()

    def ray(u, v):
        return forward + right * ((u - 315) / PHOTO_FOCAL) + up * ((420 - v) / PHOTO_FOCAL)

    toward_base = ray(504, 779)
    base = eye - toward_base * (eye.z / toward_base.z)
    axis = Vector((forward.x, forward.y, 0)).normalized()

    def flag_at(u, v):
        direction = ray(u, v)
        return eye + direction * ((base - eye).dot(axis) / direction.dot(axis))

    rod('metal', base, flag_at(484, 54), 0.049, 0.035)
    outline = [
        (479, 80),
        (478, 95),
        (482, 136),
        (454, 146),
        (436, 144),
        (411, 175),
        (385, 198),
        (377, 187),
        (402, 162),
        (409, 149),
        (421, 131),
        (439, 113),
    ]
    face(
        'flag-photo',
        [tuple(flag_at(u, v)) for u, v in outline],
        [(u / 630, 1 - v / 840) for u, v in outline],
    )

    for name, (verts, faces, uvs) in buffers.items():
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(verts, [], faces)
        mesh.update()
        obj = bpy.data.objects.new('Campus | ' + name, mesh)
        scene.collection.objects.link(obj)
        obj.parent = root
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        shader = nodes.get('Principled BSDF')
        shader.inputs['Roughness'].default_value = 0.78
        if name in photos:
            layer = mesh.uv_layers.new(name='Surface coordinates')
            for loop in mesh.loops:
                layer.data[loop.index].uv = uvs[loop.vertex_index]
            tex = nodes.new('ShaderNodeTexImage')
            tex.image = bpy.data.images.load(str(folder / photos[name]), check_existing=True)
            if name in ('roof', 'flag-photo'):
                shader = nodes.new('ShaderNodeEmission')
                mat.node_tree.links.new(shader.outputs[0], nodes.get('Material Output').inputs['Surface'])
            mat.node_tree.links.new(tex.outputs['Color'], shader.inputs[0])
        else:
            shader.inputs['Base Color'].default_value = rgb(paints[name])
        mesh.materials.append(mat)
    return root


# Approximate the street photograph's perspective from the municipal wing corner,
# roof and vent. The camera position is estimated, not survey metadata.
PHOTO_EYE = Vector((-0.014, -0.02427, 0.00172))
PHOTO_YAW = math.radians(44.02)
PHOTO_PITCH = math.radians(11.12)
PHOTO_FOCAL = 1113.02  # pixels in the 630 x 840 reference coordinate system


def photo_axes():
    yaw, pitch = PHOTO_YAW, PHOTO_PITCH
    forward = Vector((math.sin(yaw) * math.cos(pitch), math.cos(yaw) * math.cos(pitch), math.sin(pitch)))
    right = Vector((math.cos(yaw), -math.sin(yaw), 0))
    return forward, right, right.cross(forward)


def reference_depth(campus, forward, right):
    """Depth from the reference eye, to keep the facade off roofs revealed later."""
    vertices, faces = [], []
    for obj in campus.children:
        if obj.data.materials[0].name not in ('roof', 'wall', 'cladding', 'white', 'concrete', 'teal'):
            continue
        first = len(vertices)
        vertices.extend(v.co.copy() for v in obj.data.vertices)
        faces.extend(tuple(first + i for i in face.vertices) for face in obj.data.polygons)
    tree = BVHTree.FromPolygons(vertices, faces)
    eye = PHOTO_EYE * 1000
    up = right.cross(forward)
    width, height = 315, 420
    pixels = array('f')
    for y in range(height):
        for x in range(width):
            ray = (
                forward
                + right * ((x + 0.5) / width - 0.5) * (630 / PHOTO_FOCAL)
                + up * ((y + 0.5) / height - 0.5) * (840 / PHOTO_FOCAL)
            ).normalized()
            point, _, _, _ = tree.ray_cast(eye, ray, 900)
            floor = -eye.z / ray.z if ray.z < -0.001 else 900
            depth = min(floor, (point - eye).length if point is not None else 900) * ray.dot(forward)
            pixels.extend((depth / 1000, 0, 0, 1))
    image = bpy.data.images.new(
        'Entrance reference depth in km', width, height, float_buffer=True, is_data=True
    )
    image.pixels.foreach_set(pixels)
    image.update()
    return image


def project_entrance(campus, folder):
    """Project the original photograph onto the facade and foreground for the lift."""
    eye = campus.location + PHOTO_EYE
    group = bpy.data.node_groups.new('West entrance | fixed photo projection', 'ShaderNodeTree')
    for name, io, kind in [
        ('Ray', 'INPUT', 'NodeSocketVector'),
        ('Color', 'OUTPUT', 'NodeSocketColor'),
        ('Weight', 'OUTPUT', 'NodeSocketFloat'),
    ]:
        group.interface.new_socket(name=name, in_out=io, socket_type=kind)
    nodes = group.nodes
    link = group.links.new
    ray = nodes.new('NodeGroupInput').outputs['Ray']
    out = nodes.new('NodeGroupOutput')

    def math_node(op, a, b):
        n = nodes.new('ShaderNodeMath')
        n.operation = op
        for s, v in zip(n.inputs, (a, b)):
            if isinstance(v, (int, float)):
                s.default_value = v
            else:
                link(v, s)
        return n.outputs[0]

    def dot(axis):
        n = nodes.new('ShaderNodeVectorMath')
        n.operation = 'DOT_PRODUCT'
        link(ray, n.inputs[0])
        n.inputs[1].default_value = axis
        return n.outputs['Value']

    forward, right, up = photo_axes()
    depth = dot(forward)
    safe_depth = math_node('MAXIMUM', depth, 0.00001)

    def screen_coordinate(axis, size):
        ratio = math_node('DIVIDE', dot(axis), safe_depth)
        return math_node('ADD', 0.5, math_node('MULTIPLY', PHOTO_FOCAL / size, ratio))

    u, v = screen_coordinate(right, 630), screen_coordinate(up, 840)
    xy = nodes.new('ShaderNodeCombineXYZ')
    link(math_node('MINIMUM', 1, math_node('MAXIMUM', 0, u)), xy.inputs['X'])
    link(math_node('MINIMUM', 1, math_node('MAXIMUM', 0, v)), xy.inputs['Y'])
    tex = nodes.new('ShaderNodeTexImage')
    tex.image = bpy.data.images.load(str(folder / 'entrance-projection.png'), check_existing=True)
    tex.extension = 'EXTEND'
    link(xy.outputs[0], tex.inputs['Vector'])
    link(tex.outputs['Color'], out.inputs['Color'])
    margin = math_node(
        'MINIMUM',
        math_node('MINIMUM', u, math_node('SUBTRACT', 1, u)),
        math_node('MINIMUM', v, math_node('SUBTRACT', 1, v)),
    )
    edge = math_node('MAXIMUM', 0, math_node('MINIMUM', 1, math_node('MULTIPLY', margin, 9)))
    strength = nodes.new('ShaderNodeValue').outputs[0]
    shadow = nodes.new('ShaderNodeTexImage')
    shadow.image = reference_depth(campus, forward, right)
    shadow.interpolation = 'Closest'
    link(xy.outputs[0], shadow.inputs['Vector'])
    depth_channels = nodes.new('ShaderNodeSeparateColor')
    link(shadow.outputs['Color'], depth_channels.inputs[0])
    in_front = math_node('LESS_THAN', depth, math_node('ADD', depth_channels.outputs[0], 0.0012))
    inside_photo = math_node('MULTIPLY', edge, tex.outputs['Alpha'])
    visible_surface = math_node('MULTIPLY', in_front, math_node('GREATER_THAN', depth, 0))
    weight = math_node('MULTIPLY', inside_photo, visible_surface)
    link(math_node('MULTIPLY', strength, weight), out.inputs['Weight'])

    # Only the upper orthophoto needs projection on the ground. Any surface outside
    # the photograph receives its usual material, including newly revealed roofs.
    materials = {
        obj.data.materials[0]
        for obj in campus.children
        if obj.data.materials[0].name not in ('flag-photo', 'metal', 'roof')
    }
    materials.add(bpy.data.materials['city-19.jpg'])
    for material in materials:
        ns = material.node_tree.nodes
        connect = material.node_tree.links.new
        proj = ns.new('ShaderNodeGroup')
        proj.node_tree = group
        diff = ns.new('ShaderNodeVectorMath')
        diff.operation = 'SUBTRACT'
        connect(ns.new('ShaderNodeNewGeometry').outputs['Position'], diff.inputs[0])
        diff.inputs[1].default_value = eye
        connect(diff.outputs[0], proj.inputs['Ray'])
        output = ns.get('Material Output').inputs['Surface']
        original = output.links[0].from_socket
        photo = ns.new('ShaderNodeEmission')
        connect(proj.outputs['Color'], photo.inputs['Color'])
        mix = ns.new('ShaderNodeMixShader')
        connect(proj.outputs['Weight'], mix.inputs[0])
        connect(original, mix.inputs[1])
        connect(photo.outputs[0], mix.inputs[2])
        connect(mix.outputs[0], output)
    return strength
