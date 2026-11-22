"""Render the geographic flight and export the exact held camera for website pins.

blender -b -P render.py -- INPUT OUTPUT [--stills] [--format wide|portrait]
"""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import entrance_scene

RADIUS = 6371.0  # kilometres, with Killarney at the local origin
HOME = (-123.0441757, 49.2255942)
FPS = 60
LIFT = 156
LAST = LIFT + 600
METRO = LIFT + 213
STILLS = {'school': 0, 'sister': LIFT+70, 'metro': METRO, 'canada': LIFT+458, 'world': LAST}


def frame_at(lon, lat):
    lon, lat = map(math.radians, (lon, lat))
    return (Vector((-math.sin(lon), math.cos(lon), 0)),
            Vector((-math.sin(lat)*math.cos(lon), -math.sin(lat)*math.sin(lon), math.cos(lat))),
            Vector((math.cos(lat)*math.cos(lon), math.cos(lat)*math.sin(lon), math.sin(lat))))


basis = Matrix(frame_at(*HOME))
home_up = frame_at(*HOME)[2]


def surface(lon, lat, height=0):
    # Subtract Earth-sized coordinates in double precision before handing the
    # local position to Blender. Near the campus a float32 ULP is several pixels.
    phi, phi0 = map(math.radians, (lat, HOME[1]))
    delta = math.radians(lon - HOME[0])
    radius = RADIUS + height
    return Vector((radius * math.cos(phi) * math.sin(delta),
                   radius * (math.sin(phi)*math.cos(phi0) - math.cos(phi)*math.sin(phi0)*math.cos(delta)),
                   radius * (math.sin(phi)*math.sin(phi0) + math.cos(phi)*math.cos(phi0)*math.cos(delta)) - RADIUS))


