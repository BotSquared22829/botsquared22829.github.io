"""Exercise encoder failure paths without starting Blender or creating media."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch


class EncodeFramesTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.frame = self.root / 'frame.png'
        self.frame.write_bytes(b'fixture')
        self.bpy = MagicMock()
        spec = importlib.util.spec_from_file_location(
            'encode_frames', Path(__file__).parents[1] / 'robot-scene/encode_frames.py')
        self.encoder = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'bpy': self.bpy}):
            spec.loader.exec_module(self.encoder)

    def test_rejects_missing_and_mixed_directory_frames_before_creating_scene(self):
        with self.assertRaises(ValueError):
            self.encoder.encode_frames([], self.root / 'out.mp4')
        with self.assertRaises(FileNotFoundError):
            self.encoder.encode_frames([self.root / 'missing.png'], self.root / 'out.mp4')
        other = self.root / 'other/frame.png'
        other.parent.mkdir()
        other.write_bytes(b'fixture')
        with self.assertRaises(ValueError):
            self.encoder.encode_frames([self.frame, other], self.root / 'out.mp4')
        self.bpy.data.scenes.new.assert_not_called()

    def test_always_removes_temporary_scene_when_encoding_fails(self):
        self.bpy.ops.render.render.side_effect = RuntimeError('Encoder failed')
        with self.assertRaisesRegex(RuntimeError, 'Encoder failed'):
            self.encoder.encode_frames([self.frame], self.root / 'out.mp4')
        self.bpy.data.scenes.remove.assert_called_once_with(self.bpy.data.scenes.new.return_value)

    def test_cancellation_is_not_reported_as_success(self):
        self.bpy.ops.render.render.return_value = {'CANCELLED'}
        with self.assertRaisesRegex(RuntimeError, 'cancelled'):
            self.encoder.encode_frames([self.frame], self.root / 'out.mp4')
        self.bpy.data.scenes.remove.assert_called_once()

    def test_repeated_hold_frames_keep_scroll_encoding_settings(self):
        self.bpy.ops.render.render.return_value = {'FINISHED'}
        self.encoder.encode_frames([self.frame, self.frame], self.root / 'out.mp4', all_intra=True)
        scene = self.bpy.data.scenes.new.return_value
        self.assertEqual(scene.frame_end, 2)
        self.assertEqual(scene.render.ffmpeg.gopsize, 1)
        self.assertEqual(scene.render.ffmpeg.max_b_frames, 0)
        self.bpy.data.scenes.remove.assert_called_once_with(scene)


if __name__ == '__main__':
    unittest.main()
