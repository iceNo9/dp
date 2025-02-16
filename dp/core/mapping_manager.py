import hashlib
import json
import os

class MappingManager:
    def __init__(self, file_path):
        self.file_path = file_path
        self.mappings = {}
        self._load()

    def _load(self):
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r', encoding='utf-8') as f:
                self.mappings = json.load(f)

    def _save(self):
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(self.mappings, f, indent=2)

    def add(self, file_path, password):
        file_hash = self._hash_file(file_path)
        self.mappings[file_hash] = password
        self._save()

    def get(self, file_path):
        file_hash = self._hash_file(file_path)
        return self.mappings.get(file_hash)

    def _hash_file(self, file_path):
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            while chunk := f.read(4096):
                hasher.update(chunk)
        return hasher.hexdigest()