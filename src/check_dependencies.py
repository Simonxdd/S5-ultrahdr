import os
import platform
import shutil
import subprocess
from pathlib import Path

def check_dependencies():
    bad = False
    if not check_darktable():
        print("Darktable could not be found on this system.")
        bad = True
    if not check_libultrahdr():
        print("libultrahdr could not be found on this system.")
        bad = True
    if not check_exiftool():
        print("exiftool could not be found on this system.")
        bad = True
    return not bad

def check_darktable():
    # On macOS, search standard installation paths and add darktable-cli to PATH if needed
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

    # Test if darktable-cli can actually be called
    try:
        subprocess.run(
            ["darktable-cli", "--version"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except subprocess.SubprocessError:
        return True
    except (FileNotFoundError, OSError):
        return False

def check_libultrahdr():
    try:
        subprocess.run(
            ["ultrahdr_app"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except subprocess.SubprocessError:
        return True
    except (FileNotFoundError, OSError):
        return False

def check_exiftool():
    try:
        subprocess.run(
            ["exiftool"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except subprocess.SubprocessError:
        return True
    except (FileNotFoundError, OSError):
        return False