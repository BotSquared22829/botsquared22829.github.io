import bpy,json
from mathutils import Matrix,Vector
from pathlib import Path
out=(Path(__file__).resolve().parents[2] / 'output' / 'robot-scene')
s=bpy.context.scene;s.frame_set(160);bpy.context.view_layer.update()
root=bpy.data.objects['ROBOT • motion control'];inv=root.matrix_world.inverted()
def bounds(o):
 pts=[inv@o.matrix_world@Vector(v) for v in o.bound_box]
 return [[min(p[i] for p in pts),max(p[i] for p in pts)] for i in range(3)]
panels=[bpy.data.objects[n] for n in ['Part 1','Part 1.015']]
centre=sum(sum(bounds(o)[0])/2 for o in panels)/2
mirror=Matrix.Diagonal((-1,1,1,1));mirror[0][3]=2*centre
assembly=bpy.data.objects.new('ADDED • opposite side motor assembly',None)
s.collection.objects.link(assembly);assembly.parent=root;assembly.matrix_parent_inverse=Matrix.Identity(4)
names=['6000rpm Motor - Bare (GB)','Part 1.027','1501 Series M4 x 0.7mm Standoff (6mm OD, 16mm Length) 1501-0006-0160','1501 Series M4 x 0.7mm Standoff (6mm OD, 16mm Length) 1501-0006-0160.001','2mm Pitch GT2 Pinion Timing Pulley (6mm Bore, 20 Tooth)  3422-0006-0020']
added=[]
for name in names:
 src=bpy.data.objects[name];o=src.copy();o.name='ADDED • '+name;o.animation_data_clear();s.collection.objects.link(o)
 o.parent=assembly;o.matrix_parent_inverse=Matrix.Identity(4);o.matrix_basis=mirror@inv@src.matrix_world
 added.append((src,o))
bpy.context.view_layer.update()
report={'reflection_centre_x_m':centre,'parts':[]}
for src,o in added:
 a=bounds(src);b=bounds(o)
 assert abs(b[0][0]-(2*centre-a[0][1]))<1e-6
 assert abs(b[0][1]-(2*centre-a[0][0]))<1e-6
 report['parts'].append({'source':src.name,'added':o.name,'source_bounds':a,'added_bounds':b})
(out/'two-motors-verification.json').write_text(json.dumps(report,indent=2))
s.render.image_settings.media_type='IMAGE';s.render.image_settings.file_format='PNG';s.render.filepath=str(out/'two-motors-side-preview.png')
s.frame_set(68);bpy.ops.render.render(write_still=True)
s.frame_set(160);s.render.filepath=str(out/'two-motors-hero-preview.png');bpy.ops.render.render(write_still=True)
s.render.image_settings.media_type='VIDEO';s.render.image_settings.file_format='FFMPEG';s.render.filepath=str(out/'robot-motion-two-motors.mp4')
bpy.ops.wm.save_as_mainfile(filepath=str(out/'robot-motion-two-motors.blend'))
