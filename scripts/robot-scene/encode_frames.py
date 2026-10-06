import bpy
from pathlib import Path


def encode_frames(paths, output, all_intra=False):
    paths = [Path(path).resolve() for path in paths]
    if not paths:
        raise ValueError('At least one rendered frame is required')
    if any(not path.is_file() for path in paths):
        raise FileNotFoundError('Every input frame must exist before encoding')
    # Blender image-strip elements share the first image's directory.
    if len({path.parent for path in paths}) != 1:
        raise ValueError('All input frames must be in the same directory')
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    scene = bpy.data.scenes.new('Video encoding')
    try:
        scene.render.resolution_x = 1280
        scene.render.resolution_y = 720
        scene.render.resolution_percentage = 100
        scene.render.fps = 24
        scene.frame_start = 1
        scene.frame_end = len(paths)
        scene.view_settings.view_transform = 'Standard'
        scene.view_settings.look = 'None'
        scene.render.dither_intensity = 0
        scene.sequencer_colorspace_settings.name = 'sRGB'
        editor = scene.sequence_editor_create()
        strips = editor.strips if hasattr(editor, 'strips') else editor.sequences
        strip = strips.new_image('Robot animation', str(paths[0]), channel=1, frame_start=1)
        for path in paths[1:]:
            strip.elements.append(path.name)
        strip.frame_final_duration = len(paths)
        scene.render.image_settings.media_type = 'VIDEO'
        scene.render.image_settings.file_format = 'FFMPEG'
        scene.render.ffmpeg.format = 'MPEG4'
        scene.render.ffmpeg.codec = 'H264'
        scene.render.ffmpeg.constant_rate_factor = 'HIGH'
        scene.render.ffmpeg.ffmpeg_preset = 'GOOD'
        scene.render.image_settings.color_mode = 'RGB'
        scene.render.filepath = str(output)
        if all_intra:
            scene.render.ffmpeg.gopsize = 1
            scene.render.ffmpeg.use_max_b_frames = True
            scene.render.ffmpeg.max_b_frames = 0
        result = bpy.ops.render.render(animation=True, scene=scene.name)
        if 'FINISHED' not in result:
            raise RuntimeError('Video encoding was cancelled')
    finally:
        bpy.data.scenes.remove(scene)


if __name__ == '__main__':
    out = Path(__file__).resolve().parents[2] / 'output' / 'robot-scene'
    encode_frames([out / 'hero-dark-preview.png'] * 2, out / 'encoding-check.mp4')
