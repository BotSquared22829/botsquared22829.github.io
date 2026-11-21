"""Render the About story from the existing colored Master Assembly.

Run one Blender process at a time, with --prepare then --render.
Original CAD and homepage scenes are never overwritten.
"""
import json
import math
import shutil
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

BASE = Path(__file__).resolve().parents[2]
SOURCE = BASE / 'output/robot-scene/master-assembly-2026-colors/robot-motion-2026.blend'
OUT = BASE / 'output/robot-scene/about-story/field-v3'
OUT.mkdir(parents=True, exist_ok=True)
WIDTH, HEIGHT, FPS, BUILD_END, LAST = 960, 600, 24, 72, 120

# Keep named CAD subassemblies intact. These few loose parts belong to the
# launcher but were exported beside it in the Master Assembly.
LAUNCHER_PARTS = {
    '1106 Series Square Beam (11 Hole, 88mm Length) 1106-0011-0088',
    '164t 2mm Belt',
    *(f'2802 Series Zinc-Plated Steel Button Head Screw (M4 x 0.7mm, 8mm Length) 2802-0004-0008.{suffix}'
      for suffix in ('014', '019', '041', '045', '063', '064')),
    'am-5851: Pollen__am-5851: Pollen.002',
}

# The wheels sit BETWEEN the inner and outer chassis plates. The outer plates
# must stay farther out than the wheels until the wheels are fully seated.
OUTER_PLATES = {
    'outer plate', 'outer plate.001',
    'Outer Intake Plate', 'Outer Intake Plate.001',
    'Flowertake Plate', 'Flowertake Plate.001',
}
SIDE_HARDWARE = {
    *(f'2106 Series 8mm REX e-clip.{suffix}' for suffix in ('002', '003', '004', '005')),
    '1601 Series Flanged Ball Bearing (8mm ID x 14mm OD, 4mm Thickness) 1601-0014-0008 [DISCONTINUED] <2>',
    'Outer Race.005',
    '2920 Series Steel Set-Screw Collar (8mm REX Bore)  2920-0001-4008.003',
    '56 Tooth Hub-Mount Gear (MOD 0.8, 4mm Thick Acetal) 2312-0414-0056.001',
    '56 Tooth Hub-Mount Gear (MOD 0.8, 4mm Thick Acetal) 2312-0414-0056.003',
}


def smooth_progress(frame, start, end):
    progress = max(0, min(1, (frame - start) / (end - start)))
    return progress * progress * (3 - 2 * progress)


def animate_location(group, offset, start, end):
    # Sample a bounded ease at every rendered frame: no bounce or overshoot
    # through mating surfaces, and the same exact path when scrolling backward.
    for frame in range(1, LAST + 1):
        group.location = offset * (1 - smooth_progress(frame, start, end))
        group.keyframe_insert(data_path='location', frame=frame)
    # Linear interpolation between the sampled ease values guarantees the
    # offsets remain inside their clearance bounds even at fractional frames.
    animation = group.animation_data
    for layer in animation.action.layers:
        for strip in layer.strips:
            bag = strip.channelbag(animation.action_slot)
            if bag:
                for curve in bag.fcurves:
                    for point in curve.keyframe_points:
                        point.interpolation = 'LINEAR'


