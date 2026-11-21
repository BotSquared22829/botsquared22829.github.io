"""Replace the CAD in the existing website scenes, preserving both originals.

Run in one Blender process at a time with --prepare, --animation, or --portrait.
After reviewing the previews, --finish renders both outputs sequentially.
The animation stays 192 frames at 24 fps, with independent MP4 seek frames.
"""
import json
import shutil
import sys
import time
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

BASE = Path(__file__).resolve().parents[2]
SOURCE = Path.home() / 'Downloads' / 'Master Assembly.glb'
OLD = BASE / 'output' / 'robot-scene'
OUT = OLD / 'master-assembly-2026'
ROOT = 'ROBOT • motion control'
COLLECTION = 'ROBOT 2026 • imported CAD'
OUT.mkdir(parents=True, exist_ok=True)
START = time.time()


def status(stage, **details):
    data = {'stage': stage, 'elapsed_seconds': round(time.time()-START, 1), **details}
    (OUT / 'progress.json').write_text(json.dumps(data, indent=2))
    print('ROBOT_REFRESH', json.dumps(data), flush=True)


def png(scene, path, percentage=100):
    scene.render.resolution_percentage = percentage
    scene.render.image_settings.media_type = 'IMAGE'
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.filepath = str(path)
    result = bpy.ops.render.render(write_still=True)
    if 'FINISHED' not in result:
        raise RuntimeError(f'Render cancelled: {path}')


def configure_gpu(scene):
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'METAL'
    prefs.get_devices()
    metal = [device for device in prefs.devices if device.type == 'METAL']
    for device in prefs.devices:
        device.use = device in metal
    scene.cycles.device = 'GPU' if metal else 'CPU'


def projected_bounds(scene, parts):
    corners = np.array([[list(v)+[1] for v in obj.bound_box] for obj in parts])
    matrices = np.array([scene.camera.matrix_world.inverted() @ obj.matrix_world for obj in parts])
    points = np.einsum('oij,okj->oki', matrices, corners)
    scale = np.array([scene.camera.data.ortho_scale,
                      scene.camera.data.ortho_scale*scene.render.resolution_y/scene.render.resolution_x])
    xy = points[:, :, :2] / scale + .5
    return xy.min(axis=(0, 1)).tolist(), xy.max(axis=(0, 1)).tolist()


def prepare():
    status('Loading original animation')
    bpy.ops.wm.open_mainfile(filepath=str(OLD / 'robot-motion-black-right.blend'))
    scene = bpy.context.scene
    scene.frame_set(1)
    root = bpy.data.objects[ROOT]
    model_transform = bpy.data.objects['Master Assembly'].matrix_basis.copy()
    rigs = {obj.name.removeprefix('ROLL • '): obj for obj in root.children_recursive
            if obj.name.startswith('ROLL • ')}
    assert len(rigs) == 4
    for obj in list(root.children_recursive):
        if obj not in rigs.values():
            bpy.data.objects.remove(obj, do_unlink=True)
    bpy.ops.outliner.orphans_purge(do_recursive=True)
    before = set(bpy.data.objects)
    status('Importing new Master Assembly', source=str(SOURCE))
    bpy.ops.import_scene.gltf(filepath=str(SOURCE))
    imported = set(bpy.data.objects) - before
    bpy.context.view_layer.update()
    wheels = {obj.name: obj for obj in imported if obj.name in rigs}
    assert len(wheels) == 4
    wheel_centers = {}
    for name, wheel in wheels.items():
        core = next(obj for obj in wheel.children_recursive
                    if obj.type == 'MESH' and obj.name.startswith('Wheel Core'))
        wheel_centers[name] = sum((core.matrix_world @ Vector(v) for v in core.bound_box), Vector()) / 8
    for obj in imported:
        if obj.parent is None:
            source_matrix = obj.matrix_world.copy()
            obj.parent = root
            obj.matrix_parent_inverse = Matrix.Identity(4)
            obj.matrix_basis = model_transform @ source_matrix
    for name, rig in rigs.items():
        rig.location = model_transform @ wheel_centers[name]
    bpy.context.view_layer.update()
    for name, wheel in wheels.items():
        world = wheel.matrix_world.copy()
        wheel.parent = rigs[name]
        wheel.matrix_world = world
    for material in {mat for obj in imported if obj.type == 'MESH' for mat in obj.data.materials if mat}:
        if material.use_nodes:
            bs = material.node_tree.nodes.get('Principled BSDF')
            if bs:
                color = bs.inputs['Base Color'].default_value
                metal = max(color[:3])-min(color[:3]) < .04 and color[0] > .3
                bs.inputs['Metallic'].default_value = .6 if metal else .05
                bs.inputs['Roughness'].default_value = .32 if metal else .46
    collection = bpy.data.collections.new(COLLECTION)
    scene.collection.children.link(collection)
    for obj in imported | {root} | set(rigs.values()):
        for previous in list(obj.users_collection):
            previous.objects.unlink(obj)
        collection.objects.link(obj)
    scene['CAD source'] = str(SOURCE)
    scene['Previous scene'] = 'robot-motion-black-right.blend'
    scene.render.dither_intensity = 0
    scene.render.resolution_percentage = 100
    parts = [obj for obj in root.children_recursive if obj.type == 'MESH']
    checks = []
    for frame in range(1, 193):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        lo, hi = projected_bounds(scene, parts)
        checks.append({'frame': frame, 'min': lo, 'max': hi})
        if 28 <= frame <= 192:
            assert min(lo) >= 0 and max(hi) <= 1, (frame, lo, hi)
    assert checks[0]['max'][0] < 0, checks[0]
    assert checks[143]['min'] == checks[191]['min']
    (OUT/'framing.json').write_text(json.dumps(checks, indent=2))
    scene.frame_set(160)
    scene.render.image_settings.media_type = 'IMAGE'
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = str(OUT/'frames'/'robot_')
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'robot-motion-2026.blend'))
    status('Rendering animation previews', mesh_instances=len(parts))
    for frame, name in [(1, 'opening.png'), (68, 'side-preview.png'), (144, 'hero-preview.png')]:
        scene.frame_set(frame)
        png(scene, OUT/name, 100 if frame == 1 else 60)
    status('Loading original portrait')
    bpy.ops.wm.open_mainfile(filepath=str(OLD/'robot-front-premium.blend'))
    scene = bpy.context.scene
    previous = bpy.data.objects[ROOT]
    pose = previous.matrix_world.copy()
    for obj in list(previous.children_recursive)+[previous]:
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.ops.outliner.orphans_purge(do_recursive=True)
    with bpy.data.libraries.load(str(OUT/'robot-motion-2026.blend'), link=False) as (available, loaded):
        loaded.collections = [COLLECTION]
    scene.collection.children.link(loaded.collections[0])
    root = bpy.data.objects[ROOT]
    for obj in [root]+list(root.children_recursive):
        obj.animation_data_clear()
        if obj.name.startswith('ROLL • '):
            obj.rotation_euler = (0, 0, 0)
    root.matrix_world = pose
    scene['CAD source'] = str(SOURCE)
    scene['Previous scene'] = 'robot-front-premium.blend'
    configure_gpu(scene)
    scene.render.resolution_percentage = 100
    scene.cycles.samples = 128
    scene.render.filepath = str(OUT/'robot-front-2026.png')
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'robot-front-2026.blend'))
    scene.cycles.samples = 32
    status('Rendering portrait preview')
    png(scene, OUT/'portrait-preview.png', 40)
    status('Previews ready', mesh_instances=len(parts), wheel_rigs=len(rigs))


