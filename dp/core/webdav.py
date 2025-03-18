import keyring
from webdav3.client import Client
import json
import io

class WebDAVClient:
    def __init__(self, config):
        self.config = config
        self.client = None
        self.username = config.get('username')
        self.password = self.get_password_from_keyring()
        if config['url']:
            options = {
                'webdav_hostname': config['url'],
                'webdav_login': self.username,
                'webdav_password': self.password
            }
            self.client = Client(options)

    def get_password_from_keyring(self):
        """Retrieve the password securely from the keyring."""
        password = keyring.get_password('webdav', self.username)
        if password is None:
            print("No password found in keyring, prompting for password...")
            password = input(f"Enter password for {self.username}: ")
            keyring.set_password('webdav', self.username, password)
            print("Password saved securely in keyring.")
        return password

    def ensure_remote_directory(self):
        """Ensure remote directory exists"""
        if not self.client:
            return False
        try:
            if not self.client.check("/dav"):
                self.client.mkdir("/dav")
            return True
        except Exception as e:
            print(f"Failed to ensure remote directory: {e}")
            return False

    def sync(self, password_manager, mapping_manager):
        self.list_remote_files()
        if not self.client or not self.ensure_remote_directory():
            return
        
        # Sync passwords
        try:
            remote_pwd_content = self.client.get_file_content('passwords.txt')
            if remote_pwd_content:
                remote_pwd = remote_pwd_content.decode('utf-8').splitlines()
                password_manager.merge(remote_pwd)
        except Exception as e:
            print(f"Password sync failed: {e}")

        # Sync mappings
        try:
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
            # Download remote files into memory
            remote_files = {'passwords.txt': None, 'mappings.json': None}
            for remote in remote_files:
                try:
                    content = self.client.get_file_content(remote)
                    if content:
                        remote_files[remote] = content.decode('utf-8')
                except Exception as e:
                    print(f"Remote file {remote} not found or download failed: {e}")
                    remote_files[remote] = ''  # Set empty if file does not exist

            # Merge password
            if remote_files['passwords.txt']:
                remote_pwd = remote_files['passwords.txt'].splitlines()
                password_manager.merge(remote_pwd)

            # Merge mappings
            if remote_files['mappings.json']:
                remote_map = json.loads(remote_files['mappings.json'])
                mapping_manager.mappings.update(remote_map)
                mapping_manager._save()

            # Upload the merged files to remote
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
        """List files and directories in a remote WebDAV path"""
        try:
            files = self.client.list(path)
            if files:
                print(f"Files and directories in {path}:")
                for file in files:
                    print(file)
            else:
                print(f"No files found in {path}")
        except Exception as e:
            print(f"Failed to list files in {path}: {e}")
