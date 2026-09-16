import hashlib
import shutil
import os
import json

archive_path = "C:/Users/simon/Pictures/"

def copy_new_files(drives, file_ending=".RW2", progress_callback=None):
    all_source_photos = []
    for drive in drives:
        for root, dirs, files in os.walk(drive):
            for name in files:
                if name.endswith(file_ending):
                    all_source_photos.append(os.path.join(root, name))
    hash_list = _load_hash_list()
    all_source_photos_hashed = _hash_file_list(all_source_photos)

    hash_list = _remove_hash_for_removed_items(hash_list, all_source_photos_hashed)
    hash_list, source_paths, file_paths_hashed = _remove_hashed_items(hash_list, all_source_photos, all_source_photos_hashed)

    target_paths = [os.path.join(archive_path, os.path.basename(f)) for f in source_paths]

    for i, (src, dst) in enumerate(zip(source_paths, target_paths), start=1):
        if progress_callback:
            progress = int((i / len(source_paths)) * 100)
            progress_callback(progress,
                              "Please wait while files are being copied...",
                              f"Found drives {drives}.")
        shutil.copy2(src, dst)

    store_hash_list(hash_list)
    return target_paths

# Removes items from the file list that were already hashed and stored in the hash_list
def _remove_hashed_items(hash_list, file_paths, hashed_file_paths):
    # Check file paths for matches with hash_list
    append_counter = 0
    new_hashed_file_paths = []
    new_file_paths = []
    for path, hashed_path in zip(file_paths, hashed_file_paths):
        if not hashed_path in hash_list:
            hash_list.append(hashed_path)
            new_hashed_file_paths.append(hashed_path)
            new_file_paths.append(path)
            append_counter += 1
    #print("Hash list append counter: " + str(append_counter))
    return hash_list, new_file_paths, new_hashed_file_paths

def _remove_hash_for_removed_items(hash_list, hashed_file_paths):
    # Check hash_list to detect deleted files
    starting_length = len(hash_list)
    hash_list = [hash_item for hash_item in hash_list if hash_item in hashed_file_paths]
    #print("Hash list delete counter: " + str(starting_length - len(hash_list)))
    return hash_list

def _hash_file_list(file_paths):
    hashed_file_paths = []
    for file_path in file_paths:
        hashed_file_paths.append(_hash_file(file_path))
    return hashed_file_paths

def _hash_file(file_path):
    hasher = hashlib.sha256()
    stats = os.stat(file_path)
    metadata = f"{os.path.basename(file_path)}|{stats.st_mtime}"
    hasher.update(metadata.encode('utf-8'))
    return hasher.hexdigest()

# Load the hash_list from a file
def _load_hash_list():
    if not os.path.exists("hashlist.json"):
        return []
    try:
        with open("hashlist.json", "r") as f:
            loaded_hash_list = json.load(f)
        return loaded_hash_list
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from file: {e}")
        return []
    except IOError as e:
        print(f"Error reading file: {e}")
        return []

# Stores the hash_list in a file
def store_hash_list(hash_list):
    try:
        with open("hashlist.json", 'w') as f:
            json.dump(hash_list, f, indent=4)
    except IOError as e:
        print(f"Error saving file: {e}")