def animation():
    bpy.ops.wm.open_mainfile(filepath=str(OUT/'robot-motion-2026.blend'))
    scene = bpy.context.scene
    frames = OUT/'frames'
    frames.mkdir(exist_ok=True)
    scene.render.resolution_percentage = 100
    scene.render.dither_intensity = 0
    root = bpy.data.objects[ROOT]
    moving = [root]+[obj for obj in root.children_recursive if obj.name.startswith('ROLL • ')]
    def motion_state(frame):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        return tuple(round(value, 6) for obj in moving for row in obj.matrix_world for value in row)
    hold = motion_state(68)
    assert all(motion_state(frame) == hold for frame in range(69, 81))
    paths = [frames/f'robot_{frame:04d}.png' for frame in range(1, 145)]
    if paths[67].exists():
        for frame in range(69, 81):
            shutil.copyfile(paths[67], paths[frame-1])
    scene.render.image_settings.media_type = 'IMAGE'
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.filepath = str(frames/'robot_')
    scene.render.use_overwrite = False
    scene.frame_start = 1
    scene.frame_end = 144
    def frame_written(current, *args):
        frame = current.frame_current
        if frame == 68:
            for held_frame in range(69, 81):
                shutil.copyfile(paths[67], paths[held_frame-1])
        status('Rendering animation', frame=frame, frames=144)
    bpy.app.handlers.render_write.append(frame_written)
    try:
        result = bpy.ops.render.render(animation=True)
        if 'FINISHED' not in result:
            raise RuntimeError('Animation rendering was cancelled; completed frames are resumable')
    finally:
        bpy.app.handlers.render_write.remove(frame_written)
    assert all(path.is_file() for path in paths)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from encode_frames import encode_frames
    from faststart_mp4 import faststart
    status('Encoding animation')
    video = OUT/'robot-motion-2026.mp4'
    encode_frames(paths+[paths[-1]]*48, video, all_intra=True)
    faststart(video)
    shutil.copyfile(paths[0], OUT/'robot-motion-2026-start.png')
    shutil.copyfile(paths[-1], OUT/'robot-motion-2026-final.png')
    status('Animation complete', video=str(video))


def portrait():
    bpy.ops.wm.open_mainfile(filepath=str(OUT/'robot-front-2026.blend'))
    scene = bpy.context.scene
    configure_gpu(scene)
    status('Rendering final portrait', samples=scene.cycles.samples, device=scene.cycles.device)
    png(scene, OUT/'robot-front-2026.png')
    status('Portrait complete', image=str(OUT/'robot-front-2026.png'))


def verify_outputs():
    opening = bpy.data.images.load(str(OUT/'robot-motion-2026-start.png'), check_existing=False)
    values = np.empty(len(opening.pixels), dtype=np.float32)
    opening.pixels.foreach_get(values)
    assert values.reshape(-1, 4)[:, :3].max() == 0, 'Opening must be entirely black'
    bpy.data.images.remove(opening)
    result = {
        'source': str(SOURCE), 'source_bytes': SOURCE.stat().st_size,
        'animation': {'path': str(OUT/'robot-motion-2026.mp4'), 'frames': 192,
                      'fps': 24, 'resolution': [1280, 720], 'black_opening': True},
        'portrait': {'path': str(OUT/'robot-front-2026.png'), 'resolution': [2400, 1600]},
        'original_scenes_preserved': True,
    }
    (OUT/'complete.json').write_text(json.dumps(result, indent=2))
    status('Both renders complete')


if __name__ == '__main__':
    if '--prepare' in sys.argv:
        prepare()
    elif '--finish' in sys.argv:
        animation()
        portrait()
        verify_outputs()
    elif '--animation' in sys.argv:
        animation()
    elif '--portrait' in sys.argv:
        portrait()
    else:
        raise SystemExit('Pass --prepare, --animation, or --portrait after --')
