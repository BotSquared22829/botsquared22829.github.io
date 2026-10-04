"""Apply red polymer to the Robot V5 fan slot and both claw fingers, then render."""
import bpy
import json
import shutil
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / 'output/robot-scene/firetruck-v5'
SCENE = OUT / 'robot-v5-studio.blend'
IMAGE = OUT / 'robot-v5-studio.png'
bpy.ops.wm.open_mainfile(filepath=str(SCENE))

# Verified against the imported part bounds: the front fan slot and upper fingers.
# The separate blue chassis insert named "Part 1" keeps its original material.
PARTS = {'Part 1.001': 'Fan slot', 'Part 1.002': 'Claw finger right',
         'Part 1.003': 'Claw finger left'}
for name in PARTS:
    assert name in bpy.data.objects and bpy.data.objects[name].type == 'MESH', name

mat = bpy.data.materials.get('Printed polymer | BotSquared red')
if mat is None:
    mat = bpy.data.materials.new('Printed polymer | BotSquared red')
mat.use_nodes = True
bs = mat.node_tree.nodes.get('Principled BSDF')
# Saturated, nonmetallic red with a satin printed-polymer finish.
color = (.52, .009, .014, 1)
mat.diffuse_color = color
bs.inputs['Base Color'].default_value = color
bs.inputs['Metallic'].default_value = 0
bs.inputs['Roughness'].default_value = .4
for name, label in PARTS.items():
    obj = bpy.data.objects[name]
    # Material slots are object-linked to avoid touching any shared CAD mesh.
    for slot in obj.material_slots:
        slot.link = 'OBJECT'
        slot.material = mat
    obj['Printed part'] = label
    obj['Finish'] = 'Red polymer'

scene = bpy.context.scene
scene['Printed parts finish'] = 'Red fan slot and both claw fingers'
scene.render.resolution_percentage = 100
scene.cycles.samples = 96
scene.cycles.use_denoising = True
scene.render.filepath = str(IMAGE)
prefs = bpy.context.preferences.addons['cycles'].preferences
try:
    prefs.compute_device_type = 'METAL'
    prefs.get_devices()
    for device in prefs.devices:
        device.use = device.type == 'METAL'
    scene.cycles.device = 'GPU' if any(d.type == 'METAL' for d in prefs.devices) else 'CPU'
except Exception:
    scene.cycles.device = 'CPU'

backup = OUT / 'robot-v5-studio-before-red.png'
if IMAGE.exists() and not backup.exists():
    shutil.copy2(IMAGE, backup)
bpy.ops.wm.save_as_mainfile(filepath=str(SCENE))
(OUT/'red-printed-parts.json').write_text(json.dumps(PARTS, indent=2))
bpy.ops.render.render(write_still=True)
print('RENDER_COMPLETE', IMAGE, flush=True)