def verify_wheel_clearance(wheels, wheel_sides, groups, schedules, orientation):
    """Prove separation of wheel/plate volumes along their common travel axis.

    Projecting their bounding boxes is conservative: disjoint intervals imply
    disjoint meshes, including every roller. The staged, bounded translations
    make the minimum gap occur at an endpoint, so this covers the whole path.
    Call in the fully assembled pose before the competition turn.
    """
    checks = []
    for wheel in wheels:
        side = wheel_sides[wheel]
        axis = orientation @ Vector((side, 0, 0))
        wheel_points = [axis.dot(obj.matrix_world @ Vector(corner))
                        for obj in wheel.children_recursive if obj.type == 'MESH'
                        for corner in obj.bound_box]
        wheel_offset, _, wheel_end = schedules[wheel.name]
        panel_key = 'Outer side assembly ' + ('right' if side > 0 else 'left')
        panel_offset, panel_start, _ = schedules[panel_key]
        assert panel_start > wheel_end, 'Close side plates only after the wheels seat'
        wheel_travel, panel_travel = wheel_offset.dot(axis), panel_offset.dot(axis)
        assert (wheel_offset - axis * wheel_travel).length < 1e-6
        assert (panel_offset - axis * panel_travel).length < 1e-6
        for plate in groups[panel_key].children_recursive:
            if plate.name not in OUTER_PLATES:
                continue
            plate_inner = min(axis.dot(plate.matrix_world @ Vector(corner)) for corner in plate.bound_box)
            seated_gap = plate_inner - max(wheel_points)
            minimum_gap = min(seated_gap, seated_gap + panel_travel - wheel_travel)
            assert minimum_gap > .001, (wheel.name, plate.name, minimum_gap)
            checks.append({'wheel': wheel.name, 'plate': plate.name,
                           'minimum_clearance_mm': minimum_gap * 1000})
    assert len(checks) == 12, 'Check both wheels against all three plates on each side'
    return checks


def report(stage, **details):
    data = {'stage': stage, **details}
    (OUT / 'progress.json').write_text(json.dumps(data, indent=2))
    print('ABOUT_RENDER', json.dumps(data), flush=True)


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def still(scene, name):
    scene.render.image_settings.media_type = 'IMAGE'
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.filepath = str(OUT / name)
    if 'FINISHED' not in bpy.ops.render.render(write_still=True):
        raise RuntimeError(f'Render cancelled: {name}')


