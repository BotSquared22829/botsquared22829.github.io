"""Match Robot V5's materials to assets/robot-cdrc-2026.jpg and render."""
import bpy
import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / 'output/robot-scene/firetruck-v5'
SCENE = OUT / 'robot-v5-studio.blend'
IMAGE = OUT / 'robot-v5-reference-colors.png'
bpy.ops.wm.open_mainfile(filepath=str(SCENE))

def material(name, color, roughness, metallic=0, specular=.35):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = (*color, 1)
    bs = mat.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value = (*color, 1)
    bs.inputs['Metallic'].default_value = metallic
    bs.inputs['Roughness'].default_value = roughness
    bs.inputs['Specular IOR Level'].default_value = specular
    return mat

red = material('Reference | red printed polymer', (.34,.006,.013), .46, specular=.28)
blue = material('Reference | blue fan housing', (.012,.046,.20), .46, specular=.3)
rubber = material('Reference | black rubber', (.006,.007,.008), .67, specular=.24)
black = material('Reference | black electronics casing', (.009,.01,.012), .48)
graphite = material('Reference | dark wheel centers', (.015,.017,.020), .4, .12)

assignments = {}
def assign(obj, index, mat):
    obj.material_slots[index].link = 'OBJECT'
    obj.material_slots[index].material = mat
    assignments.setdefault(obj.name, []).append({'slot': index, 'material': mat.name})

printed = {'Part 1': red, 'Part 1.001': blue, 'Part 1.002': red, 'Part 1.003': red}
for name, mat in printed.items():
    obj = bpy.data.objects[name]
    for index in range(len(obj.material_slots)):
        assign(obj, index, mat)
    obj['Finish'] = mat.name

for obj in bpy.context.scene.objects:
    if obj.type != 'MESH':
        continue
    # Read the untouched CAD mesh slots so the operation remains repeatable.
    for index, source in enumerate(obj.data.materials):
        if not source:
            continue
        name = source.name
        if obj.name.startswith('3614 Series Rhino Wheel'):
            if name.startswith('0.188235_'):
                assign(obj, index, rubber)
            elif name.startswith('0.250980_'):
                assign(obj, index, graphite)
        elif obj.name == 'Control Hub REV-31-1152':
            if name.startswith(('0.647059_', '0.349020_', '0.250980_')):
                assign(obj, index, black)
        elif obj.name.startswith('Matrix 12V 3000mAh NiMH Battery'):
            if name.startswith(('0.917647_', '0.250980_')):
                assign(obj, index, black)

scene = bpy.context.scene
scene['Color reference'] = 'assets/robot-cdrc-2026.jpg'
scene['Printed parts finish'] = 'Photo reference: red claws and lower tray; blue fan housing'
scene['Notes'] = 'Photo-matched material colors; original CAD geometry and studio composition retained.'
scene.render.resolution_percentage = 100
scene.render.filepath = str(IMAGE)
scene.cycles.samples = 96
scene.cycles.use_denoising = True
prefs = bpy.context.preferences.addons['cycles'].preferences
try:
    prefs.compute_device_type = 'METAL'
    prefs.get_devices()
    for device in prefs.devices:
        device.use = device.type == 'METAL'
    scene.cycles.device = 'GPU' if any(d.type == 'METAL' for d in prefs.devices) else 'CPU'
except Exception:
    scene.cycles.device = 'CPU'
bpy.ops.wm.save_as_mainfile(filepath=str(SCENE))
(OUT/'reference-materials.json').write_text(json.dumps(assignments, indent=2))
bpy.ops.render.render(write_still=True)
print('RENDER_COMPLETE', IMAGE, flush=True)
