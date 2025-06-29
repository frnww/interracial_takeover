import subprocess
import sys
import os
import time
import re
import hashlib
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

MOD_FILE = r"G:\Modding\Paradox Interactive\Crusader Kings III\mod\interracial_takeover.mod"  # <-- set your .mod file path here
CK3_TIGER_CMD = "ck3-tiger.exe"  # Must be in your PATH
DEBOUNCE_TIME = 2  # seconds

def extract_mod_folder(mod_file_path):
    with open(mod_file_path, encoding='utf-8-sig') as f:
        content = f.read()
    match = re.search(r'path\s*=\s*"?(.+?)"?\s*$', content, re.MULTILINE)
    if not match:
        print("ERROR: Could not find a path= entry in the .mod file!")
        sys.exit(1)
    mod_folder = match.group(1).strip().replace('/', os.sep)
    # If path is relative, resolve it relative to the .mod file
    if not os.path.isabs(mod_folder):
        mod_folder = os.path.abspath(os.path.join(os.path.dirname(mod_file_path), mod_folder))
    return mod_folder

WATCHED_FOLDER = extract_mod_folder(MOD_FILE)
WATCHED_EXTENSIONS = ('.txt', '.yml')  # File types to watch

# Dict to store last known sha256 hashes
file_hashes = {}

def sha256_of_file(path):
    try:
        h = hashlib.sha256()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                h.update(chunk)
        return h.hexdigest()
    except Exception as e:
        return None

class ChangeHandler(FileSystemEventHandler):
    def __init__(self):
        self.last_run = 0

    def on_any_event(self, event):
        if event.is_directory or not event.src_path.lower().endswith(WATCHED_EXTENSIONS):
            return
        now = time.time()
        # Debounce
        if now - self.last_run <= DEBOUNCE_TIME:
            return

        file_path = event.src_path
        new_hash = sha256_of_file(file_path)
        old_hash = file_hashes.get(file_path)
        if new_hash is not None and new_hash != old_hash:
            print(f"File content changed: {file_path}")
            command_line = f'{CK3_TIGER_CMD} "{MOD_FILE}"'
            subprocess.Popen(
                f'cmd.exe /c start "" cmd.exe /k {command_line}',
                shell=True
            )
            self.last_run = now
        # Always update the hash table (even if None for deleted/moved)
        file_hashes[file_path] = new_hash

def scan_all_files_and_cache_hashes(folder, extensions):
    for root, dirs, files in os.walk(folder):
        for file in files:
            if file.lower().endswith(extensions):
                full_path = os.path.join(root, file)
                file_hashes[full_path] = sha256_of_file(full_path)

if __name__ == "__main__":
    print(f"Watching: {WATCHED_FOLDER} (from mod file: {MOD_FILE})")
    scan_all_files_and_cache_hashes(WATCHED_FOLDER, WATCHED_EXTENSIONS)
    event_handler = ChangeHandler()
    observer = Observer()
    observer.schedule(event_handler, WATCHED_FOLDER, recursive=True)
    observer.start()
    print(f"Watching '{WATCHED_FOLDER}' for content changes to .txt or .yml files. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
