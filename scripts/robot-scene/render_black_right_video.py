import bpy,json,time,sys,traceback,shutil
from pathlib import Path
OUT=(Path(__file__).resolve().parents[2] / 'output' / 'robot-scene')
sys.path.insert(0,str(Path(__file__).resolve().parent));from encode_frames import encode_frames
s=bpy.context.scene;s.render.dither_intensity=0
started=time.time(); frames=OUT/'black-right-clean-frames';frames.mkdir(exist_ok=True)

# Verify every fully entered frame fits the camera before the expensive render.
import numpy as np
root=bpy.data.objects['ROBOT • motion control']
parts=[o for o in root.children_recursive if o.type=='MESH']
corners=np.array([[list(v)+[1] for v in o.bound_box] for o in parts])
checks=[]
for frame in range(28,145):
 s.frame_set(frame);bpy.context.view_layer.update()
 matrices=np.array([s.camera.matrix_world.inverted()@o.matrix_world for o in parts])
 camera_points=np.einsum('oij,okj->oki',matrices,corners)
 xy=camera_points[:,:,:2]/np.array([s.camera.data.ortho_scale,s.camera.data.ortho_scale*s.render.resolution_y/s.render.resolution_x])+.5
 lo=xy.min(axis=(0,1));hi=xy.max(axis=(0,1))
 assert np.all(lo>=0) and np.all(hi<=1),(frame,lo.tolist(),hi.tolist())
 checks.append({'frame':frame,'min':lo.tolist(),'max':hi.tolist()})
(OUT/'black-right-full-framing.json').write_text(json.dumps(checks))

try:
 s.render.image_settings.media_type='IMAGE';s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGB';s.render.image_settings.compression=15
 s.render.filepath=str(frames/'robot_');s.render.use_overwrite=False;s.frame_start=1;s.frame_end=144
 def progress(scene,*args):
  (OUT/'black-right-render-progress.json').write_text(json.dumps({'stage':'render','frame':scene.frame_current,'last_rendered_frame':144,'elapsed_seconds':round(time.time()-started,1)}))
  if scene.frame_current==68:
   for f in range(69,81):shutil.copyfile(scene.render.frame_path(frame=68),scene.render.frame_path(frame=f))
 bpy.app.handlers.render_write.append(progress)
 bpy.ops.render.render(animation=True)
 bpy.app.handlers.render_write.remove(progress)
 paths=[Path(s.render.frame_path(frame=f)) for f in range(1,145)]
 assert all(p.exists() for p in paths)
 (OUT/'black-right-render-progress.json').write_text(json.dumps({'stage':'encoding','frames':192,'elapsed_seconds':round(time.time()-started,1)}))
 encode_frames(paths+[paths[-1]]*48,OUT/'robot-motion-black-right.mp4',all_intra=True)
 from faststart_mp4 import faststart
 faststart(OUT/'robot-motion-black-right.mp4')
 shutil.copyfile(paths[-1],OUT/'hero-black-right-preview.png')
 s.frame_end=192;s.frame_set(160);s.render.use_overwrite=True
 s.render.image_settings.media_type='VIDEO';s.render.image_settings.file_format='FFMPEG';s.render.filepath=str(OUT/'robot-motion-black-right.mp4')
 for screen in bpy.data.screens:
  for area in screen.areas:
   if area.type=='CONSOLE':area.type='VIEW_3D'
   if area.type=='VIEW_3D':
    for space in area.spaces:
     if space.type=='VIEW_3D':
      space.region_3d.view_perspective='CAMERA';space.overlay.show_overlays=False
 bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'robot-motion-black-right.blend'))
 (OUT/'black-right-video-complete.json').write_text(json.dumps({'frames':192,'fps':24,'seconds':8,'resolution':[1280,720],'elapsed_seconds':round(time.time()-started,1)}))
except Exception:
 (OUT/'black-right-render-error.txt').write_text(traceback.format_exc());raise