def prepare():
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    scene = bpy.context.scene
    scene.frame_set(144)
    bpy.context.view_layer.update()
    old_root = bpy.data.objects['ROBOT • motion control']
    cad = [old_root, *old_root.children_recursive]
    objects = [obj for obj in cad if obj.type in {'MESH', 'FONT'}]
    meshes = [obj for obj in objects if obj.type == 'MESH']
    bounds = [obj.matrix_world @ Vector(corner) for obj in meshes for corner in obj.bound_box]
    origin = Vector(((min(v.x for v in bounds) + max(v.x for v in bounds)) / 2,
                     (min(v.y for v in bounds) + max(v.y for v in bounds)) / 2,
                     min(v.z for v in bounds)))
    model = bpy.data.objects.new('ABOUT • complete robot', None)
    scene.collection.objects.link(model)
    expected = {obj: Matrix.Translation(-origin) @ obj.matrix_world.copy() for obj in objects}
    orientation = old_root.matrix_world.to_quaternion()
    inverse_root = old_root.matrix_world.inverted()
    master = bpy.data.objects['Master Assembly']
    # Reparent complete CAD branches, not meshes selected by their height.
    # Bearings, rollers, belts, motors and fasteners travel with their assembly.
    branches = list(master.children) + [obj for obj in old_root.children if obj != master]
    branch_x = {}
    for branch in branches:
        parts = [obj for obj in [branch, *branch.children_recursive] if obj.type in {'MESH', 'FONT'}]
        centers = [inverse_root @ obj.matrix_world @ (sum((Vector(c) for c in obj.bound_box), Vector()) / 8)
                   for obj in parts]
        branch_x[branch] = sum(center.x for center in centers) / len(centers)
    wheels = [obj for obj in branches if obj.name.startswith('ROLL •')]
    assert len(wheels) == 4
    wheel_sides = {obj: 1 if (inverse_root @ obj.matrix_world.translation).x > 0 else -1
                   for obj in wheels}
    old_world = old_root.matrix_world.copy()
    for obj in cad:
        obj.animation_data_clear()
    old_root.parent = model
    old_root.matrix_parent_inverse = Matrix.Identity(4)
    old_root.matrix_world = Matrix.Translation(-origin) @ old_world
    bpy.context.view_layer.update()
    groups = {}
    schedules = {}
    members = {}
    for obj in branches:
        world = obj.matrix_world.copy()
        name = obj.name.removeprefix('occurrence of ')
        if obj in wheel_sides:
            key = obj.name
            # Slide straight along the axle, never diagonally toward the center.
            offset = orientation @ Vector((wheel_sides[obj] * .075, 0, 0))
            start, end = 5, 20
        elif name == 'turret plate':
            key, offset, start, end = 'Turret deck', Vector((0, 0, .07)), 22, 33
        elif name.startswith('turret assem <') or name in LAUNCHER_PARTS:
            key, offset, start, end = 'Complete launcher', Vector((0, 0, .16)), 35, 53
        elif (name in OUTER_PLATES | SIDE_HARDWARE | {'Part 1.016', 'Part 1.057'}
              or 'License Plate <' in name
              or name.startswith(('Control Hub (REV)', 'Expansion Hub (REV)'))
              or (name.startswith('2802 Series') and abs(branch_x[obj]) > .15)):
            side = 1 if branch_x[obj] > 0 else -1
            key = 'Outer side assembly ' + ('right' if side > 0 else 'left')
            offset, start, end = orientation @ Vector((side * .12, 0, 0)), 55, 66
        else:
            key, offset, start, end = 'Chassis and intake', Vector(), 1, 2
        if key not in groups:
            group = bpy.data.objects.new('ABOUT • ' + key, None)
            scene.collection.objects.link(group)
            group.parent = model
            groups[key] = group
            schedules[key] = (offset, start, end)
            members[key] = []
        members[key].append(name)
        obj.parent = groups[key]
        obj.matrix_parent_inverse = Matrix.Identity(4)
        obj.matrix_world = world
    # Retain the CAD hierarchy and material coordinate references; remove only
    # the old set dressing. No CAD object is deleted or split into height bands.
    for obj in list(bpy.data.objects):
        if obj not in cad and obj not in groups.values() and obj != model and obj.type not in {'CAMERA', 'LIGHT'}:
            bpy.data.objects.remove(obj, do_unlink=True)
    for key, group in groups.items():
        # The hub face markings use the original root's texture coordinates.
        # Give moving panels an equivalent moving reference so their markings
        # stay attached while the panel slides into place.
        materials = {slot.material for obj in group.children_recursive if obj.type == 'MESH'
                     for slot in obj.material_slots if slot.material and slot.material.use_nodes}
        coordinates = [node for material in materials for node in material.node_tree.nodes
                       if node.type == 'TEX_COORD' and node.object == old_root]
        if coordinates:
            anchor = bpy.data.objects.new('ABOUT • material coordinates • ' + key, None)
            scene.collection.objects.link(anchor)
            anchor.parent = group
            anchor.matrix_world = Matrix.Translation(-origin) @ old_world
            for node in coordinates:
                node.object = anchor
        animate_location(group, *schedules[key])
    for frame, angle in [(1, 0), (BUILD_END, 0), (LAST - 10, -16), (LAST, -16)]:
        model.rotation_euler.z = math.radians(angle)
        model.keyframe_insert(data_path='rotation_euler', frame=frame)

    camera = scene.camera
    camera.animation_data_clear()
    camera.data.animation_data_clear()
    camera.location = (0, -2.6, 1.45)
    aim(camera, (0, 0, .235))
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = 1.18
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from about_field import add_competition_field
    add_competition_field(scene, model, OUT)
    for light in [obj for obj in scene.objects if obj.type == 'LIGHT']:
        aim(light, (0, 0, .16))
    scene.world.color = (0, 0, 0)
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x, scene.render.resolution_y = WIDTH, HEIGHT
    scene.render.resolution_percentage = 100
    scene.render.fps = FPS
    scene.render.film_transparent = False
    scene.render.dither_intensity = 0
    scene.render.use_file_extension = True
    scene.render.use_sequencer = False
    scene.frame_start, scene.frame_end = 1, LAST
    scene.eevee.taa_render_samples = 24
    scene['About CAD source'] = str(SOURCE)
    scene['About animation'] = '1–72: outer side plates held clear, wheels seat, deck and launcher seat, outer side assemblies close, settled hold. 73–120: competition turn and full-scale BIOBUZZ field reveal.'
    scene.frame_set(BUILD_END)
    bpy.context.view_layer.update()
    errors = {obj.name: max(abs(obj.matrix_world[i][j] - matrix[i][j]) for i in range(4) for j in range(4))
              for obj, matrix in expected.items()}
    assert max(errors.values()) < 1e-5, sorted(errors.items(), key=lambda item: -item[1])[:5]
    clearance = verify_wheel_clearance(wheels, wheel_sides, groups, schedules, orientation)
    # Check every rendered pose fits, including the higher exploded launcher.
    corners = np.array([[list(corner) + [1] for corner in obj.bound_box] for obj in meshes])
    camera_inverse = camera.matrix_world.inverted()
    camera_scale = np.array([camera.data.ortho_scale, camera.data.ortho_scale * HEIGHT / WIDTH])
    framing = []
    for frame in range(1, LAST + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        matrices = np.array([camera_inverse @ obj.matrix_world for obj in meshes])
        projected = np.einsum('oij,okj->oki', matrices, corners)[:, :, :2] / camera_scale + .5
        lo, hi = projected.min(axis=(0, 1)).tolist(), projected.max(axis=(0, 1)).tolist()
        assert min(lo) > .02 and max(hi) < .98, (frame, lo, hi)
        framing.append({'frame': frame, 'min': lo, 'max': hi})
    (OUT / 'assembly-verification.json').write_text(json.dumps({
        'renderable_parts': len(objects), 'max_final_transform_error': max(errors.values()),
        'wheel_plate_clearance': clearance,
        'groups': {key: {'offset': list(offset), 'start': start, 'end': end, 'branches': members[key]}
                   for key, (offset, start, end) in schedules.items()},
        'framing': framing,
    }, indent=2))
    scene.frame_set(BUILD_END)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'about-robot.blend'))
    report('Rendering color previews', meshes=len(meshes), groups=len(groups))
    for frame, name in [(1, 'build-start.png'), (12, 'wheels-inserting.png'), (20, 'wheels-seated.png'),
                        (33, 'deck-seated.png'), (53, 'launcher-seated.png'), (60, 'plates-closing.png'),
                        (BUILD_END, 'build-complete.png'), (84, 'field-reveal.png'), (LAST, 'compete.png')]:
        scene.frame_set(frame)
        still(scene, name)

    render_sketch(scene)
    report('Previews ready', source=str(SOURCE), meshes=len(meshes), resolution=[WIDTH, HEIGHT])


