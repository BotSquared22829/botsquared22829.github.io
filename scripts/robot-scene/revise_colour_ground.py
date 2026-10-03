import bpy,math,json,numpy as np
from mathutils import Vector
from pathlib import Path
OUT=(Path(__file__).resolve().parents[2] / 'output' / 'robot-scene')
s=bpy.context.scene;root=bpy.data.objects['ROBOT • motion control']
# Interpret the CAD swatches to match the supplied display-space references.
def linear(v): return v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4
for m in bpy.data.materials:
 try: rgb=[float(v) for v in m.name.split('_')[:3]]
 except: continue
 if len(rgb)!=3: continue
 bs=next((n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
 if not bs:continue
 neutral=max(rgb)-min(rgb)<.045
 c=tuple(linear(v) for v in rgb)
 bs.inputs['Base Color'].default_value=(*c,1)
 bs.inputs['Metallic'].default_value=.42 if neutral and rgb[0]>.4 else .04
 bs.inputs['Roughness'].default_value=.48 if neutral and rgb[0]>.4 else .57
 m.diffuse_color=(*c,1)
# More saturated yellow game pieces, and near-black rubber.
for o in root.children_recursive:
 if o.type!='MESH':continue
 for m in o.data.materials:
  bs=next((n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
  if not bs:continue
  if 'Pollen' in o.name:
   bs.inputs['Base Color'].default_value=(.85,.70,.008,1);bs.inputs['Roughness'].default_value=.4;bs.inputs['Metallic'].default_value=0
  if any(k in o.name for k in ['Gecko','Roller Cover','Wheel Core']):
   bs.inputs['Base Color'].default_value=(.018,.018,.018,1);bs.inputs['Roughness'].default_value=.68;bs.inputs['Metallic'].default_value=0
# Place nominal 96-mm drive wheels on z=0. The previous CAD bounding box
# overestimated the tyre radius, causing a 27-mm clearance.
rigs=[o for o in s.objects if o.name.startswith('ROLL')]
axis_local_z=sum(r.location.z for r in rigs)/len(rigs)
root_z=.048-axis_local_z
for f in [1,14,68,80,116,144,192]:
 s.frame_set(f);root.location.z=root_z;root.keyframe_insert(data_path='location',index=2,frame=f)
# Integrate the wheel travel from the animated chassis movement, including turn.
prev={}; angles={r.name:0. for r in rigs}
for r in rigs:r.animation_data_clear()
prev_yaw=None
for f in range(1,193):
 s.frame_set(f);bpy.context.view_layer.update(); yaw=root.rotation_euler.z
 for r in rigs:
  pos=r.matrix_world.translation.copy()
  if r.name in prev:
   d=pos-prev[r.name]; mid=(yaw+prev_yaw)/2
   dx=math.cos(mid)*d.x+math.sin(mid)*d.y;dy=-math.sin(mid)*d.x+math.cos(mid)*d.y
   sign=1 if 'Right Slant' in r.name else -1
   angles[r.name]+=(-dy+sign*dx)/.048
  r.rotation_euler.x=angles[r.name];r.keyframe_insert(data_path='rotation_euler',index=0,frame=f)
  prev[r.name]=pos
 prev_yaw=yaw
# Keep the decorative game pieces just clear of the plane too.
s.frame_set(160);bpy.context.view_layer.update();cache={}
def verts(mesh):
 if mesh.name not in cache:
  arr=np.empty(len(mesh.vertices)*3,dtype=np.float32);mesh.vertices.foreach_get('co',arr);cache[mesh.name]=arr.reshape(-1,3)
 return cache[mesh.name]
def zmin(o):return float((verts(o.data)@np.array(o.matrix_world[2][:3])+o.matrix_world[2][3]).min())
for o in root.children_recursive:
 if o.type=='MESH' and 'Pollen' in o.name and zmin(o)<.0001:
  w=o.matrix_world.copy();w.translation.z+=.0001-zmin(o);o.matrix_world=w
# Neutral controlled lighting on an almost-black matte studio.
floor=bpy.data.objects['Studio floor'];bs=floor.data.materials[0].node_tree.nodes.get('Principled BSDF')
bs.inputs['Base Color'].default_value=(.0012,.0012,.0012,1);bs.inputs['Roughness'].default_value=.92;bs.inputs['Specular IOR Level'].default_value=.12
bg=s.world.node_tree.nodes['Background'];bg.inputs[0].default_value=(.015,.015,.015,1);bg.inputs[1].default_value=.12
for name,power,size in [('Key softbox',38,.8),('Warm rim',48,.55),('Front fill',15,.9)]:
 light=bpy.data.objects[name].data;light.energy=power;light.size=size;light.color=(1,1,1)
s.view_settings.exposure=-.3
s.eevee.taa_render_samples=64
s.render.image_settings.media_type='IMAGE';s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGB'
s.render.resolution_percentage=100;s.render.filepath=str(OUT/'hero-dark-preview.png')
bpy.ops.render.render(write_still=True)
checks=[]
for f in [1,36,68,96,116,144,160,192]:
 s.frame_set(f);bpy.context.view_layer.update()
 wheels=[]
 for r in rigs:
  lows=[zmin(o) for o in r.children if o.type=='MESH' and o.name.startswith('Roller Cover')]
  wheels.append(min(lows))
 checks.append({'frame':f,'tyre_minimum_z_m':wheels})
s.frame_set(160)
(OUT/'grounding-verification.json').write_text(json.dumps({'root_z_m':root_z,'tyre_checks':checks},indent=2))
s.render.image_settings.media_type='VIDEO';s.render.image_settings.file_format='FFMPEG';s.render.filepath=str(OUT/'robot-motion-dark.mp4');s.frame_end=192
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'robot-motion-dark.blend'))
