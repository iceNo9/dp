from webdav3.client import Client
import json

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

    def sync(self, password_manager, mapping_manager):
        if not self.client:
            return
        
        # Sync passwords
        try:
            self.client.download('passwords.txt', 'temp_pwd.txt')
            with open('temp_pwd.txt', 'r') as f:
                remote_pwd = [line.strip() for line in f]
            password_manager.merge(remote_pwd)
            # self.client.upload('passwords.txt', password_manager.file_path)
        except Exception as e:
            print(f"Password sync failed: {e}")

        # Sync mappings
        try:
            self.client.download('mappings.json', 'temp_map.json')
            with open('temp_map.json', 'r') as f:
                remote_map = json.load(f)
            mapping_manager.mappings.update(remote_map)
            mapping_manager._save()
            # self.client.upload('mappings.json', mapping_manager.file_path)
        except Exception as e:
            print(f"Mapping sync failed: {e}")

    def upload_and_sync(self, password_manager, mapping_manager):
        if not self.client:
            print("WebDAV not configured.")
            return

        try:
            # 下载远程文件到本地临时文件
            remote_files = {'passwords.txt': 'temp_pwd.txt', 'mappings.json': 'temp_map.json'}
            for remote, local in remote_files.items():
                try:
                    self.client.download(remote, local)
                except Exception as e:
                    print(f"Remote file {remote} not found or download failed: {e}")
                    # 如果远程文件不存在，创建一个空的本地文件
                    with open(local, 'w') as f:
                        if remote == 'passwords.txt':
                            f.write('')
                        elif remote == 'mappings.json':
                            f.write('{}')

            # 合并密码本
            with open('temp_pwd.txt', 'r') as f:
                remote_pwd = [line.strip() for line in f if line.strip()]
            password_manager.merge(remote_pwd)

            # 合并映射
            with open('temp_map.json', 'r') as f:
                remote_map = json.load(f)
            mapping_manager.mappings.update(remote_map)
            mapping_manager._save()

            # 上传合并后的文件到远程
            self.client.upload('passwords.txt', password_manager.file_path)
            self.client.upload('mappings.json', mapping_manager.file_path)
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