def render_sketch(scene):
    report('Rendering technical sketch')
    # Match the opening color frame exactly: the browser blends materials,
    # not two different assembly poses, before starting the wheel motion.
    scene.frame_set(1)
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.render.use_compositing = False
    scene.view_settings.view_transform = 'Standard'
    shading = scene.display.shading
    shading.light = 'STUDIO'
    shading.color_type = 'SINGLE'
    shading.single_color = (.035, .035, .035)
    shading.background_type = 'WORLD'
    shading.show_shadows = False
    shading.show_cavity = True
    shading.cavity_type = 'BOTH'
    shading.curvature_ridge_factor = 2.5
    shading.curvature_valley_factor = 0
    shading.cavity_ridge_factor = 2.5
    shading.cavity_valley_factor = 0
    shading.show_object_outline = True
    shading.object_outline_color = (.3, .32, .36)
    shading.show_specular_highlight = False
    still(scene, 'sketch.png')


def transition_stills():
    """Refresh the matching sketch/color pair without re-rendering the video."""
    bpy.ops.wm.open_mainfile(filepath=str(OUT / 'about-robot.blend'))
    scene = bpy.context.scene
    scene.frame_set(1)
    first_frame = OUT / 'frames' / 'robot_0001.png'
    if first_frame.is_file():
        shutil.copyfile(first_frame, OUT / 'build-start.png')
    else:
        still(scene, 'build-start.png')
    render_sketch(scene)
    for source, target in [('sketch.png', 'about-robot-sketch.png'), ('build-start.png', 'about-robot-build-start.png')]:
        shutil.copyfile(OUT / source, BASE / 'assets' / target)
    report('Transition stills complete', frame=1, resolution=[WIDTH, HEIGHT])


