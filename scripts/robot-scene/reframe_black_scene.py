"""Keep entry fully off-screen and move the final robot toward the right edge."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
out=Path(__file__).resolve().parents[2]/'output'/'robot-scene'
s=bpy.context.scene;root=bpy.data.objects['ROBOT • motion control']
parts=[o for o in root.children_recursive if o.type=='MESH']
def bounds(frame):
 s.frame_set(frame);bpy.context.view_layer.update()
 pts=[world_to_camera_view(s,s.camera,o.matrix_world@Vector(v)) for o in parts for v in o.bound_box]
 return [min(v.x for v in pts),max(v.x for v in pts),min(v.y for v in pts),max(v.y for v in pts)]
before_start=bounds(1)
root.location.x+=(-.03-before_start[1])*s.camera.data.ortho_scale
root.keyframe_insert(data_path='location',index=0,frame=1)
before_end=bounds(144)
shift=(.94-before_end[1])*s.camera.data.ortho_scale
for frame,weight in [(116,.65),(144,1),(192,1)]:
 s.frame_set(frame);root.location.x+=shift*weight;root.keyframe_insert(data_path='location',index=0,frame=frame)
# Reintegrate wheel rotation to match the revised travel.
rigs=[o for o in s.objects if o.name.startswith('ROLL')]
prev={};angles={r.name:0. for r in rigs};prev_yaw=None
for r in rigs:r.animation_data_clear()
for frame in range(1,193):
 s.frame_set(frame);bpy.context.view_layer.update();yaw=root.rotation_euler.z
 for r in rigs:
  pos=r.matrix_world.translation.copy()
  if r.name in prev:
   d=pos-prev[r.name];mid=(yaw+prev_yaw)/2
   dx=math.cos(mid)*d.x+math.sin(mid)*d.y;dy=-math.sin(mid)*d.x+math.cos(mid)*d.y
   sign=1 if 'Right Slant' in r.name else -1
   angles[r.name]+=(-dy+sign*dx)/.048
  r.rotation_euler.x=angles[r.name];r.keyframe_insert(data_path='rotation_euler',index=0,frame=frame)
  prev[r.name]=pos
 prev_yaw=yaw
checks={str(f):bounds(f) for f in [1,14,36,68,80,96,116,144,160,192]}
assert checks['1'][1]<0,checks
assert checks['144'][1]>.90 and checks['144'][1]<.98,checks
assert checks['144']==checks['192'],checks
(out/'black-right-framing.json').write_text(json.dumps({'before_start':before_start,'before_end':before_end,'final_shift_m':shift,'after':checks},indent=2))
s.render.image_settings.media_type='IMAGE';s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGB'
for frame,name in [(1,'black-right-opening.png'),(144,'black-right-hero.png')]:
 s.frame_set(frame);s.render.filepath=str(out/name);bpy.ops.render.render(write_still=True)
s.frame_set(160);s.render.image_settings.media_type='VIDEO';s.render.image_settings.file_format='FFMPEG';s.render.filepath=str(out/'robot-motion-black-right.mp4')
bpy.ops.wm.save_as_mainfile(filepath=str(out/'robot-motion-black-right.blend'))