def textured_surface(scene, folder, layers, order):
    layer = layers[order]
    globe = order == 0
    west, south, east, north = layer['bounds']
    nx, ny = (288, 144) if globe else (72, 56)
    # Chordal patches sit inside the sphere. Finer grids naturally cover coarser
    # layers; a small radial offset also separates the overlapping municipal tiles.
    height = 0 if globe else order * 0.00022
    vertices, faces, uv = [], [], []
    for j in range(ny+1):
        v = j/ny
        lat = south + (north-south)*v
        if layer.get('mercator'):
            a, b = [math.asinh(math.tan(math.radians(x))) for x in (south, north)]
            lat = math.degrees(math.atan(math.sinh(a + (b-a)*v)))
        for i in range(nx+1):
            u = i/nx
            vertices.append(surface(west + (east-west)*u, lat, height))
            uv.append((u, v))
            if i < nx and j < ny:
                k = j*(nx+1) + i
                faces.append((k, k+1, k+nx+2, k+nx+1))

    mesh = bpy.data.meshes.new(layer['file'])
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    for face in mesh.polygons:
        face.use_smooth = True
    coords = mesh.uv_layers.new(name='Geographic UV')
    for loop in mesh.loops:
        coords.data[loop.index].uv = uv[loop.vertex_index]
    obj = bpy.data.objects.new(layer['file'], mesh)
    scene.collection.objects.link(obj)
    mat = bpy.data.materials.new(layer['file'])
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    link = mat.node_tree.links.new
    uv_coords = nodes.new('ShaderNodeTexCoord').outputs['UV']
    limits = {'city-19.jpg': (.8, 1.6), 'city-17.jpg': (2.4, 5),
              'city-15.jpg': (5, 13), 'sentinel.png': (75, 220),
              'coast-20240831.jpg': (600, 1600), 'northwest.jpg': (1700, 4200)}
    distance = nodes.new('ShaderNodeCameraData').outputs['View Distance']

    def calc(op, a, b):
        node = nodes.new('ShaderNodeMath')
        node.operation = op
        for socket, value in zip(node.inputs, (a, b)):
            if isinstance(value, (float, int)):
                socket.default_value = value
            else:
                link(value, socket)
        return node.outputs[0]

    def mix(factor, under, over):
        node = nodes.new('ShaderNodeMixRGB')
        link(factor, node.inputs[0])
        link(under, node.inputs[1])
        if isinstance(over, tuple):
            node.inputs[2].default_value = over
        else:
            link(over, node.inputs[2])
        return node.outputs[0]

    # Sample the coarser maps in this patch's UV space. A color blend is
    # deterministic at each pixel, including where two imagery scales overlap.
    for source in layers[:order+1]:
        w, s, e, n = source['bounds']
        low, high = south, north
        if source.get('mercator'):
            s, n, low, high = [math.asinh(math.tan(math.radians(v))) for v in (s, n, low, high)]
        coords = nodes.new('ShaderNodeVectorMath')
        coords.operation = 'MULTIPLY_ADD'
        link(uv_coords, coords.inputs[0])
        coords.inputs[1].default_value = ((east-west)/(e-w), (high-low)/(n-s), 1)
        coords.inputs[2].default_value = ((west-w)/(e-w), (low-s)/(n-s), 0)
        texture = nodes.new('ShaderNodeTexImage')
        texture.image = bpy.data.images.load(str(folder / source['file']), check_existing=True)
        texture.extension = 'EXTEND'
        link(coords.outputs[0], texture.inputs['Vector'])
        rgb = texture.outputs['Color']
        if source is layers[0]:
            facing = nodes.new('ShaderNodeLayerWeight').outputs['Facing']
            color = mix(calc('POWER', facing, 7), rgb, (.065, .24, .44, 1))
            continue
        separate = nodes.new('ShaderNodeSeparateXYZ')
        link(coords.outputs[0], separate.inputs[0])
        u, v = separate.outputs[:2]
        edge = calc('MINIMUM', calc('MINIMUM', u, calc('SUBTRACT', 1, u)),
                    calc('MINIMUM', v, calc('SUBTRACT', 1, v)))
        edge = calc('MINIMUM', 1, calc('MAXIMUM', 0, calc('MULTIPLY', edge, 12)))
        near, far = limits[source['file']]
        fade = calc('MAXIMUM', 0, calc('MINIMUM', 1, calc('DIVIDE', calc('SUBTRACT', far, distance), far-near)))
        color = mix(calc('MULTIPLY', edge, fade), color, rgb)
    emission = nodes.new('ShaderNodeEmission')
    link(color, emission.inputs['Color'])
    link(emission.outputs[0], nodes.get('Material Output').inputs['Surface'])
    mesh.materials.append(mat)


def ease(t):
    t = max(0, min(1, t))
    return t*t*(3-2*t)


def entrance_pose(camera, frame, portrait):
    t = ease(frame/LIFT)
    ground = surface(*entrance_scene.CORNER) + Vector((0, 0, entrance_scene.GROUND_KM))
    # Start on the Killarney Street approach, looking slightly up at the doors.
    eye = ground + entrance_scene.PHOTO_EYE
    yaw = entrance_scene.PHOTO_YAW
    start_range = .034
    pitch = entrance_scene.PHOTO_PITCH - math.radians(2.2)
    focus = eye + start_range*Vector((math.sin(yaw), math.cos(yaw), math.tan(pitch)))
    aim = focus.lerp(surface(*HOME), t**1.35)
    distance = .38 if portrait else .48
    final_height = distance * math.cos(math.radians(1))
    height = .005 * math.expm1(math.log1p(final_height/.005)*t) + eye.z*(1-t)
    radius = (1-t)*start_range + t*distance*math.sin(math.radians(1)) + .10*t*(1-t)
    bearing = math.pi + yaw*(1-t)
    camera.location = Vector((aim.x + radius*math.sin(bearing), aim.y + radius*math.cos(bearing), height))
    back = (camera.location - aim).normalized()
    right = Vector((0,0,1)).cross(back).normalized()
    camera.rotation_euler = Matrix((right, back.cross(right), back)).transposed().to_euler()
    start_lens = 58 if portrait else 42
    camera.data.lens = start_lens + (38-start_lens)*t
    camera.data.shift_x = 0 if portrait else -.115-.055*t
    camera.data.clip_start = .00025
    bpy.context.view_layer.update()


