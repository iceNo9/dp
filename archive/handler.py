import subprocess
from pathlib import Path
from typing import Optional
from log_config import logger
from utils.file_utils import calculate_feature
from password_manager.manager import PasswordManager


class ArchiveHandler:
    def __init__(self):
        """初始化：检查 bin/ 目录下是否有 7z.exe"""
        self.seven_zip_path = Path(__file__).parent.parent / "bin" / "7za.exe"
        if not self.seven_zip_path.exists():
            raise FileNotFoundError(f"未找到 7z.exe，请将其放入 {self.seven_zip_path}")

        self.password_manager = PasswordManager()

    def detect_format(self, file_path: Path) -> Optional[str]:
        """使用 7z.exe 识别文件类型"""
        try:
            result = subprocess.run(
                [self.seven_zip_path, "l", str(file_path)],
                capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            output = result.stdout.lower()

            if "7-zip archive" in output:
                return "7z"
            elif "zip archive" in output:
                return "zip"
            elif "rar archive" in output:
                return "rar"
            elif "tar archive" in output:
                return "tar"
            elif "gzip compressed" in output:
                return "gzip"
            else:
                return None
        except Exception as e:
            logger.error(f"7z 识别文件格式失败: {e}")
            return None

    def is_encrypted(self, file_path: Path) -> bool:
        """检查文件是否加密"""
        try:
            # 使用 7z l 命令查看文件详细信息
            result = subprocess.run(
                [self.seven_zip_path, "l", str(file_path)],
                capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            output = result.stdout.lower()

            # 如果方法包含 7zAES 表示文件加密
            if "7zaes" in output:
                logger.debug(f"文件 '{file_path}' 使用了 AES 加密。")
                return True

            # 如果方法包含其他加密方式也认为文件加密
            if "aes" in output or "zipcrypto" in output:
                logger.debug(f"文件 '{file_path}' 使用了加密。")
                return True

            return False
        except Exception as e:
            logger.error(f"检查文件加密时发生异常: {e}")
            return False

    def extract_with_7z(self, file_path: Path, output_dir: Path, password: Optional[str] = "") -> bool:
        """使用 7z.exe 解压"""
        try:
            # 正常解压
            command = [str(self.seven_zip_path), "x", str(file_path), f"-o{output_dir}", "-y"]
            command.append(f"-p{password}")

            result = subprocess.run(command, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)

            if "wrong password" in result.stdout.lower():
                logger.debug(f"密码错误: {password}")
                return False
            elif "error" in result.stdout.lower():
                logger.error(f"7z 解压失败: {result.stdout}")
                return False

            logger.info(f"文件 '{file_path}' 成功解压到 '{output_dir}'")
            return True
        except Exception as e:
            logger.error(f"7z 解压异常: {e}")
            return False

    def extract_with_password_retry(self, file_path: Path, output_dir: Path):
        """尝试无密码解压，若失败则遍历密码库"""
        feature = calculate_feature(file_path)

        # 2. 尝试已存储的特定密码
        saved_password = self.password_manager.get_password_by_feature(feature)
        if saved_password:
            logger.info(f"尝试使用已保存的密码 '{saved_password}' 解压")
            if self.extract_with_7z(file_path, output_dir, saved_password):
                return

        # 3. 遍历全局密码
        for password in self.password_manager.data.get("global_passwords", []):
            logger.info(f"尝试使用密码 '{password}' 解压")
            if self.extract_with_7z(file_path, output_dir, password):
                self.password_manager.add_feature_password_mapping(feature, password)
                logger.info(f"文件 '{file_path}' 的密码为 '{password}'")
                return

        logger.error(f"无法解压文件 '{file_path}'，未找到有效密码")

    def extract(self, file_path: Path, output_dir: Path):
        """外部调用解压函数的入口"""
        logger.info(f"开始处理文件 '{file_path}'")
        
        # 优先判断是否加密
        if not self.is_encrypted(file_path):
            # 文件没有加密，直接解压
            logger.info(f"文件 '{file_path}' 没有加密，开始解压")
            if self.extract_with_7z(file_path, output_dir, password=""):
                logger.info(f"文件 '{file_path}' 成功解压到 '{output_dir}'")
                return
        else:
            # 文件被加密，尝试密码解压
            logger.info(f"文件 '{file_path}' 被加密，正在尝试密码解压")
            self.extract_with_password_retry(file_path, output_dir)
