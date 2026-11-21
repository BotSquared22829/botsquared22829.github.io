"""Match the Master Assembly's finishes to the supplied Onshape references.

Use --prepare for color previews, then --finish for sequential final renders.
Only the robot's materials change; scene backgrounds, lights, and motion stay.
"""
import json
import re
import shutil
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import refresh_robot_scenes as render

BASELINE = render.OUT
OUT = BASELINE.parent / 'master-assembly-2026-colors'
OUT.mkdir(parents=True, exist_ok=True)
render.OUT = OUT


def linear(value):
    return value/12.92 if value <= .04045 else ((value+.055)/1.055)**2.4


def finish(material, rgb, metallic, roughness):
    color = tuple(linear(value) for value in rgb) + (1,)
    bs = material.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value = color
    bs.inputs['Metallic'].default_value = metallic
    bs.inputs['Roughness'].default_value = roughness
    bs.inputs['Specular IOR Level'].default_value = .3
    material.diffuse_color = color


def material(name, rgb, metallic=0, roughness=.5):
    result = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    result.use_nodes = True
    finish(result, rgb, metallic, roughness)
    return result


def hub_label(obj, root):
    """Restore the colored face markings absent from the texture-free GLB."""
    side = 1 if obj.name.startswith('Control') else -1
    inv = root.matrix_world.inverted()
    points = [inv @ obj.matrix_world @ Vector(v) for v in obj.bound_box]
    lo = [min(point[i] for point in points) for i in range(3)]
    hi = [max(point[i] for point in points) for i in range(3)]
    label = obj.material_slots[0].material.copy()
    label.name = f'Reference • {obj.name} black case and orange/white label'
    obj.material_slots[0].link = 'OBJECT'
    obj.material_slots[0].material = label
    nodes, links = label.node_tree.nodes, label.node_tree.links
    bs = nodes.get('Principled BSDF')
    coords = nodes.new('ShaderNodeTexCoord'); coords.object = root
    xyz = nodes.new('ShaderNodeSeparateXYZ'); links.new(coords.outputs['Object'], xyz.inputs[0])

    def math(operation, a, b=None):
        node = nodes.new('ShaderNodeMath'); node.operation = operation
        for index, value in enumerate([a, b]):
            if value is None:
                continue
            if isinstance(value, (float, int)):
                node.inputs[index].default_value = value
            else:
                links.new(value, node.inputs[index])
        return node.outputs[0]

    def band(value, low, high):
        return math('MULTIPLY', math('GREATER_THAN', value, low), math('LESS_THAN', value, high))

    x = math('MULTIPLY', xyz.outputs['X'], side)
    y = xyz.outputs['Y']
    u = math('DIVIDE', math('SUBTRACT', y, lo[1]), hi[1]-lo[1])
    if side < 0:
        u = math('SUBTRACT', 1., u)
    v = math('DIVIDE', math('SUBTRACT', xyz.outputs['Z'], lo[2]), hi[2]-lo[2])
    outer = hi[0] if side > 0 else -lo[0]
    face = math('GREATER_THAN', x, outer-.0005)
    panel = math('MULTIPLY', face, band(u, .19, .84))
    white = math('MULTIPLY', panel, band(v, .57, .76))
    diagonal = math('SUBTRACT', 1.06, math('MULTIPLY', .65, v))
    orange = math('MULTIPLY', panel, math('MULTIPLY', band(v, .76, .94), math('GREATER_THAN', u, diagonal)))
    mix = nodes.new('ShaderNodeMixRGB')
    mix.inputs[1].default_value = tuple(bs.inputs['Base Color'].default_value)
    mix.inputs[2].default_value = tuple(linear(c) for c in (.92, .92, .92))+(1,)
    links.new(white, mix.inputs[0])
    accent = nodes.new('ShaderNodeMixRGB')
    links.new(mix.outputs[0], accent.inputs[1])
    accent.inputs[2].default_value = tuple(linear(c) for c in (1., .31, .005))+(1,)
    links.new(orange, accent.inputs[0]); links.new(accent.outputs[0], bs.inputs['Base Color'])
    # Small label lettering stays within the existing enclosure's silhouette.
    text = bpy.data.curves.new(f'{obj.name} label lettering', 'FONT')
    text.body = 'CONTROL\nHUB' if side > 0 else 'EXPANSION\nHUB'
    text.size = .008; text.space_line = 1.; text.extrude = 0
    lettering = bpy.data.objects.new(text.name, text)
    obj.users_collection[0].objects.link(lettering)
    lettering.parent = root
    lettering.location = (side*(outer+.00012), lo[1]+(hi[1]-lo[1])*(.23 if side > 0 else .77), lo[2]+.71*(hi[2]-lo[2]))
    lettering.rotation_euler = Matrix(((0, 0, side), (side, 0, 0), (0, 1, 0))).to_euler()
    text.materials.append(material('Reference • black label ink', (.025, .025, .025), roughness=.65))