def campus_lighting(scene):
    nodes = scene.world.node_tree.nodes
    link = scene.world.node_tree.links.new
    coords = nodes.new('ShaderNodeTexCoord')
    xyz = nodes.new('ShaderNodeSeparateXYZ')
    link(coords.outputs['Generated'], xyz.inputs[0])
    sky = nodes.new('ShaderNodeValToRGB')
    link(xyz.outputs['Z'], sky.inputs[0])
    gradient = sky.color_ramp
    gradient.elements[0].color = entrance_scene.rgb('3d6da7')
    gradient.elements[1].color = entrance_scene.rgb('224d89')
    gradient.elements.new(.32).color = entrance_scene.rgb('2e5f9a')
    blend = nodes.new('ShaderNodeMixRGB')
    blend.inputs[1].default_value = (.0014,.0024,.0045,1)
    link(sky.outputs[0], blend.inputs[2])
    link(blend.outputs[0], nodes.get('Background').inputs['Color'])
    light = bpy.data.lights.new('Afternoon sun', 'SUN')
    light.energy, light.angle = 2.5, math.radians(5)
    sun = bpy.data.objects.new(light.name, light)
    scene.collection.objects.link(sun)
    sun.rotation_euler = Vector((.55,.64,-.85)).to_track_quat('-Z','Y').to_euler()
    return blend.inputs[0]


def camera_pose(scene, camera, frame, portrait):
    if frame < LIFT:
        entrance_pose(camera, frame, portrait)
        return
    camera.data.clip_start = .015
    camera.data.lens = 38
    # Camera range in km. Logarithmic travel gives the campus and continent
    # comparable screen time despite the five orders of magnitude in distance.
    stops = [
        (LIFT, *HOME, .38 if portrait else .48, 1, .00 if portrait else -.17),
        (STILLS['sister'], *HOME, 1.65, 5, .00 if portrait else -.15),
        (METRO, -122.956, 49.231, 33 if portrait else 40, 21, .00 if portrait else -.13),
        (LIFT+328, -123.15, 49.75, 460, 12, .00 if portrait else -.13),
        (STILLS['canada'], -101, 60.5, 8100 if portrait else 7100, 4, .00 if portrait else -.13),
        (LAST, -102, 40, 18600 if portrait else 26200, 0, .00 if portrait else -.16)
    ]
    # The coastal waypoint guides the path without braking to a stop halfway to Canada.
    values = [(lon, lat, math.log(distance), tilt, shift) for _, lon, lat, distance, tilt, shift in stops]
    for i, (a, b) in enumerate(zip(stops, stops[1:])):
        if frame > b[0]:
            continue
        span = b[0] - a[0]
        t = (frame-a[0])/span
        ease = t*t*(3-2*t)
        pose = []
        for column in zip(*values):
            before = (column[3]-column[2])/(stops[3][0]-stops[2][0])
            after = (column[4]-column[3])/(stops[4][0]-stops[3][0])
            slope = 2*before*after/(before+after) if before*after > 0 else 0
            value = column[i] + (column[i+1]-column[i])*ease
            if i == 2:
                value += span*(t**3-t*t)*slope
            if i == 3:
                value += span*t*(1-t)**2*slope
            pose.append(value)
        lon, lat, log_distance, tilt, shift = pose
        distance = math.exp(log_distance)
        break
    east, north, up = frame_at(lon, lat)
    tilt = math.radians(tilt)
    back = basis @ (up*math.cos(tilt) - north*math.sin(tilt))
    camera.location = surface(lon, lat) + distance*back
    right = basis @ east
    camera.rotation_euler = Matrix((right, back.cross(right), back)).transposed().to_euler()
    camera.data.shift_x = shift
    bpy.context.view_layer.update()


