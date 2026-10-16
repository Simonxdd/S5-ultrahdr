import tempfile
import subprocess
import os
import platform
import shutil
from pathlib import Path

os.environ["PATH"] += os.pathsep + r'C:\Program Files\darktable\bin'

BASE_DIR = Path(__file__).resolve().parent
STYLES_V1 = BASE_DIR / "dt" / "styles_v1"

def process_images(copied_photos, progress_callback=None):
    output_paths = [Path(p).with_name(Path(p).stem + "-hdr.avif") for p in copied_photos]
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

def _generate_ultra_hdr_avif(input_path: Path, output_path: Path, speed: int=4, quality: int=85):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        sdr_png = (tmp_path / "temp_sdr.png").as_posix()
        hdr_png = (tmp_path / "temp_hdr.png").as_posix()
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
                "--speed", str(speed), "-q", str(quality), "-d", "10"
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
    return dimensions[0], dimensions[1]

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
#_generate_ultra_hdr_v2(input, "output.avif")