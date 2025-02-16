import os
import pyzipper
import py7zr
import rarfile
import tarfile
from tqdm import tqdm

class Extractor:
    @staticmethod
    def detect_type(file_path):
        signature = open(file_path, 'rb').read(4)
        if signature.startswith(b'PK'):
            return 'zip'
        elif signature.startswith(b'7z'):
            return '7z'
        elif signature.startswith(b'Rar'):
            return 'rar'
        elif signature.startswith(b'\x1f\x8b'):
            return 'tar.gz'
        return os.path.splitext(file_path)[1][1:]

    def extract(self, file_path, output_dir=None, password=None):
        file_type = self.detect_type(file_path)
        output_dir = output_dir or os.path.splitext(file_path)[0]
        os.makedirs(output_dir, exist_ok=True)

        try:
            if file_type == 'zip':
                self._extract_zip(file_path, output_dir, password)
            elif file_type == '7z':
                self._extract_7z(file_path, output_dir, password)
            elif file_type == 'rar':
                self._extract_rar(file_path, output_dir, password)
            elif file_type in ['tar', 'gz', 'bz2']:
                self._extract_tar(file_path, output_dir)
            else:
                raise ValueError("Unsupported file format")
            return True
        except Exception as e:
            return False

    def _extract_zip(self, path, output, pwd):
        with pyzipper.AESZipFile(path) as zf:
            if pwd:
                zf.setpassword(pwd.encode('utf-8'))
            total = sum(f.file_size for f in zf.infolist())
            with tqdm(total=total, unit='B', unit_scale=True) as pbar:
                for f in zf.infolist():
                    zf.extract(f, output)
                    pbar.update(f.file_size)

    def _extract_7z(self, path, output, pwd):
        with py7zr.SevenZipFile(path, 'r', password=pwd) as z:
            z.extractall(output)

    def _extract_rar(self, path, output, pwd):
        with rarfile.RarFile(path) as rf:
            if pwd:
                rf.setpassword(pwd)
            rf.extractall(output)

    def _extract_tar(self, path, output):
        with tarfile.open(path) as tf:
            tf.extractall(output)