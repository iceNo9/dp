import zipfile
import py7zr
import tarfile
import gzip
import magic
from pathlib import Path
from typing import List, Optional
from log_config import logger
from utils.file_utils import calculate_feature
from password_manager.manager import PasswordManager
from py7zr.exceptions import PasswordRequired, Bad7zFile

class ArchiveHandler:
    def __init__(self):
        self.password_manager = PasswordManager()

    def detect_format(self, file_path: Path) -> Optional[str]:
        mime = magic.Magic(mime=True)
        file_type = mime.from_file(str(file_path))  # 显式转换为字符串
        if file_type == "application/zip":
            return "zip"
        elif file_type == "application/x-7z-compressed":
            return "7z"
        elif file_type == "application/x-tar":
            return "tar"
        elif file_type == "application/gzip":
            return "gzip"
        return None

    def extract(self, file_path: Path, output_dir: Path, password: Optional[str] = None) -> bool:
        format = self.detect_format(file_path)
        if not format:
            logger.error(f"无法识别的文件格式: {file_path}")
            return False

        try:
            if format == "zip":
                with zipfile.ZipFile(file_path, "r") as zip_ref:
                    if password:
                        zip_ref.setpassword(password.encode())
                    zip_ref.extractall(output_dir)
            elif format == "7z":
                try:
                    # 尝试无密码解压
                    with py7zr.SevenZipFile(file_path, mode="r") as archive:
                        archive.extractall(output_dir)
                    logger.info(f"文件 '{file_path}' 无需密码解压成功")
                    return True
                except Bad7zFile:
                    logger.error(f"文件 '{file_path}' 解压失败: 文件损坏或无效")
                except PasswordRequired:
                    # 需要密码时才尝试带密码解压
                    if password:
                        with py7zr.SevenZipFile(file_path, mode="r", password=password) as archive:
                            archive.extractall(output_dir)
                    else:
                        raise ValueError("7z 文件可能需要密码")
            elif format == "tar":
                with tarfile.open(file_path, "r") as tar_ref:
                    tar_ref.extractall(output_dir)
            elif format == "gzip":
                with gzip.open(file_path, "rb") as gz_ref:
                    with open(output_dir / file_path.stem, "wb") as out_ref:
                        out_ref.write(gz_ref.read())
            logger.info(f"文件 '{file_path}' 解压成功到 '{output_dir}'")
            return True
        except Exception as e:
            logger.error(f"解压失败: {e}")
            return False

    def extract_with_password_retry(self, file_path: Path, output_dir: Path):
        feature = calculate_feature(file_path)

        # 先尝试无密码解压
        logger.info(f"尝试无密码解压 '{file_path}'")
        if self.extract(file_path, output_dir):
            return

        # 尝试已存储的特定密码
        saved_password = self.password_manager.get_password_by_feature(feature)
        if saved_password:
            logger.info(f"尝试使用已保存的密码 '{saved_password}' 解压")
            if self.extract(file_path, output_dir, saved_password):
                return

        # 遍历全局密码
        for password in self.password_manager.data["global_passwords"]:
            logger.info(f"尝试使用密码 '{password}' 解压")
            if self.extract(file_path, output_dir, password):
                self.password_manager.add_feature_password_mapping(feature, password)
                logger.info(f"文件 '{file_path}' 的密码为 '{password}'")
                return

        logger.error(f"无法解压文件 '{file_path}'，未找到有效密码")
