import sys

import src.usb_connection as usb
import src.file_handling as fh
import src.raw_processing as raw
from src.check_dependencies import check_dependencies

_first_run = True

def main():
    if not check_dependencies():
        sys.exit(0)
    update_display(0, "Please connect your camera.", "Waiting for USB connection...")
    drives = usb.wait_for_drives()
    print(drives)
    update_display(0, "Please wait...", f"Found drives {drives}.")
    copied_photos = fh.copy_new_files(drives, progress_callback=update_display)
    raw.process_images(copied_photos, progress_callback=update_display)
    update_display(100, "All done!", f"Images processed.")

def update_display(progress, message1, message2):
    global _first_run
    bar = f"[{'█' * (progress // 5)}{'-' * (20 - progress // 5)}] {progress}%"
    if not _first_run:
        # Move up 3 lines, clear them, and print updated status
        print(f"\033[3F\033[K{message1}\n\033[K{message2}\n\033[K{bar}")
    else:
        print(f"{message1}\n{message2}\n{bar}")
        _first_run = False

if __name__ == '__main__':
    main()