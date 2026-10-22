import math
import tempfile
import subprocess
import os
import platform
import shutil
from pathlib import Path
from enum import Enum

os.environ["PATH"] += os.pathsep + r'C:\Program Files\darktable\bin'

BASE_DIR = Path(__file__).resolve().parent
STYLES_V1 = BASE_DIR / "dt" / "styles_v1"

class AVIFSize(Enum):
    SMALL = (2048, 2048, None, 420)         # Smallest that should software-decode on Android
    BASELINE = (3840, 3840, 8912896, 420)   # Level 5.1 with 3840x3840 res limit for smartphone decoders
    PLUS = (4096, 4096, None, 420)          # Strict 4096x4096 limit, largest that decodes on Pixel 8.
    ADVANCED = (16384, 8704, 35651584, 444)     # AVIF Level 6.0, very large

    def __init__(self, max_width, max_height, max_pixels, chroma_subsampling):
        self.max_width = max_width
        self.max_height = max_height
        self.max_pixels = max_pixels
        self.chroma_subsampling = chroma_subsampling

def process_images(copied_photos, progress_callback=None):
    output_paths = [Path(p).with_name(Path(p).stem + "-hdr.jpg") for p in copied_photos]
    for i, (src, dst) in enumerate(zip(copied_photos, output_paths), start=1):
        if progress_callback:
            progress = int((i / len(copied_photos)) * 100)
            progress_callback(progress,
                              "You can now turn off the camera.",
                              f"Processing photos...")
        _generate_ultra_hdr_jpeg(src, dst) # switch later