def render():
    bpy.ops.wm.open_mainfile(filepath=str(OUT / 'about-robot.blend'))
    scene = bpy.context.scene
    frames = OUT / 'frames'
    frames.mkdir(exist_ok=True)
    scene.render.image_settings.media_type = 'IMAGE'
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.filepath = str(frames / 'robot_')
    scene.render.use_overwrite = False
    def written(current, *_):
        report('Rendering CAD animation', frame=current.frame_current, total=LAST)
    bpy.app.handlers.render_write.append(written)
    try:
        if 'FINISHED' not in bpy.ops.render.render(animation=True):
            raise RuntimeError('Animation cancelled; completed frames can be resumed')
    finally:
        bpy.app.handlers.render_write.remove(written)
    paths = [frames / f'robot_{frame:04d}.png' for frame in range(1, LAST + 1)]
    if not all(p.is_file() for p in paths):
        raise RuntimeError('Animation is missing frames')
    # Encode in a separate scene after rendering, with independently seekable frames.
    report('Encoding CAD animation')
    video_scene = bpy.data.scenes.new('About video encoding')
    video_scene.render.resolution_x, video_scene.render.resolution_y = WIDTH, HEIGHT
    video_scene.render.resolution_percentage = 100
    video_scene.render.fps = FPS
    video_scene.frame_start, video_scene.frame_end = 1, LAST
    video_scene.view_settings.view_transform = 'Standard'
    video_scene.view_settings.look = 'None'
    video_scene.sequencer_colorspace_settings.name = 'sRGB'
    editor = video_scene.sequence_editor_create()
    strip = editor.strips.new_image('CAD assembly', str(paths[0]), channel=1, frame_start=1)
    for path in paths[1:]:
        strip.elements.append(path.name)
    strip.frame_final_duration = LAST
    video_scene.render.image_settings.media_type = 'VIDEO'
    video_scene.render.image_settings.file_format = 'FFMPEG'
    video_scene.render.image_settings.color_mode = 'RGB'
    video_scene.render.ffmpeg.format = 'MPEG4'
    video_scene.render.ffmpeg.codec = 'H264'
    video_scene.render.ffmpeg.constant_rate_factor = 'HIGH'
    video_scene.render.ffmpeg.gopsize = 1
    video_scene.render.ffmpeg.use_max_b_frames = True
    video_scene.render.ffmpeg.max_b_frames = 0
    video_scene.render.filepath = str(OUT / 'about-robot.mp4')
    if 'FINISHED' not in bpy.ops.render.render(animation=True, scene=video_scene.name):
        raise RuntimeError('Video encoding cancelled')
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from faststart_mp4 import faststart
    faststart(OUT / 'about-robot.mp4')
    for source, target in [('about-robot.mp4', 'about-robot.mp4'), ('sketch.png', 'about-robot-sketch.png'),
                           ('frames/robot_0001.png', 'about-robot-build-start.png'), ('compete.png', 'about-robot-poster.png')]:
        shutil.copyfile(OUT / source, BASE / 'assets' / target)
    report('Complete', frames=LAST, fps=FPS, duration=LAST/FPS, source=str(SOURCE))


if __name__ == '__main__':
    if '--prepare' in sys.argv:
        prepare()
    elif '--render' in sys.argv:
        render()
    elif '--transition-stills' in sys.argv:
        transition_stills()
    else:
        raise SystemExit('Use --prepare, --render, or --transition-stills')
