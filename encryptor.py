from cryptography.fernet import Fernet
import pathlib

def load_or_create_key(key_path):
    if key_path.exists():
        return key_path.read_bytes()
    key = Fernet.generate_key()
    key_path.write_bytes(key)
    return key

def encrypt_file(file_path, fernet):
    data = file_path.read_bytes()
    file_path.write_bytes(fernet.encrypt(data))

def decrypt_file(file_path, fernet):
    data = file_path.read_bytes()
    file_path.write_bytes(fernet.decrypt(data))
