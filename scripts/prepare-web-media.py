"""Generate the published media from the original images and robot renders."""

from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from PIL import Image


ASSETS = Path(__file__).resolve().parents[1] / 'assets'


def webp(output, filename, widths=(), *, quality=86, lossless=False):
    source = ASSETS / filename
    with Image.open(source) as original:
        options = {'quality': quality, 'method': 6, 'lossless': lossless}
        if original.info.get('icc_profile'):
            options['icc_profile'] = original.info['icc_profile']
        image = original.convert('RGBA' if original.has_transparency_data else 'RGB')
        if not widths:
            image.save(output / f'{source.stem}.webp', **options)
        for width in widths:
            height = round(image.height * width / image.width)
            resized = image.resize((width, height), Image.Resampling.LANCZOS)
            resized.save(output / f'{source.stem}-{width}.webp', **options)


def about_video(output):
    subprocess.run([
        'ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error', '-y',
        '-i', str(ASSETS / 'about-robot.mp4'), '-an', '-c:v', 'libx264', '-preset', 'medium',
        '-crf', '20', '-pix_fmt', 'yuv420p', '-g', '6',
        '-sc_threshold', '0', '-color_range', 'tv', '-colorspace', 'bt709',
        '-color_primaries', 'bt709', '-color_trc', 'bt709', '-movflags', '+faststart',
        str(output / 'about-robot-web.mp4'),
    ], check=True)


def prepare_media(output):
    webp(output, 'botsquared-logo.png', (96, 288), lossless=True)
    webp(output, 'first-tech-challenge-logo.png', (528,), lossless=True)
    webp(output, 'team-group.png', (640, 1210))
    webp(output, 'robot-front-2026.jpg', (720, 1200, 2400), quality=88)

    for filename in ('award-finalist-alliance.png', 'award-reach.png', 'award-bc-championships.png'):
        webp(output, filename, (640, 1024))
    for filename in ('robot-decode-2026-cutout.png', 'robot-cdc-2025-cutout.png', 'robot-cdc-2026-v5-cutout.png'):
        with Image.open(ASSETS / filename) as source:
            widths = (640, source.width)
        webp(output, filename, widths)

    for filename in (
        'team-collaboration.png', 'robot-transfer.png', 'stem-buddies.png',
        'outreach-team-meeting.png', 'fundraising-krispy-kreme.png',
        'team-adam-fockler.jpg', 'team-evan-chan.jpg', 'team-gerard-tran.png',
        'team-jacob-joe.jpg', 'team-jayden-wong.jpg', 'team-salomi-aiyathurai.jpg',
        'team-steven-zhang.jpg', 'team-theo-shim.jpg',
        'about-robot-poster.png', 'about-robot-build-start.png', 'robot-motion-black-poster.png',
    ):
        webp(output, filename)
    for filename in ('about-robot-sketch.png', 'robot-code-telemetry.png', 'robot-intake.png', 'robot-motion-2026-start.png'):
        webp(output, filename, lossless=True)

    about_video(output)


if __name__ == '__main__':
    with TemporaryDirectory(dir=ASSETS, prefix='.web-media-') as directory:
        output = Path(directory)
        prepare_media(output)
        for media in output.iterdir():
            media.replace(ASSETS / media.name)
