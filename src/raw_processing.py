import tempfile
import subprocess
import os
from pathlib import Path

os.environ["PATH"] += os.pathsep + r'C:\Program Files\darktable\bin'

def process_images(copied_photos, progress_callback=None):
    output_paths = [Path(p).with_name(Path(p).stem + "-hdr.jpg") for p in copied_photos]
    for i, (src, dst) in enumerate(zip(copied_photos, output_paths), start=1):
        if progress_callback:
            progress = int((i / len(copied_photos)) * 100)
            progress_callback(progress,
                              "You can now turn off the camera.",
                              f"Processing photos...")
        _generate_ultra_hdr(src, dst)

def _generate_ultra_hdr(input_path, output_path):
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
                '--style', 'SDR'
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            subprocess.run([
                'darktable-cli',
                input_str,
                hdr_png,
                '--style', 'Ultra_HDR'
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
                './ultrahdr_app',
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