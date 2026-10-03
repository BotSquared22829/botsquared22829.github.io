import bpy,json,math
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
from pathlib import Path
out=(Path(__file__).resolve().parents[2] / 'output' / 'robot-scene')
s=bpy.context.scene; root=bpy.data.objects['ROBOT • motion control']; parts=[o for o in root.children_recursive if o.type=='MESH']
checks=[]
for f in [36,68,80,96,116,144,160,192]:
 s.frame_set(f)
 pts=[world_to_camera_view(s,s.camera,o.matrix_world@Vector(v)) for o in parts for v in o.bound_box]
 bounds=[min(p.x for p in pts),max(p.x for p in pts),min(p.y for p in pts),max(p.y for p in pts)]
 checks.append({'frame':f,'projected_bounds':bounds,'inside_frame':all(0<=v<=1 for v in bounds)})
s.frame_set(160)
forward=root.rotation_euler.to_matrix()@Vector((0,-1,0)); camera_forward=s.camera.rotation_euler.to_matrix()@Vector((0,0,-1))
result={'camera_downward_degrees':math.degrees(math.asin(-camera_forward.z)),'final_robot_facing_vector':list(forward),'checks':checks,'render':{'fps':s.render.fps,'frames':[s.frame_start,s.frame_end]}}
(out/'scene-verification.json').write_text(json.dumps(result,indent=2))
assert all(c['inside_frame'] for c in checks),result
assert abs(result['camera_downward_degrees']-15)<.001,result
assert forward.x<0 and forward.y<0,result