def apply_colors():
    scene = bpy.context.scene
    root = bpy.data.objects[render.ROOT]
    objects = [obj for obj in root.children_recursive if obj.type == 'MESH']
    materials = {slot.material for obj in objects for slot in obj.material_slots if slot.material}
    audit = []
    for mat in materials:
        match = re.match(r'^(\d+\.\d+)_(\d+\.\d+)_(\d+\.\d+)', mat.name)
        if not match:
            continue
        rgb = tuple(float(value) for value in match.groups())
        r, g, b = rgb
        spread = max(rgb)-min(rgb)
        if spread < .045:
            gray = sum(rgb)/3
            if gray <= .4:
                # These are polymer/rubber housings, not metallic gray paint.
                value = max(.025, gray*.60)
                target, metal, rough, role = (value,)*3, 0, .55, 'Charcoal polymer'
            else:
                target, metal, rough, role = rgb, .72, .36, 'Silver aluminum or steel'
        elif r > .7 and g < .06 and b < .06:
            target, metal, rough, role = (.82, .008, .012), 0, .42, 'BotSquared red'
        elif r > .9 and g > .85 and b > .15:
            target, metal, rough, role = (.99, .93, .035), 0, .32, 'Lemon yellow game ball'
        elif r > .85 and g > .45 and b < .1:
            target, metal, rough, role = rgb, .28, .35, 'Golden yellow motor sleeve or wheel plate'
        elif r > .4 and .1 < g < .4 and b < .12:
            target, metal, rough, role = (.68, .20, .045), 0, .42, 'Burnt orange intake roller'
        else:
            target, metal, rough, role = rgb, .1, .45, 'CAD accent'
        finish(mat, target, metal, rough)
        mat['Reference finish'] = role
        audit.append({'material': mat.name, 'role': role, 'reference_srgb': target,
                      'linear_base_color': list(mat.diffuse_color), 'metallic': metal, 'roughness': rough})
    tire = material('Reference • black rubber tire', (.075, .078, .08), roughness=.72)
    digits = material('Reference • light gray number lettering', (.75, .75, .75), metallic=.22, roughness=.4)
    for obj in objects:
        if obj.name.startswith(('Roller Cover', 'Roller Core')):
            for slot in obj.material_slots:
                slot.link = 'OBJECT'; slot.material = tire
        parent = obj.parent
        number = False
        while parent and parent != root:
            if 'License Plate <' in parent.name:
                number = True
            parent = parent.parent
        if number and obj.name.startswith('Part '):
            for slot in obj.material_slots:
                slot.link = 'OBJECT'; slot.material = digits
        if obj.name in {'Control Hub (REV)', 'Expansion Hub (REV)'}:
            hub_label(obj, root)
    scene['Color reference'] = 'Five Onshape screenshots supplied on 2026-10-14; white is UI, not a scene background.'
    scene['Finish palette'] = 'Silver lattice; charcoal plastics/electronics; black rubber/belts; red plates/logo; orange rollers; yellow balls; gold motor sleeves.'
    return audit


def prepare():
    for filename in ['robot-motion-2026.blend', 'robot-front-2026.blend']:
        render.status('Applying reference colors', scene=filename)
        bpy.ops.wm.open_mainfile(filepath=str(BASELINE/filename))
        scene = bpy.context.scene
        scene.frame_set(160); bpy.context.view_layer.update()
        audit = apply_colors()
        scene.render.resolution_percentage = 100
        scene.render.filepath = str(OUT/'frames'/'robot_' if 'motion' in filename else OUT/'robot-front-2026.png')
        bpy.ops.wm.save_as_mainfile(filepath=str(OUT/filename))
        (OUT/f'{Path(filename).stem}-materials.json').write_text(json.dumps(audit, indent=2))
        if 'motion' in filename:
            render.status('Rendering color previews')
            for frame, name in [(1, 'opening.png'), (68, 'side-preview.png'), (144, 'hero-preview.png')]:
                scene.frame_set(frame)
                render.png(scene, OUT/name, 100 if frame == 1 else 60)
        else:
            render.configure_gpu(scene)
            scene.cycles.samples = 16
            render.status('Rendering portrait color preview')
            render.png(scene, OUT/'portrait-preview.png', 30)
    shutil.copyfile(BASELINE/'framing.json', OUT/'framing.json')
    # Entirely offscreen frames are identical black, independent of materials.
    frames = OUT/'frames'; frames.mkdir(exist_ok=True)
    for check in json.loads((OUT/'framing.json').read_text()):
        frame = check['frame']
        if frame <= 144 and check['max'][0] < 0:
            shutil.copyfile(BASELINE/'frames'/f'robot_{frame:04d}.png', frames/f'robot_{frame:04d}.png')
    render.status('Color previews ready')


def repair_scene_paths():
    for filename in ['robot-motion-2026.blend', 'robot-front-2026.blend']:
        bpy.ops.wm.open_mainfile(filepath=str(OUT/filename))
        scene = bpy.context.scene
        scene.render.filepath = str(OUT/'frames'/'robot_' if 'motion' in filename else OUT/'robot-front-2026.png')
        bpy.ops.wm.save_as_mainfile(filepath=str(OUT/filename))


if __name__ == '__main__':
    if '--prepare' in sys.argv:
        prepare()
    elif '--finish' in sys.argv:
        render.portrait()
        render.animation()
        render.verify_outputs()
        repair_scene_paths()
    elif '--paths' in sys.argv:
        repair_scene_paths()
    else:
        raise SystemExit('Pass --prepare or --finish after --')
