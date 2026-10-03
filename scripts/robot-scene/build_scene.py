import bpy, math, json
from mathutils import Vector, Matrix
from pathlib import Path
OUT=(Path(__file__).resolve().parents[2] / 'output' / 'robot-scene')
scene=bpy.context.scene
robot=list(scene.objects)
meshes=[o for o in robot if o.type=='MESH']
pts=[o.matrix_world @ Vector(v) for o in meshes for v in o.bound_box]
minz=min(p.z for p in pts)
pivot=Vector((-.151,-.1718,minz))
root=bpy.data.objects.new('ROBOT • motion control',None); scene.collection.objects.link(root)
root.empty_display_type='ARROWS'; root.empty_display_size=.15
for o in robot:
 if o.parent is None:
  w=o.matrix_world.copy(); o.parent=root; o.matrix_world=Matrix.Translation(-pivot)@w
bpy.context.view_layer.update()
# Separate wheel rigs, preserving the original assembly and all CAD parts.
wheels=[]
for o in robot:
 if o.name.startswith('96mm Mecanum Wheel'):
  parts=[p for p in o.children_recursive if p.type=='MESH']
  core=next((p for p in parts if p.name.startswith('Wheel Core')),None)
  if not core: continue
  ps=[core.matrix_world @ Vector(v) for v in core.bound_box]
  center=sum(ps,Vector())/8
  rig=bpy.data.objects.new('ROLL • '+o.name,None); scene.collection.objects.link(rig); rig.parent=root; rig.location=center; bpy.context.view_layer.update()
  for p in parts:
   w=p.matrix_world.copy(); p.parent=rig; p.matrix_world=w
  wheels.append(rig)
# Materials retain the CAD colors, with restrained metal response.
for m in bpy.data.materials:
 if m.use_nodes:
  bs=next((n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
  if bs:
   c=bs.inputs['Base Color'].default_value
   neutral=max(c[:3])-min(c[:3])<.04
   bs.inputs['Metallic'].default_value=.6 if neutral and c[0]>.3 else .05
   bs.inputs['Roughness'].default_value=.32 if neutral and c[0]>.3 else .46
# Smooth travel, direction change, and a two-second final hold.
poses=[(1,-1.04,0,90),(14,-.92,0,90),(68,.34,0,90),(80,.34,0,90),(116,.25,.055,-25),(144,.16,.09,-45),(192,.16,.09,-45)]
for f,x,y,a in poses:
 root.location=(x,y,.002); root.rotation_euler=(0,0,math.radians(a)); root.keyframe_insert(data_path='location',frame=f); root.keyframe_insert(data_path='rotation_euler',frame=f)
for rig in wheels:
 for f,a in [(1,0),(14,-2.5),(68,-28.75),(80,-28.75),(116,-26),(144,-24),(192,-24)]:
  rig.rotation_euler.x=a; rig.keyframe_insert(data_path='rotation_euler',frame=f)
# Matte charcoal studio floor.
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,0)); floor=bpy.context.object; floor.name='Studio floor'
mat=bpy.data.materials.new('Charcoal matte'); mat.diffuse_color=(.026,.035,.052,1); mat.use_nodes=True
bs=mat.node_tree.nodes.get('Principled BSDF'); bs.inputs['Base Color'].default_value=mat.diffuse_color; bs.inputs['Roughness'].default_value=.6
floor.data.materials.append(mat)
world=bpy.data.worlds.new('Studio ambient'); scene.world=world; world.use_nodes=True; world.node_tree.nodes['Background'].inputs[0].default_value=(.14,.18,.26,1); world.node_tree.nodes['Background'].inputs[1].default_value=.4

def aim(obj,point): obj.rotation_euler=(Vector(point)-obj.location).to_track_quat('-Z','Y').to_euler()
def area(name,loc,power,size,color):
 d=bpy.data.lights.new(name,'AREA'); d.energy=power; d.shape='DISK'; d.size=size; d.color=color
 o=bpy.data.objects.new(name,d); scene.collection.objects.link(o); o.location=loc; aim(o,(.05,0,.15))
area('Key softbox',(-.65,-.65,1.3),100,1.0,(.86,.93,1))
area('Warm rim',(.8,.65,1.0),130,.7,(1,.77,.48))
area('Front fill',(.8,-1,.6),45,.8,(.62,.79,1))
camd=bpy.data.cameras.new('Camera • 15 degree downward'); cam=bpy.data.objects.new(camd.name,camd); scene.collection.objects.link(cam)
cam.location=(0,-2.6,.19+2.6*math.tan(math.radians(15))); aim(cam,(0,0,.19)); camd.type='ORTHO'; camd.ortho_scale=1.36; camd.lens=50; scene.camera=cam
scene.render.engine='CYCLES' if False else 'CYCLES'
# EEVEE enum is discovered from this installed Blender build.
engines=[e.identifier for e in scene.render.bl_rna.properties['engine'].enum_items]
try: scene.render.engine='CYCLES' if False else 'BLENDER_EEVEE'
except: scene.render.engine='BLENDER_EEVEE_NEXT'
scene.render.resolution_x=1280; scene.render.resolution_y=720; scene.render.resolution_percentage=100
scene.render.fps=24; scene.frame_start=1; scene.frame_end=192
scene.render.image_settings.file_format='PNG'; scene.render.image_settings.color_mode='RGBA'; scene.render.film_transparent=False
scene.render.filepath=str(OUT/'frames'/'robot_')
scene.view_settings.view_transform='AgX'
for f,label in [(1,'ENTER from left'),(68,'RIGHT stop'),(80,'RETURN + turn'),(144,'HERO front-left / rear-right'),(192,'END')]: scene.timeline_markers.new(label,frame=f)
scene['Shot notes']='8 seconds / 24fps. Enters left, travels right, returns and turns to face front-left. Camera pitched downward 15 degrees. Intake is front (-Y in source).'
scene.frame_set(160)
bpy.ops.object.select_all(action='DESELECT'); root.select_set(True); bpy.context.view_layer.objects.active=root
for screen in bpy.data.screens:
 for a in screen.areas:
  if a.type=='VIEW_3D':
   a.spaces.active.region_3d.view_perspective='CAMERA'; a.spaces.active.overlay.show_overlays=False
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'robot-motion.blend'))
scene.render.filepath=str(OUT/'hero-preview.png')
scene.render.resolution_percentage=75
bpy.ops.render.render(write_still=True)
scene.render.resolution_percentage=100; scene.render.filepath=str(OUT/'frames'/'robot_')
open(OUT/'build-complete.json','w').write(json.dumps({'file':str(OUT/'robot-motion.blend'),'frame':160,'wheels':len(wheels),'min_z':minz}))
