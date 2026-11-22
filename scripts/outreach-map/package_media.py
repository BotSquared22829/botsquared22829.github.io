"""Encode both directions of the flight and package matching static chapters."""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

ASSETS = Path(__file__).resolve().parents[2] / 'assets'


def encode_video(folder, camera, output):
    last = camera['last']
    fps = camera['fps']
    # Scrolling up can play natively even on devices without negative playback rates.
    # Both halves use the same camera samples and share the turnaround frame.
    with tempfile.TemporaryDirectory() as sequence:
        for index in range(2 * last + 1):
            source = folder / f'{min(index, 2 * last - index):04d}.jpg'
            (Path(sequence) / f'{index:04d}.jpg').symlink_to(source.resolve(strict=True))
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-xerror', '-y',
                        '-framerate', str(fps), '-i', str(Path(sequence) / '%04d.jpg'),
                        '-an', '-c:v', 'libx264', '-preset', 'medium', '-crf', '20',
                        '-pix_fmt', 'yuv420p', '-g', str(fps // 2), '-sc_threshold', '0',
                        '-metadata', 'comment=Killarney entrance photograph by Arnold C (Wikimedia Commons). '
                                     'City of Vancouver open data, modified Copernicus Sentinel data, and NASA imagery.',
                        '-movflags', '+faststart', str(output)], check=True)


def package(frames, projections, output):
    output.mkdir(parents=True, exist_ok=True)
    cameras = {}
    for fmt in ('wide', 'portrait'):
        folder = frames / fmt
        cameras[fmt] = json.loads((projections / fmt / 'camera.json').read_text())
        for name in ('school', 'sister', 'metro', 'canada', 'world'):
            frame = cameras[fmt]['stops'][name]
            suffix = '-portrait' if fmt == 'portrait' else ''
            with Image.open(folder / f'{frame:04d}.jpg') as still:
                still.save(output / f'{name}{suffix}.webp', quality=91, method=6)
        encode_video(folder, cameras[fmt], output / f'{fmt}.mp4')
    (output / 'cameras.js').write_text('// Generated from the two Blender cameras.\nconst outreachMapCameras = ' +
                                       json.dumps(cameras, separators=(',', ':')) + ';\n')
    for src, dest in [('sponsor-knotbot.png','knotbot.webp'), ('ftc-news-logo.png','ftc-news.webp')]:
        with Image.open(ASSETS / src) as image:
            image.thumbnail((144, 144), Image.Resampling.LANCZOS)
            image.save(output / dest, quality=90, method=6)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('frames', type=Path)
    parser.add_argument('--projections', type=Path, help='Separate camera-only output, if used')
    args = parser.parse_args()
    destination = ASSETS / 'outreach-map'
    destination.mkdir(parents=True, exist_ok=True)
    # Finish both encodes before replacing a working site's media.
    with tempfile.TemporaryDirectory(dir=destination) as staging:
        package(args.frames, args.projections or args.frames, Path(staging))
        for asset in Path(staging).iterdir():
            asset.replace(destination / asset.name)
