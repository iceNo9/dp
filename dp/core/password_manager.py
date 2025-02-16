import os

class PasswordManager:
    def __init__(self, file_path):
        self.file_path = file_path
        self.passwords = []
        self._load()

    def _load(self):
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r') as f:
                self.passwords = sorted({line.strip() for line in f if line.strip()})
        self._save()

    def _save(self):
        with open(self.file_path, 'w') as f:
            f.write('\n'.join(self.passwords))

    def add(self, password):
        if password not in self.passwords:
            self.passwords.append(password)
            self.passwords.sort()
            self._save()

    def merge(self, passwords):
        merged = list(set(self.passwords + passwords))
        merged.sort()
        self.passwords = merged
        self._save()