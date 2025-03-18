import json
from pathlib import Path
from typing import List, Dict
from log_config import logger
from config.settings import PASSWORDS_FILE
from typing import Optional

class PasswordManager:
    def __init__(self):
        self.passwords_file = PASSWORDS_FILE
        self.data = {"global_passwords": [], "feature_password_map": {}}
        self.load()

    def load(self):
        """加载密码库"""
        if self.passwords_file.exists():
            try:
                with open(self.passwords_file, "r") as f:
                    self.data = json.load(f)
            except Exception as e:
                logger.error(f"加载密码文件失败: {e}")

    def save(self):
        """保存密码库到文件"""
        try:
            with open(self.passwords_file, "w") as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            logger.error(f"保存密码文件失败: {e}")

    def add_password(self, password: str):
        """添加密码到全局库"""
        if password not in self.data["global_passwords"]:
            self.data["global_passwords"].append(password)
            self.save()  # 及时保存更改
            logger.info(f"密码 '{password}' 已添加到全局库")
        else:
            logger.warning(f"密码 '{password}' 已存在")

    def delete_password(self, password: str):
        """从全局库删除密码"""
        if password in self.data["global_passwords"]:
            self.data["global_passwords"].remove(password)
            self.save()  # 及时保存更改
            logger.info(f"密码 '{password}' 已从全局库删除")
        else:
            logger.warning(f"密码 '{password}' 不存在")

    def add_feature_password_mapping(self, feature: str, password: str):
        """为文件特征值绑定密码"""
        if not password:  # 检查空密码
            logger.warning(f"尝试为文件特征值 '{feature}' 绑定空密码，已忽略")
            return

        self.data["feature_password_map"][feature] = password
        self.save()  # 及时保存更改
        logger.info(f"文件特征值 '{feature}' 已映射到密码 '{password}'")

    def get_password_by_feature(self, feature: str) -> Optional[str]:
        """根据特征值获取密码"""
        return self.data["feature_password_map"].get(feature)

    def import_passwords(self, file_path: Path):
        """从文件导入密码"""
        try:
            with open(file_path, "r") as f:
                passwords = [line.strip() for line in f.readlines()]
                for password in passwords:
                    self.add_password(password)
            logger.info(f"从文件 '{file_path}' 导入密码成功")
        except Exception as e:
            logger.error(f"导入密码失败: {e}")

    def export_passwords(self, output_dir: Path):
        """导出密码"""
        try:
            output_file = output_dir / "passwords.txt"
            with open(output_file, "w") as f:
                for password in self.data["global_passwords"]:
                    f.write(f"{password}\n")
            logger.info(f"密码已导出到 '{output_file}'")
        except Exception as e:
            logger.error(f"导出密码失败: {e}")

    def export_mappings(self, output_dir: Path):
        """导出密码映射"""
        try:
            output_file = output_dir / "mappings.txt"
            with open(output_file, "w") as f:
                for feature, password in self.data["feature_password_map"].items():
                    f.write(f"{feature}:{password}\n")
            logger.info(f"密码映射已导出到 '{output_file}'")
        except Exception as e:
            logger.error(f"导出密码映射失败: {e}")

    def import_mappings(self, file_path: Path):
        """从文件导入密码映射"""
        try:
            with open(file_path, "r") as f:
                lines = f.readlines()
                for line in lines:
                    feature, password = line.strip().split(":", 1)  # 分割特征和值
                    self.add_feature_password_mapping(feature, password)  # 使用已有的方法添加映射
            logger.info(f"从文件 '{file_path}' 导入密码映射成功")
        except Exception as e:
            logger.error(f"导入密码映射失败: {e}")