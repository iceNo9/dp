import subprocess
from pathlib import Path
from typing import Optional
from log_config import logger
from utils.file_utils import calculate_feature
from password_manager.manager import PasswordManager


class ArchiveHandler:
    def __init__(self):
        """初始化：检查 bin/ 目录下是否有 7z.exe 和 7z.dll"""
        self.bin_dir = Path(__file__).parent.parent / "bin"
        self.seven_zip_path = self.bin_dir / "7z.exe"
        self.seven_zip_dll = self.bin_dir / "7z.dll"

        if not self.seven_zip_path.exists():
            raise FileNotFoundError(f"未找到 7z.exe，请将其放入 {self.seven_zip_path}")
        if not self.seven_zip_dll.exists():
            logger.warning("未找到 7z.dll，可能无法解压 RAR 文件")

        self.password_manager = PasswordManager()

    def extract_with_7z(self, file_path: Path, output_dir: Path, password: Optional[str] = "") -> bool:
        """使用 7z.exe 解压"""
        try:
            command = [str(self.seven_zip_path), "x", str(file_path), f"-o{output_dir}", "-y"]
            command.append(f"-p{password}")

            result = subprocess.run(command, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            output = result.stdout.lower()

            if "wrong password" in output or "incorrect password" in output:
                logger.debug(f"密码错误: {password}")
                return False
            elif "error" in output:
                logger.debug(f"7z 解压失败: {output}")
                return False

            logger.info(f"文件 '{file_path}' 成功解压到 '{output_dir}' 密码:{password}")
            return True
        except Exception as e:
            logger.debug(f"7z 解压异常: {e}")
            return False

    def extract_with_password_retry(self, file_path: Path, output_dir: Path):
        """尝试无密码解压，若失败则遍历密码库"""
        feature = calculate_feature(file_path)

        # 1. 尝试无密码解压
        logger.debug(f"尝试无密码解压文件 '{file_path}'")
        if self.extract_with_7z(file_path, output_dir, password=""):
            return

        # 2. 尝试已存储的特定密码
        saved_password = self.password_manager.get_password_by_feature(feature)
        if saved_password:
            logger.debug(f"尝试使用已保存的密码 '{saved_password}' 解压")
            if self.extract_with_7z(file_path, output_dir, saved_password):
                return

        # 3. 遍历全局密码
        for password in self.password_manager.data.get("global_passwords", []):
            logger.debug(f"尝试使用密码 '{password}' 解压")
            if self.extract_with_7z(file_path, output_dir, password):
                self.password_manager.add_feature_password_mapping(feature, password)
                logger.info(f"文件 '{file_path}' 的密码为 '{password}'")
                return

        logger.error(f"无法解压文件 '{file_path}'，未找到有效密码")

    def extract(self, file_path: Path, output_dir: Path):
        """外部调用解压函数的入口"""
        logger.debug(f"开始处理文件 '{file_path}'")

        # 直接尝试解压，先使用无密码
        logger.debug(f"尝试无密码解压文件 '{file_path}'")
        if self.extract_with_7z(file_path, output_dir, password=""):
            logger.info(f"文件 '{file_path}' 成功解压到 '{output_dir}' 无密码")
            return

        # 如果无密码解压失败，尝试密码解压
        logger.info(f"文件 '{file_path}' 需要密码，正在尝试密码解压")
        self.extract_with_password_retry(file_path, output_dir)