def render(args):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    if args.metal:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type = 'METAL'
        prefs.refresh_devices()
        if not any(device.type == 'METAL' for device in prefs.devices):
            raise RuntimeError('No Metal device found')
        for device in prefs.devices:
            device.use = device.type == 'METAL'
    scene.cycles.device = 'GPU' if args.metal else 'CPU'
    scene.cycles.samples = 3
    scene.cycles.use_denoising = False
    scene.cycles.max_bounces = 1
    scene.cycles.use_adaptive_sampling = False
    scene.world = bpy.data.worlds.new('Space')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.0014, .0024, .0045, 1)
    scene.view_settings.view_transform = 'Standard'
    scene.render.resolution_percentage = 100
    scene.render.use_persistent_data = True
    scene.render.image_settings.file_format = 'JPEG'
    scene.render.image_settings.quality = 95
    camera = bpy.data.objects.new('Flight camera', bpy.data.cameras.new('Flight camera'))
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.lens = 38
    camera.data.sensor_fit = 'HORIZONTAL'
    camera.data.clip_start, camera.data.clip_end = .015, 100000
    layers = [dict(file='earth.jpg', bounds=[-180,-90,180,90]), *json.loads((args.input / 'layers.json').read_text())]
    campus = None
    if not args.camera_only:
        if args.stills or args.first < math.ceil(.98 * LIFT):
            campus = entrance_scene.build(scene, args.input, surface(*entrance_scene.CORNER), layers[-1]['bounds'])
            daylight = campus_lighting(scene)
        for order in range(len(layers)):
            textured_surface(scene, args.input, layers, order)
        if campus:
            photo_weight = entrance_scene.project_entrance(campus, args.input)
    portrait = args.format == 'portrait'
    width, height = (768, 896) if portrait else (1440, 900)
    scene.render.resolution_x, scene.render.resolution_y = width, height
    folder = args.output / args.format
    folder.mkdir(parents=True, exist_ok=True)
    camera_pose(scene, camera, METRO, portrait)
    projection = camera.calc_matrix_camera(bpy.context.evaluated_depsgraph_get(), x=width, y=height)
    clip = projection @ camera.matrix_world.inverted()
    # Map Earth-centred Cartesian kilometres directly to homogeneous clip coordinates.
    transform = basis.to_4x4() @ Matrix.Translation(-RADIUS * home_up)
    origin_track = []
    for frame in range(METRO+1):
        camera_pose(scene, camera, frame, portrait)
        point = world_to_camera_view(scene, camera, surface(*HOME))
        origin_track.append([round(point.x, 6), round(1-point.y, 6)])
    (folder / 'camera.json').write_text(json.dumps(dict(fps=FPS, last=LAST, stops={**STILLS, 'overhead': LIFT}, clip=[list(row) for row in clip @ transform], origin=origin_track)))
    if args.camera_only:
        return
    frames = STILLS.values() if args.stills else range(args.first, args.last+1, args.step)
    for frame in frames:
        path = folder / f'{frame:04d}.jpg'
        if path.exists():
            continue
        if campus:
            t = frame/LIFT
            relief = 1 - ease((t-.66)/.32)
            photo_weight.default_value = 1 - ease((t-.20)/.34)
            campus.scale.z = .001*relief
            daylight.default_value = 1 - ease((t-.48)/.35)
            for obj in campus.children:
                if obj.hide_render != (relief == 0):
                    obj.hide_render = relief == 0
            scene.cycles.samples = 18 if t < .75 else 3
        camera_pose(scene, camera, frame, portrait)
        pending = path.with_suffix('.part.jpg')
        scene.render.filepath = str(pending)
        bpy.ops.render.render(write_still=True)
        pending.replace(path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--format', choices=['wide','portrait'], required=True)
    parser.add_argument('--metal', action='store_true', help='Use the Mac GPU for Cycles')
    parser.add_argument('--camera-only', action='store_true')
    parser.add_argument('--stills', action='store_true')
    parser.add_argument('--step', type=int, default=1, help='Render every Nth frame for a camera proof')
    parser.add_argument('--first', type=int, default=0)
    parser.add_argument('--last', type=int, default=LAST)
    render(parser.parse_args(sys.argv[sys.argv.index('--')+1:]))
