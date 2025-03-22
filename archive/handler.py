import subprocess
from pathlib import Path
from typing import Optional
from log_config import logger
from utils.file_utils import calculate_feature
from password_manager.manager import PasswordManager
from concurrent.futures import ThreadPoolExecutor, as_completed


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

    def test_password_with_7z(self, file_path: Path, password: str) -> bool:
        """使用 7z t 测试密码"""
        try:
            command = [str(self.seven_zip_path), "t", str(file_path), f"-p{password}"]

            # 执行 7z t 命令进行密码验证
            result = subprocess.run(command, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)

            output = result.stdout.lower()

            if "wrong password" in output or "incorrect password" in output:
                logger.debug(f"密码错误: {password}")
                return False  # 密码错误
            elif "error" in output:
                logger.debug(f"7z 测试失败: {output}")
                return False  # 7z 测试失败
            logger.info(f"密码 '{password}' 测试通过")
            return True
        except Exception as e:
            logger.debug(f"7z 测试密码异常: {e}")
            return False

    def extract_with_7z(self, file_path: Path, output_dir: Path, password: Optional[str] = "") -> bool:
        """使用 7z.exe 解压，并实时显示进度"""
        try:
            command = [str(self.seven_zip_path), "x", str(file_path), f"-o{output_dir}", "-y", "-bsp1"]
            command.append(f"-p{password}")

            # 使用 Popen 实现实时输出
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=subprocess.CREATE_NO_WINDOW)

            # 实时读取标准输出
            for line in process.stdout:
                line = line.strip()
                if "%" in line:  # 进度行
                    logger.info(f"解压进度: {line}")  # 打印进度百分比

            # 等待进程结束并获取输出
            stdout, stderr = process.communicate()

            # 检查是否有错误信息
            if "wrong password" in stdout.lower() or "incorrect password" in stdout.lower():
                logger.debug(f"密码错误: {password}")
                return False
            elif "error" in stdout.lower():
                logger.debug(f"7z 解压失败: {stdout}")
                return False

            logger.info(f"文件 '{file_path}' 成功解压到 '{output_dir}' 密码:{password}")
            return True
        except Exception as e:
            logger.debug(f"7z 解压异常: {e}")
            return False

    def extract_with_password_retry(self, file_path: Path, output_dir: Path):
        """使用线程池尝试不同密码解压"""
        feature = calculate_feature(file_path)

        # 创建一个线程池来并发尝试多个密码
        with ThreadPoolExecutor(max_workers=20) as executor:
            # 1. 尝试已存储的特定密码
            saved_password = self.password_manager.get_password_by_feature(feature)
            if saved_password:
                logger.info(f"尝试使用已保存的密码 '{saved_password}' 解压")
                if self.test_password_with_7z(file_path, saved_password):
                    if self.extract_with_7z(file_path, output_dir, saved_password):
                        return

            # 2. 生成全局密码列表并提交到线程池
            global_passwords = self.password_manager.data.get("global_passwords", [])
            futures = []
            
            # 为每个密码创建任务并提交到线程池
            for password in global_passwords:
                futures.append(executor.submit(self.test_password_and_extract, file_path, output_dir, password))

            # 等待任务完成并检查结果
            for future in as_completed(futures):
                result = future.result()
                if result:
                    logger.info("密码解压成功")
                    return

        logger.error(f"无法解压文件 '{file_path}'，未找到有效密码")

    def test_password_and_extract(self, file_path: Path, output_dir: Path, password: str) -> bool:
        """测试密码并解压"""
        if self.test_password_with_7z(file_path, password):
            return self.extract_with_7z(file_path, output_dir, password)
        return False

    def extract(self, file_path: Path, output_dir: Path):
        """外部调用解压函数的入口"""
        logger.info(f"开始处理文件 '{file_path}'")

        # 1. 尝试无密码解压
        logger.info(f"尝试无密码解压")
        if self.test_password_and_extract(file_path, output_dir, password=""):
            return

        # 2. 如果以上方法都失败，尝试密码解密
        logger.info(f"文件 '{file_path}' 被加密，正在尝试密码解压")
        self.extract_with_password_retry(file_path, output_dir)
