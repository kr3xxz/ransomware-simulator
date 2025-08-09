import argparse
import json
import os
import pathlib
import platform
import random
import shutil
import string
import subprocess
import time

from encryptor import load_or_create_key, encrypt_file, decrypt_file

# --- Configuration (can be moved to config.yaml later) ---
try:
    import yaml
    CONFIG = yaml.safe_load(pathlib.Path('config.yaml').read_text())
    DECOY_TEMPLATE_DIR = pathlib.Path(CONFIG['decoy_template_dir'])
    DECOY_DIR = pathlib.Path(CONFIG['decoy_work_dir'])
    KEY_DIR = pathlib.Path(CONFIG['key_dir'])
    LOG_DIR = pathlib.Path(CONFIG['log_dir'])
except (ImportError, FileNotFoundError):
    print("WARNING: config.yaml not found or pyyaml not installed. Using default paths.")
    DECOY_TEMPLATE_DIR = pathlib.Path('decoy_templates')
    DECOY_DIR = pathlib.Path('decoys') # Default to 'decoys'
    KEY_DIR = pathlib.Path('keys')
    LOG_DIR = pathlib.Path('logs')


# --- Helper Functions ---
def random_string(n=8):
    """Generates a random string for filenames."""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(n))

def plant_decoys():
    """Copies files from templates to the working decoy directory."""
    if not DECOY_DIR.exists():
        DECOY_DIR.mkdir()
    # Clean out old decoys first for a fresh run
    for item in DECOY_DIR.iterdir():
        item.unlink()
    # Plant new ones
    for src_file in DECOY_TEMPLATE_DIR.iterdir():
        ext = src_file.suffix
        dest_file = DECOY_DIR / f"{random_string()}{ext}"
        shutil.copy(src_file, dest_file)

def drop_ransom_note(key_filename):
    """Creates a ransom note on the desktop and opens it."""
    note_text = f"""YOUR FILES HAVE BEEN ENCRYPTED!
---------------------------------------
This is a **TRAINING SIMULATION ONLY**. No real data has been harmed.

To restore your files, run the following command in your terminal,
using the key file that was generated for this run:

    python simulator.py --decrypt {key_filename}

(If this were a real attack, you would see instructions to pay a ransom.)
"""
    try:
        desktop = pathlib.Path.home() / "Desktop"
        note_path = desktop / "RANSOM_NOTE.txt"
        note_path.write_text(note_text)
        print(f"Ransom note created at: {note_path}")
        if platform.system() == "Windows":
            os.startfile(str(note_path))
        else:
            subprocess.run(["gedit", str(note_path)], check=False)
    except Exception as e:
        print(f"Could not open ransom note automatically: {e}")

def simulate(encrypt: bool, key_path: pathlib.Path):
    """Main simulation logic for encryption or decryption using an explicit key path."""
    KEY_DIR.mkdir(exist_ok=True)
    LOG_DIR.mkdir(exist_ok=True)
    
    key = load_or_create_key(key_path)
    
    from cryptography.fernet import Fernet
    try:
        f = Fernet(key)
    except Exception as e:
        print(f"FATAL: Could not initialize encryption engine. Is the key valid? Error: {e}")
        return

    action = encrypt_file if encrypt else decrypt_file
    summary = []
    print(f"Starting to process files in: {DECOY_DIR}")

    for fp in DECOY_DIR.rglob("*.*"):
        if fp.is_file():
            try:
                action(fp, f)
                summary.append({"file": str(fp), "status": "processed"})
            except Exception as e:
                # This is CRITICAL for debugging decryption
                print(f"ERROR: Failed to process {fp}. Reason: {e}")
                summary.append({"file": str(fp), "status": "error", "reason": str(e)})

    (LOG_DIR / "latest_run_summary.json").write_text(json.dumps(summary, indent=2))
    
    if encrypt:
        drop_ransom_note(key_path.name)

# --- Main Execution Block ---
def main():
    parser = argparse.ArgumentParser(
        description="Safe Ransomware Simulator. Run --plant, then --encrypt, then --decrypt with the generated key.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--plant", action="store_true", help="Plant fresh decoy files from templates.")
    parser.add_argument("--encrypt", action="store_true", help="Encrypt decoys and drop ransom note.")
    parser.add_argument("--decrypt", type=str, metavar="KEY_FILENAME", help="Decrypt decoys using a specific key file from the 'keys/' directory.")
    
    args = parser.parse_args()

    # Logic to ensure only one action is performed
    action_count = sum([args.plant, args.encrypt, args.decrypt is not None])
    if action_count != 1:
        parser.error("You must specify exactly one action: --plant, --encrypt, or --decrypt KEY_FILENAME")

    # Execute the requested action
    if args.plant:
        print(f"🌱 Planting decoy files into '{DECOY_DIR}'...")
        plant_decoys()
        print("✅ Decoy files planted successfully.")
    elif args.encrypt:
        print("🔒 Starting encryption simulation...")
        # Define the key path for this specific run
        key_path = KEY_DIR / f"{int(time.time())}.key"
        simulate(encrypt=True, key_path=key_path)
        print(f"✅ Encryption complete. Key saved as: {key_path.name}")
    elif args.decrypt:
        # Construct the full path to the user-provided key file
        key_file_path = KEY_DIR / args.decrypt
        if not key_file_path.is_file():
            parser.error(f"Key file not found at '{key_file_path}'. Please check the filename.")
        
        print(f"🔑 Starting decryption process with key: {args.decrypt}")
        simulate(encrypt=False, key_path=key_file_path)
        print("✅ Decryption complete. Please verify the files.")

if __name__ == "__main__":
    main()
