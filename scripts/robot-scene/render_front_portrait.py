"""Front-facing studio portrait, derived from the final black-right video scene.

Run with Blender --background --python this_file.py [-- --final].
"""
import bpy
import math
import sys
import json
from pathlib import Path
from mathutils import Vector

OUT = Path(__file__).resolve().parents[2] / 'output' / 'robot-scene'
FINAL = '--final' in sys.argv
bpy.ops.wm.open_mainfile(filepath=str(OUT / 'robot-motion-black-right.blend'))
s = bpy.context.scene
s.frame_set(160)
root = bpy.data.objects['ROBOT • motion control']
root.animation_data_clear()
root.location.x = 0
root.location.y = 0
root.rotation_euler = (0, 0, 0)
for o in root.children_recursive:
    o.animation_data_clear()
bpy.context.view_layer.update()
for o in list(s.objects):
    if o.type in {'LIGHT', 'CAMERA'} or o.name == 'Studio floor':
        bpy.data.objects.remove(o, do_unlink=True)

def material(name, color, roughness=.5, metallic=0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bs = m.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value = (*color, 1)
    bs.inputs['Roughness'].default_value = roughness
    bs.inputs['Metallic'].default_value = metallic
    return m

def cube(name, loc, size, mat):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = size
    o.data.materials.append(mat)
    return o

# Concrete is entirely procedural: mottling, aggregate, and fine pores.
concrete = material('Architectural concrete • fine aggregate', (.075,)*3, .67)
n = concrete.node_tree.nodes
l = concrete.node_tree.links
bs = n.get('Principled BSDF')
tex = n.new('ShaderNodeTexCoord')
coarse = n.new('ShaderNodeTexNoise'); coarse.inputs['Scale'].default_value=4.8
coarse.inputs['Detail'].default_value=5; coarse.inputs['Roughness'].default_value=.75
l.new(tex.outputs['Object'], coarse.inputs['Vector'])
ramp = n.new('ShaderNodeValToRGB')
ramp.color_ramp.elements[0].position=.18; ramp.color_ramp.elements[0].color=(.027,.027,.027,1)
ramp.color_ramp.elements[1].position=.82; ramp.color_ramp.elements[1].color=(.13,.13,.13,1)
l.new(coarse.outputs['Fac'],ramp.inputs[0]); l.new(ramp.outputs[0],bs.inputs['Base Color'])
grain = n.new('ShaderNodeTexNoise'); grain.inputs['Scale'].default_value=650
grain.inputs['Detail'].default_value=3
l.new(tex.outputs['Object'],grain.inputs['Vector'])
bump = n.new('ShaderNodeBump'); bump.inputs['Strength'].default_value=.5; bump.inputs['Distance'].default_value=.0015
l.new(grain.outputs['Fac'],bump.inputs['Height']); l.new(bump.outputs['Normal'],bs.inputs['Normal'])
bpy.ops.mesh.primitive_plane_add(size=200, location=(0,0,-.001))
floor=bpy.context.object; floor.name='Concrete floor'; floor.data.materials.append(concrete)
wall = material('Black room • light absorbing', (.002,)*3, .94)
cube('Black rear wall', (0,2,1.5), (8,.05,3),wall)
cube('Black left wall', (-3,0,1.5), (.05,6,3),wall)
cube('Black right wall', (3,0,1.5), (.05,6,3),wall)

def aim(o, target):
    o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()

def light(name, loc, target, power, size, shape='DISK', height=None):
    d=bpy.data.lights.new(name,'AREA'); d.energy=power; d.color=(1,1,1)
    d.shape=shape; d.size=size
    if height is not None: d.size_y=height
    o=bpy.data.objects.new(name,d); s.collection.objects.link(o); o.location=loc; aim(o,target)
    return o

light('White key • tall softbox',(-.7,-.65,.85),(0,0,.2),28,.4,'RECTANGLE',.8)
light('White edge • right',( .55,.15,.65),(0,0,.23),40,.18,'RECTANGLE',.7)
light('White edge • left',(-.6,.2,.55),(0,0,.22),30,.16,'RECTANGLE',.6)
light('Top strip • steel highlights',(0,.1,1.15),(0,0,0),20,.65,'RECTANGLE',.14)
light('Subtle frontal detail',( .15,-1,.45),(0,0,.2),2,.7)

# Smoothly bounded, turbulent volume banks. They sit behind the assembly,
# with a thin layer of drifting fog around its base.
def smoke(name, loc, size, density, seed):
    m=bpy.data.materials.new(name); m.use_nodes=True
    n=m.node_tree.nodes; n.clear(); l=m.node_tree.links
    out=n.new('ShaderNodeOutputMaterial')
    vol=n.new('ShaderNodeVolumePrincipled')
    vol.inputs['Color'].default_value=(.82,.82,.82,1)
    vol.inputs['Anisotropy'].default_value=.2
    l.new(vol.outputs['Volume'],out.inputs['Volume'])
    tex=n.new('ShaderNodeTexCoord')
    sub=n.new('ShaderNodeVectorMath'); sub.operation='SUBTRACT'; sub.inputs[1].default_value=(.5,.5,.5)
    l.new(tex.outputs['Generated'],sub.inputs[0])
    length=n.new('ShaderNodeVectorMath'); length.operation='LENGTH'; l.new(sub.outputs[0],length.inputs[0])
    edge=n.new('ShaderNodeMapRange'); edge.clamp=True
    edge.inputs['From Min'].default_value=.15; edge.inputs['From Max'].default_value=.5
    edge.inputs['To Min'].default_value=1; edge.inputs['To Max'].default_value=0
    l.new(length.outputs['Value'],edge.inputs[0])
    noise=n.new('ShaderNodeTexNoise'); noise.noise_dimensions='4D'
    noise.inputs['Scale'].default_value=5; noise.inputs['Detail'].default_value=5
    noise.inputs['Roughness'].default_value=.72; noise.inputs['Distortion'].default_value=2
    noise.inputs['W'].default_value=seed
    l.new(tex.outputs['Generated'],noise.inputs['Vector'])
    ramp=n.new('ShaderNodeMapRange'); ramp.clamp=True
    ramp.inputs['From Min'].default_value=.48; ramp.inputs['From Max'].default_value=.75
    ramp.inputs['To Min'].default_value=0; ramp.inputs['To Max'].default_value=density
    l.new(noise.outputs['Fac'],ramp.inputs[0])
    mul=n.new('ShaderNodeMath'); mul.operation='MULTIPLY'
    l.new(ramp.outputs[0],mul.inputs[0]); l.new(edge.outputs[0],mul.inputs[1])
    l.new(mul.outputs[0],vol.inputs['Density'])
    return cube(name,loc,size,m)

smoke('Smoke • rising left',(-.43,.5,.2),(1.15,.6,.6),4,1.7)
smoke('Smoke • rising right',(.46,.58,.24),(1.1,.65,.7),4.8,4.1)
smoke('Smoke • floor drift',(0,.05,.04),(2,1.2,.13),1.25,7.2)
smoke('Smoke • left foreground curl',(-.46,-.28,.06),(.7,.65,.2),1.8,9.4)
smoke('Smoke • right foreground curl',(.5,-.18,.07),(.7,.6,.23),2,12.3)

world=bpy.data.worlds.new('Black room atmosphere'); world.use_nodes=True; s.world=world
world.node_tree.nodes['Background'].inputs['Color'].default_value=(.015,.015,.015,1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value=.08
d=bpy.data.cameras.new('Front portrait • 60mm'); cam=bpy.data.objects.new(d.name,d)
s.collection.objects.link(cam); s.camera=cam
cam.location=(0,-1.45,.28); aim(cam,(0,0,.15)); d.type='PERSP'; d.lens=60
d.clip_start=.01; d.clip_end=100
s.render.engine='CYCLES'
s.cycles.samples=128 if FINAL else 32
s.cycles.use_adaptive_sampling=True
s.cycles.adaptive_threshold=.035
s.cycles.use_denoising=True
s.cycles.max_bounces=8; s.cycles.volume_bounces=2
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type='METAL'; prefs.get_devices()
    for device in prefs.devices: device.use=device.type=='METAL'
    if any(device.type=='METAL' for device in prefs.devices): s.cycles.device='GPU'
except Exception as e:
    print('Using CPU:',e)
s.render.resolution_x=2400; s.render.resolution_y=1600
s.render.resolution_percentage=100 if FINAL else 40
s.render.image_settings.media_type='IMAGE'; s.render.image_settings.file_format='PNG'
s.render.image_settings.color_mode='RGB'; s.render.image_settings.color_depth='16'
s.render.film_transparent=False; s.render.dither_intensity=1
s.view_settings.view_transform='AgX'; s.view_settings.look='AgX - Medium High Contrast'
s.view_settings.exposure=-1.65
s.render.filepath=str(OUT/('robot-front-premium.png' if FINAL else 'robot-front-premium-preview.png'))
s['Portrait source']='robot-motion-black-right.blend; exact assembly from latest video'
s['Art direction']='Centered front view. Black room, procedural concrete, white studio lights, turbulent smoke.'
s.frame_start=160; s.frame_end=160
for screen in bpy.data.screens:
    for a in screen.areas:
        if a.type=='VIEW_3D':
            a.spaces.active.region_3d.view_perspective='CAMERA'
            a.spaces.active.overlay.show_overlays=False
if FINAL:
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'robot-front-premium.blend'))
bpy.ops.render.render(write_still=True)
(OUT/('front-portrait-final.json' if FINAL else 'front-portrait-preview.json')).write_text(json.dumps({'source':'robot-motion-black-right.blend','image':s.render.filepath,'device':s.cycles.device,'samples':s.cycles.samples}))
