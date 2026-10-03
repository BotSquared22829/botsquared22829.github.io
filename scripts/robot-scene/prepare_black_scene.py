"""Run in Blender with the completed two-motor scene loaded."""
import bpy,json
from pathlib import Path
out=Path(__file__).resolve().parents[2]/'output'/'robot-scene'
s=bpy.context.scene
bpy.data.objects['Studio floor'].hide_render=True
background=s.world.node_tree.nodes['Background']
background.inputs['Color'].default_value=(0,0,0,1)
background.inputs['Strength'].default_value=0
s.render.film_transparent=False
s.render.dither_intensity=0
s.frame_set(160)
s.render.image_settings.media_type='IMAGE';s.render.image_settings.file_format='PNG'
s.render.image_settings.color_mode='RGB';s.render.filepath=str(out/'black-hero-preview.png')
bpy.ops.render.render(write_still=True)
s.render.image_settings.media_type='VIDEO';s.render.image_settings.file_format='FFMPEG'
s.render.filepath=str(out/'robot-motion-black.mp4')
s.render.ffmpeg.gopsize=1
s.render.ffmpeg.max_b_frames=0
s.render.ffmpeg.use_max_b_frames=True
(out/'black-ffmpeg-settings.json').write_text(json.dumps({p.identifier:str(getattr(s.render.ffmpeg,p.identifier)) for p in s.render.ffmpeg.bl_rna.properties if p.identifier!='rna_type'},indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(out/'robot-motion-black.blend'))