def _generate_ultra_hdr_jpeg(input_path, output_path):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        sdr_png = (tmp_path / "temp_sdr.png").as_posix()
        hdr_png = (tmp_path / "temp_hdr.png").as_posix()
        sdr_raw = (tmp_path / "sdr.raw").as_posix()
        hdr_raw = (tmp_path / "hdr.raw").as_posix()
        input_str = Path(input_path).as_posix()
        output_str = Path(output_path).as_posix()
        try:
            subprocess.run([
                'darktable-cli',
                input_str,
                sdr_png,
                '--style', 'SDR',
                '--core', '--configdir', STYLES_V1.as_posix()
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            subprocess.run([
                'darktable-cli',
                input_str,
                hdr_png,
                '--style', 'Ultra_HDR',
                '--core', '--configdir', STYLES_V1.as_posix()
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            subprocess.run([
                'ffmpeg', '-y', '-i', sdr_png,
                '-loglevel', 'fatal', '-f', 'rawvideo',
                '-pix_fmt', 'rgba', sdr_raw
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            subprocess.run([
                'ffmpeg', '-y', '-i', hdr_png,
                '-loglevel', 'fatal', '-f', 'rawvideo',
                '-pix_fmt', 'p010le', hdr_raw
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            width, height = _get_image_dimensions(sdr_png)

            subprocess.run([
                'ultrahdr_app',
                '-m', '0',
                '-p', hdr_raw,
                '-y', sdr_raw,
                '-w', str(width),
                '-h', str(height),
                '-q', '85',
                '-Q', '95',
                '-a', '0',
                '-b', '3',
                '-c', '0',
                '-C', '2',
                '-t', '2',
                '-M', '1',
                '-L', '1000',
                '-z', output_str
            ], check=True)

            subprocess.run([
                "exiftool",
                "-overwrite_original",
                "-TagsFromFile",
                input_str,
                "--Orientation",
                output_str
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        except subprocess.CalledProcessError as e:
            print(f"\nAn error occurred: {e}")

def generate_ultra_hdr_avif(input_path: Path, output_path: Path, profile: AVIFSize, speed: int=4, quality: int=85):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        sdr_png = (tmp_path / "temp_sdr.png").as_posix()
        hdr_png = (tmp_path / "temp_hdr.png").as_posix()
        sdr_png_scaled = (tmp_path / "temp_sdr_scaled.png").as_posix()
        hdr_png_scaled = (tmp_path / "temp_hdr_scaled.png").as_posix()
        input_str = Path(input_path).as_posix()
        output_str = Path(output_path).as_posix()
        try:
            # SDR processing
            subprocess.run([
                'darktable-cli',
                input_str,
                sdr_png,
                '--style', 'SDR',
                '--core', '--configdir', STYLES_V1.as_posix(),
                '--conf', 'plugins/imageio/format/png/bpp=16'
            ], check=True, capture_output=True)
            # HDR processing
            subprocess.run([
                'darktable-cli',
                input_str,
                hdr_png,
                '--style', 'Ultra_HDR',
                '--core', '--configdir', STYLES_V1.as_posix(),
                '--conf', 'plugins/imageio/format/png/bpp=16'
            ], check=True, capture_output=True)
            hdr_png = _resize_image(hdr_png, hdr_png_scaled, profile.max_width, profile.max_height, profile.max_pixels)
            sdr_png = _resize_image(sdr_png, sdr_png_scaled, profile.max_width, profile.max_height, profile.max_pixels)
            # reapply camera metadata
            subprocess.run([
                "exiftool",
                "-overwrite_original",
                "-TagsFromFile",
                input_str,
                "--Orientation",
                sdr_png
            ], check=True, capture_output=True)
            # encode gain mapped avif
            subprocess.run([
                'avifgainmaputil',
                'combine', sdr_png, hdr_png,
                output_str, "--ignore-profile", "--cicp-alternate", "9/16/9", # darktable doesn't write correct cicp
                "--speed", str(speed), "-q", str(quality), "-d", "10", "-y", str(profile.chroma_subsampling)
            ], check=True, capture_output=True)

        except subprocess.CalledProcessError as e:
            print(f"\nAn error occurred: {e}")
            print(e.stdout)
            print(e.stderr)

def _get_image_dimensions(image_path):
    """Uses ffprobe to get width and height of the image."""
    cmd = [
        'ffprobe', '-v', 'error', '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height', '-of', 'csv=p=0:s=x',
        image_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    # result.stdout will be something like "2160x2160\n"
    dimensions = result.stdout.strip().split('x')
    return int(dimensions[0]), int(dimensions[1])

def _resize_image(image_path, output_path, max_width, max_height, max_pixels=None):
    """Resizes an image using ffmpeg and Lanczos scaling to fit dimensions and pixel constraints."""
    width, height = _get_image_dimensions(image_path)

    # Calculate scale factor for max dimensions
    scale = 1.0
    if width > max_width or height > max_height:
        scale = min(max_width / width, max_height / height)

    # Calculate scale factor for total pixel count if specified
    if max_pixels and (width * height * (scale ** 2)) > max_pixels:
        pixel_scale = math.sqrt(max_pixels / (width * height))
        scale = min(scale, pixel_scale)

    # Resize only if scaling is needed
    if scale < 1.0:
        new_width = int(width * scale)
        new_height = int(height * scale)

        # Prevent rounding overflow past limits
        new_width = min(new_width, max_width)
        new_height = min(new_height, max_height)

        # Run ffmpeg with Lanczos filter
        cmd = [
            'ffmpeg', '-y', '-i', image_path,
            '-vf', f'scale={new_width}:{new_height}:sws_flags=lanczos',
            output_path
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path

    return image_path

if __name__ == '__main__':
    if platform.system() == "Darwin" and not shutil.which("darktable-cli"):
        candidates = [
            Path("/Applications/darktable.app/Contents/MacOS/darktable-cli"),
            Path.home()
            / "Applications/darktable.app/Contents/MacOS/darktable-cli",
            Path("/opt/homebrew/bin/darktable-cli"),  # Apple Silicon Homebrew
            Path("/usr/local/bin/darktable-cli"),  # Intel Homebrew
            Path("/opt/local/bin/darktable-cli"),  # MacPorts
        ]
    for binary_path in candidates:
        if binary_path.is_file():
            os.environ["PATH"] = (
                    str(binary_path.parent)
                    + os.pathsep
                    + os.environ.get("PATH", "")
            )
            break
    # Testing here...