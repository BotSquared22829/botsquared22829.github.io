import bpy,json,time,sys,traceback,shutil
from pathlib import Path
OUT=(Path(__file__).resolve().parents[2] / 'output' / 'robot-scene')
sys.path.insert(0,str(Path(__file__).resolve().parent));from encode_frames import encode_frames
s=bpy.context.scene; started=time.time(); frames=OUT/'two-motors-frames';frames.mkdir(parents=True,exist_ok=True)
try:
 s.render.image_settings.media_type='IMAGE';s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGB';s.render.image_settings.compression=15
 s.render.filepath=str(frames/'robot_');s.render.use_overwrite=False;s.frame_start=1;s.frame_end=144
 def progress(scene,*args):
  (OUT/'two-motors-render-progress.json').write_text(json.dumps({'stage':'render','frame':scene.frame_current,'last_rendered_frame':144,'elapsed_seconds':round(time.time()-started,1)}))
  if scene.frame_current==68:
   for f in range(69,81):shutil.copyfile(scene.render.frame_path(frame=68),scene.render.frame_path(frame=f))
 bpy.app.handlers.render_write.append(progress)
 try:
  result=bpy.ops.render.render(animation=True)
  if 'FINISHED' not in result:raise RuntimeError('Frame rendering was cancelled')
 finally:
  bpy.app.handlers.render_write.remove(progress)
 paths=[Path(s.render.frame_path(frame=f)) for f in range(1,145)]
 assert all(p.exists() for p in paths)
 (OUT/'two-motors-render-progress.json').write_text(json.dumps({'stage':'encoding','frames':192,'elapsed_seconds':round(time.time()-started,1)}))
 encode_frames(paths+[paths[-1]]*48,OUT/'robot-motion-two-motors.mp4')
 shutil.copyfile(paths[-1],OUT/'hero-two-motors-preview.png')
 s.frame_end=192;s.frame_set(160);s.render.use_overwrite=True
 s.render.image_settings.media_type='VIDEO';s.render.image_settings.file_format='FFMPEG';s.render.filepath=str(OUT/'robot-motion-two-motors.mp4')
 for screen in bpy.data.screens:
  for area in screen.areas:
   if area.type=='CONSOLE':area.type='VIEW_3D'
   if area.type=='VIEW_3D':
    for space in area.spaces:
     if space.type=='VIEW_3D':
      space.region_3d.view_perspective='CAMERA';space.overlay.show_overlays=False
 bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'robot-motion-two-motors.blend'))
 (OUT/'two-motors-video-complete.json').write_text(json.dumps({'frames':192,'fps':24,'seconds':8,'resolution':[1280,720],'elapsed_seconds':round(time.time()-started,1)}))
except Exception:
 (OUT/'two-motors-render-error.txt').write_text(traceback.format_exc());raise
