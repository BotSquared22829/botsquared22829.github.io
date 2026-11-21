"""Place the full-size official BIOBUZZ field behind the About robot."""
import json
import math
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector
from bpy_extras.object_utils import world_to_camera_view

BASE = Path(__file__).resolve().parents[2]
CAD = BASE / 'output/robot-scene/field-cad'
FIELD_ANGLE = 30


def orient_field(field):
    # View along the perimeter instead of through the central hive and its
    # A-frame. Rotate the whole field around the robot; preserve every part.
    field.matrix_world = (Matrix.Rotation(math.radians(FIELD_ANGLE), 4, 'Z')
                          @ Matrix.Translation((.94, -1.24, field.location.z)))
    bpy.context.view_layer.update()


def verify_field_crop(scene, field):
    foreground = [obj for obj in field.children_recursive if obj.type == 'MESH'
                  and any(name in obj.name for name in ('Hive Goal', 'Goal Rib', 'A-Frame Leg'))]
    assert foreground
    for obj in foreground:
        points = [world_to_camera_view(scene, scene.camera, obj.matrix_world @ Vector(corner))
                  for corner in obj.bound_box]
        lo = [min(v[i] for v in points) for i in range(2)]
        hi = [max(v[i] for v in points) for i in range(2)]
        assert hi[0] <= 0 or lo[0] >= 1 or hi[1] <= 0 or lo[1] >= 1, obj.name
    return len(foreground)


def add_competition_field(scene, robot, output):
    scene.frame_set(72)
    bpy.context.view_layer.update()
    wheels = [obj for obj in robot.children_recursive if obj.name.startswith('ROLL •')]
    contact_heights = []
    for wheel in wheels:
        minima = []
        for obj in wheel.children_recursive:
            if obj.type != 'MESH':
                continue
            vertices = np.empty(len(obj.data.vertices) * 3, dtype=np.float32)
            obj.data.vertices.foreach_get('co', vertices)
            matrix = np.array(obj.matrix_world)
            minima.append(float((vertices.reshape(-1, 3) @ matrix[2, :3] + matrix[2, 3]).min()))
        contact_heights.append(min(minima))
    assert len(contact_heights) == 4
    assert max(contact_heights) - min(contact_heights) < .001

    before = set(scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(CAD / 'biobuzz-field.glb'))
    imported = set(scene.objects) - before
    roots = [obj for obj in imported if obj.parent not in imported]
    field = bpy.data.objects.new('ABOUT • official BIOBUZZ field', None)
    scene.collection.objects.link(field)
    for obj in roots:
        obj.parent = field
    for obj in imported:
        obj.name = 'FIELD • ' + obj.name
    field_collection = bpy.data.collections.new('ABOUT • field geometry')
    scene.collection.children.link(field_collection)
    for obj in [field, *imported]:
        for collection in list(obj.users_collection):
            collection.objects.unlink(obj)
        field_collection.objects.link(obj)
    bpy.context.view_layer.update()
    tiles = [obj for obj in imported if obj.type == 'MESH' and 'Field Soft Tiles' in obj.name]
    assert len(tiles) == 36
    tile_points = [obj.matrix_world @ Vector(corner) for obj in tiles for corner in obj.bound_box]
    lo = Vector([min(v[i] for v in tile_points) for i in range(3)])
    hi = Vector([max(v[i] for v in tile_points) for i in range(3)])
    assert 3.5 < hi.x - lo.x < 3.7 and 3.5 < hi.y - lo.y < 3.7
    assert .014 < hi.z - lo.z < .017, 'Check the STEP/glTF up axis and meter conversion'
    # Place the robot in the rear-left lane, beside the perimeter flower.
    # Keep the ENTIRE field at 1:1 scale: the existing camera crops the view.
    field.location = (.94, -1.24, min(contact_heights) - hi.z)
    orient_field(field)
    assert all(abs(scale - 1) < 1e-6 for scale in field.scale)
    # Blend two identically posed views in the compositor. Fading individual
    # CAD materials creates noisy transparency and exposes hidden back faces.
    # This keeps real surfaces, occlusion, and contact shadows intact.
    full_view = scene.view_layers[0]
    full_view.name = 'ABOUT • robot on field'
    bare_view = scene.view_layers.new('ABOUT • robot alone')
    bare_view.layer_collection.children[field_collection.name].exclude = True
    tree = bpy.data.node_groups.new('ABOUT • smooth field reveal', 'CompositorNodeTree')
    tree.interface.new_socket(name='Image', in_out='OUTPUT', socket_type='NodeSocketColor')
    scene.compositing_node_group = tree
    nodes, links = tree.nodes, tree.links
    bare = nodes.new('CompositorNodeRLayers')
    bare.layer = bare_view.name
    full = nodes.new('CompositorNodeRLayers')
    full.layer = full_view.name
    mix = nodes.new('ShaderNodeMix')
    mix.data_type = 'RGBA'
    mix.blend_type = 'MIX'
    mix.label = 'Field reveal at unchanged physical scale'
    links.new(bare.outputs['Image'], mix.inputs[6])
    links.new(full.outputs['Image'], mix.inputs[7])
    result = nodes.new('NodeGroupOutput')
    links.new(mix.outputs[2], result.inputs['Image'])
    for frame in range(1, 121):
        progress = max(0, min(1, (frame - 72) / 26))
        mix.inputs[0].default_value = progress * progress * (3 - 2 * progress)
        mix.inputs[0].keyframe_insert('default_value', frame=frame)
    scene.render.use_compositing = True
    for obj in imported:
        # Invisible during both the color build and Workbench sketch render.
        for frame, hidden in [(1, True), (72, True), (73, False), (120, False)]:
            obj.hide_render = hidden
            obj.keyframe_insert('hide_render', frame=frame)

    bpy.context.view_layer.update()
    robot_points = [obj.matrix_world @ Vector(corner) for obj in robot.children_recursive
                    if obj.type == 'MESH' for corner in obj.bound_box]
    robot_lo = Vector([min(v[i] for v in robot_points) for i in range(3)])
    robot_hi = Vector([max(v[i] for v in robot_points) for i in range(3)])
    # The rear perimeter is outside the robot's bounding volume; the nearby
    # flower also stays behind it. No miniature arena or altered tile spacing.
    robot_in_field = [field.matrix_world.inverted() @ point for point in robot_points]
    rear_wall_clearance = 1.777 - max(point.y for point in robot_in_field)
    assert rear_wall_clearance > .1
    report = {
        'source': json.loads((CAD / 'source.json').read_text()),
        'imported_meshes': sum(obj.type == 'MESH' for obj in imported),
        'tile_count': len(tiles), 'tile_floor_dimensions_m': list(hi - lo),
        'field_scale': list(field.scale), 'field_translation_m': list(field.location),
        'field_rotation_degrees': FIELD_ANGLE,
        'foreground_parts_outside_camera': verify_field_crop(scene, field),
        'wheel_contact_heights_m': contact_heights,
        'max_wheel_floor_gap_mm': (max(contact_heights) - min(contact_heights)) * 1000,
        'robot_bounds_m': [list(robot_lo), list(robot_hi)],
        'rear_wall_clearance_m': rear_wall_clearance,
        'camera_width_m': scene.camera.data.ortho_scale,
    }
    (output / 'field-verification.json').write_text(json.dumps(report, indent=2))
    scene['About field source'] = str(CAD / 'biobuzz-field.glb')
    scene.frame_set(72)
    return field
