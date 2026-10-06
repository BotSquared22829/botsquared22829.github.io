"""Render the downloaded Robot V5 CAD assembly in a reusable Blender studio.

Blender --background --python scripts/robot-scene/render_firetruck_studio.py
Append -- --final to render the saved scene at delivery resolution.
Use -- --source /path/to/Robot.glb to choose a CAD export for a new scene.
"""
import argparse
import bpy
import json
import math
import sys
from pathlib import Path
from mathutils import Vector

OUT = Path(__file__).resolve().parents[2] / 'output/robot-scene/firetruck-v5'
OUT.mkdir(parents=True, exist_ok=True)
BLEND = OUT / 'robot-v5-studio.blend'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--final', action='store_true')
parser.add_argument('--source', type=Path, default=Path.home() / 'Downloads/Robot V5.glb')
arguments = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
FINAL = arguments.final
SOURCE = arguments.source.expanduser().resolve()

if FINAL:
    bpy.ops.wm.open_mainfile(filepath=str(BLEND))
else:
    if not SOURCE.is_file():
        raise FileNotFoundError(f'CAD export not found: {SOURCE}. Pass -- --source /path/to/Robot.glb')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(SOURCE))
    scene = bpy.context.scene
    imported = list(scene.objects)
    meshes = [o for o in imported if o.type == 'MESH']

    def bounds():
        bpy.context.view_layer.update()
        pts = [o.matrix_world @ Vector(v) for o in meshes for v in o.bound_box]
        lo = Vector(tuple(min(p[i] for p in pts) for i in range(3)))
        hi = Vector(tuple(max(p[i] for p in pts) for i in range(3)))
        return lo, hi, pts

    lo, hi, _ = bounds()
    original_dimensions = list(hi-lo)
    root = bpy.data.objects.new('Robot V5 | assembly', None)
    scene.collection.objects.link(root)
    for obj in imported:
        if obj.parent is None:
            world = obj.matrix_world.copy()
            obj.parent = root
            obj.matrix_world = world
    # The source export kept Onshape's Z-up convention; glTF imports Y-up.
    root.rotation_euler.x = -math.pi / 2
    lo, hi, _ = bounds()
    root.location = (-(lo.x+hi.x)/2, -(lo.y+hi.y)/2, -lo.z)
    lo, hi, pts = bounds()
    height = (hi-lo).z
    print('ROBOT_DIMENSIONS', tuple(hi-lo), flush=True)

    # Keep CAD colors while giving neutral metal and dark rubber realistic response.
    for mat in bpy.data.materials:
        if not mat.use_nodes:
            continue
        bs = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if bs is None:
            continue
        rgb = tuple(bs.inputs['Base Color'].default_value[:3])
        brightness = sum(rgb)/3
        neutral = max(rgb)-min(rgb) < .065
        # Onshape encodes its display RGB values directly in this export.
        linear = tuple(c/12.92 if c <= .04045 else ((c+.055)/1.055)**2.4 for c in rgb)
        bs.inputs['Base Color'].default_value = (*linear, 1)
        bs.inputs['Metallic'].default_value = .72 if brightness > .4 else .12
        bs.inputs['Roughness'].default_value = .29 if brightness > .4 else .47
        if neutral and brightness < .36:
            bs.inputs['Metallic'].default_value = .02
            bs.inputs['Roughness'].default_value = .58

    def material(name, rgb, roughness, metallic=0):
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        bs = mat.node_tree.nodes.get('Principled BSDF')
        bs.inputs['Base Color'].default_value = (*rgb, 1)
        bs.inputs['Roughness'].default_value = roughness
        bs.inputs['Metallic'].default_value = metallic
        return mat

    floor_mat = material('Studio | graphite satin', (.035,.043,.052), .42, .18)
    bpy.ops.mesh.primitive_plane_add(size=200*height, location=(0,0,-.001*height))
    floor = bpy.context.object
    floor.name = 'Studio | seamless graphite floor'
    floor.data.materials.append(floor_mat)

    world = bpy.data.worlds.new('Studio | soft ambient')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (.16,.19,.24,1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = .22
    scene.world = world

    def aim(obj, target):
        obj.rotation_euler = (Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()

    def area(name, loc, power, size, color, aspect=1):
        data = bpy.data.lights.new(name, 'AREA')
        data.energy = power * height**2 * .3
        data.shape = 'RECTANGLE'
        data.size = size*height
        data.size_y = size*height*aspect
        data.color = color
        obj = bpy.data.objects.new(name, data)
        scene.collection.objects.link(obj)
        obj.location = Vector(loc)*height
        aim(obj, (0,0,.45*height))

    area('Studio | large soft key', (-1.4,-1.4,2.1), 450, 1.35, (1,.96,.90), 1.4)
    area('Studio | cool rim', (1.1,.9,1.75), 550, .8, (.77,.87,1), 1.7)
    area('Studio | front fill', (1.6,-1.6,1.0), 180, 1.4, (.89,.94,1))
    area('Studio | top strip', (-.15,.3,2.4), 230, .9, (1,1,1), .3)

    camera_data = bpy.data.cameras.new('Camera | three-quarter hero')
    camera = bpy.data.objects.new(camera_data.name, camera_data)
    scene.collection.objects.link(camera)
    target = Vector((0,0,.46*height))
    direction = Vector((1.15,-1.8,.9)).normalized()
    camera.location = target + direction*height*3.6
    aim(camera, target)
    camera_data.type = 'ORTHO'
    scene.camera = camera
    scene.render.resolution_x = 2400
    scene.render.resolution_y = 1800
    # Fit actual geometry to the camera with a generous margin for shadows.
    bpy.context.view_layer.update()
    projected = [camera.matrix_world.inverted() @ p for p in pts]
    span_x = max(p.x for p in projected)-min(p.x for p in projected)
    span_y = max(p.y for p in projected)-min(p.y for p in projected)
    camera_data.ortho_scale = max(span_x*1.32, span_y*4/3*1.26)
    camera_data.clip_end = 100*height
    scene['Source'] = 'Onshape Firetruck Comp 2026 / Robot V5, fine GLB export'
    scene['Source file'] = str(SOURCE)
    scene['Notes'] = 'CAD colors retained; graphite studio floor and four area lights.'
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 96
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 6
    scene.cycles.transparent_max_bounces = 6
    scene.view_settings.view_transform = 'AgX'
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.film_transparent = False
    scene.render.filepath = str(OUT/'robot-v5-studio.png')
    scene.render.resolution_percentage = 100
    for screen in bpy.data.screens:
        for space_area in screen.areas:
            if space_area.type == 'VIEW_3D':
                space_area.spaces.active.region_3d.view_perspective = 'CAMERA'
                space_area.spaces.active.overlay.show_overlays = False
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    (OUT/'scene-info.json').write_text(json.dumps({
        'source': scene['Source file'], 'original_dimensions': original_dimensions,
        'dimensions': list(hi-lo), 'meshes': len(meshes),
        'materials': len(bpy.data.materials),
        'vertices': sum(len(o.data.vertices) for o in meshes),
        'polygons': sum(len(o.data.polygons) for o in meshes),
    }, indent=2))

scene = bpy.context.scene
# Metal is available on this Mac; fall back to CPU if it is not exposed.
prefs = bpy.context.preferences.addons['cycles'].preferences
try:
    prefs.compute_device_type = 'METAL'
    prefs.get_devices()
    metal = [d for d in prefs.devices if d.type == 'METAL']
    for device in prefs.devices:
        device.use = device.type == 'METAL'
    scene.cycles.device = 'GPU' if metal else 'CPU'
except Exception:
    scene.cycles.device = 'CPU'
scene.render.resolution_percentage = 100 if FINAL else 40
scene.cycles.samples = 96 if FINAL else 20
scene.render.filepath = str(OUT/('robot-v5-studio.png' if FINAL else 'robot-v5-preview.png'))
bpy.ops.render.render(write_still=True)
print('RENDER_COMPLETE', scene.render.filepath, flush=True)
