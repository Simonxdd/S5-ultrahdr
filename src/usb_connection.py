import ctypes
import platform
import time
import psutil

def wait_for_drives(target_name="LUMIX", interval=1):
    while True:
        drives = get_drive_paths(target_name)
        if drives:
            return drives
        time.sleep(interval)

def get_drive_paths(target_name):
    if platform.system() == "Windows":
        return get_drive_paths_win32(target_name)
    return []

def get_drive_paths_win32(target_name):
    matching_drives = []
    for partition in psutil.disk_partitions():
        mountpoint = partition.mountpoint
        volume_name = ctypes.create_unicode_buffer(256)
        file_system = ctypes.create_unicode_buffer(256)

        try:
            result = ctypes.windll.kernel32.GetVolumeInformationW(
                ctypes.c_wchar_p(mountpoint),
                volume_name,
                ctypes.sizeof(volume_name),
                None, None, None,
                file_system,
                ctypes.sizeof(file_system)
            )
            if result and volume_name.value.strip().lower() == target_name.strip().lower():
                matching_drives.append(mountpoint)
        except Exception:
            continue

    return matching_drives