from webdav3.client import Client
import json
import io

class WebDAVClient:
    def __init__(self, config):
        self.config = config
        self.client = None
        if config['url']:
            options = {
                'webdav_hostname': config['url'],
                'webdav_login': config['username'],
                'webdav_password': config['password']
            }
            self.client = Client(options)

    def ensure_remote_directory(self):
        """确保远程目录存在"""
        if not self.client:
            return False
        try:
            # 检查远程根目录是否存在
            if not self.client.check("/"):
                self.client.mkdir("/")
            return True
        except Exception as e:
            print(f"Failed to ensure remote directory: {e}")
            return False

    def sync(self, password_manager, mapping_manager):
        if not self.client or not self.ensure_remote_directory():
            return
        
        # Sync passwords
        try:
            # 将远程文件内容加载到内存
            remote_pwd_content = self.client.get_file_content('passwords.txt')
            if remote_pwd_content:
                remote_pwd = remote_pwd_content.decode('utf-8').splitlines()
                password_manager.merge(remote_pwd)
        except Exception as e:
            print(f"Password sync failed: {e}")

        # Sync mappings
        try:
            # 将远程文件内容加载到内存
            remote_map_content = self.client.get_file_content('mappings.json')
            if remote_map_content:
                remote_map = json.loads(remote_map_content.decode('utf-8'))
                mapping_manager.mappings.update(remote_map)
                mapping_manager._save()
        except Exception as e:
            print(f"Mapping sync failed: {e}")

    def upload_and_sync(self, password_manager, mapping_manager):
        if not self.client or not self.ensure_remote_directory():
            print("WebDAV not configured.")
            return

        try:
            # 下载远程文件到内存
            remote_files = {'passwords.txt': None, 'mappings.json': None}
            for remote in remote_files:
                try:
                    content = self.client.get_file_content(remote)
                    if content:
                        remote_files[remote] = content.decode('utf-8')
                except Exception as e:
                    print(f"Remote file {remote} not found or download failed: {e}")
                    # 如果远程文件不存在，设置为空
                    remote_files[remote] = ''

            # 合并密码本
            if remote_files['passwords.txt']:
                remote_pwd = remote_files['passwords.txt'].splitlines()
                password_manager.merge(remote_pwd)

            # 合并映射
            if remote_files['mappings.json']:
                remote_map = json.loads(remote_files['mappings.json'])
                mapping_manager.mappings.update(remote_map)
                mapping_manager._save()

            # 上传合并后的文件到远程
            self.client.upload_to(
                'passwords.txt',
                io.BytesIO('\n'.join(password_manager.passwords).encode('utf-8'))
            )
            self.client.upload_to(
                'mappings.json',
                io.BytesIO(json.dumps(mapping_manager.mappings, indent=2).encode('utf-8'))
            )
            print("Upload and sync completed.")
        except Exception as e:
            print(f"Upload and sync failed: {e}")

    def list_remote_files(self, path='/'):
        """列出远程 WebDAV 路径下的文件和目录"""
        try:
            files = self.client.list(path)  # 获取指定路径下的所有文件和文件夹
            if files:
                print(f"Files and directories in {path}:")
                for file in files:
                    print(file)
            else:
                print(f"No files found in {path}")
        except Exception as e:
            print(f"Failed to list files in {path}: {e}")