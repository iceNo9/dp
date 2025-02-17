import configparser
import os
import keyring

class ConfigManager:
    def __init__(self, config_path='data/config.ini'):
        self.config_path = config_path
        self.config = configparser.ConfigParser()
        self._init_config()

    def _init_config(self):
        if not os.path.exists(self.config_path):
            self._create_default_config()
        self.config.read(self.config_path)

    def _create_default_config(self):
        self.config['webdav'] = {
            'url': '',
            'username': '',
            'sync_interval': '10'
        }
        self.config['local'] = {
            'password_file': 'data/passwords.txt',
            'mapping_file': 'data/mappings.json'
        }
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w') as f:
            self.config.write(f)

    def get_webdav_config(self):
        """Retrieve WebDAV config, excluding password (stored in keyring)"""
        url = self.config['webdav']['url']
        username = self.config['webdav']['username']
        password = keyring.get_password('webdav', username)
        return {
            'url': url,
            'username': username,
            'password': password,
            'sync_interval': int(self.config['webdav'].get('sync_interval', '10'))
        }

    def update_webdav_config(self, url, username, password):
        """Update WebDAV config and save the password in keyring"""
        self.config['webdav']['url'] = url
        self.config['webdav']['username'] = username
        # Save password securely in keyring
        keyring.set_password('webdav', username, password)
        with open(self.config_path, 'w') as f:
            self.config.write(f)

    def get_local_config(self):
        return {
            'password_file': self.config['local']['password_file'],
            'mapping_file': self.config['local']['mapping_file']
        }
