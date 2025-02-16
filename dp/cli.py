import cmd
import json
import os
import threading
import time
from dp.core.config import ConfigManager
from dp.core.password_manager import PasswordManager
from dp.core.mapping_manager import MappingManager
from dp.core.webdav import WebDAVClient
from dp.core.extractor import Extractor

class DpCLI(cmd.Cmd):
    prompt = '(dp) '
    intro = 'Smart Decompression Tool - Type help for commands'

    def __init__(self):
        super().__init__()
        self.config = ConfigManager()
        self.pwd_manager = PasswordManager(self.config.get_local_config()['password_file'])
        self.map_manager = MappingManager(self.config.get_local_config()['mapping_file'])
        self.webdav = WebDAVClient(self.config.get_webdav_config())
        self.extractor = Extractor()
        self.sync_thread = None
        self._is_online = False  # 初始状态为 Local
        self._start_sync()

    def _start_sync(self):
        if self._is_online:
            self.sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
            self.sync_thread.start()

    def _sync_loop(self):
        while self._is_online:  # 仅在 Online 状态下同步
            self.webdav.sync(self.pwd_manager, self.map_manager)
            time.sleep(600)  # 10 minutes

    def do_webdav(self, arg):
        """Set WebDAV credentials: webdav [url|username|password] <value>"""
        args = arg.split()
        if len(args) != 2:
            print("Invalid format. Usage: webdav [url|username|password] <value>")
            return
        
        key, value = args
        if key not in ['url', 'username', 'password']:
            print("Invalid key. Must be one of: url, username, password")
            return
        
        webdav_config = self.config.get_webdav_config()
        webdav_config[key] = value
        self.config.update_webdav_config(
            url=webdav_config['url'],
            username=webdav_config['username'],
            password=webdav_config['password']
        )
        print(f"WebDAV {key} updated.")

    def do_login(self, arg):
        """Login to WebDAV: login"""
        webdav_config = self.config.get_webdav_config()
        url = webdav_config['url']
        username = webdav_config['username']
        password = webdav_config['password']

        if not url or not username or not password:
            print("Error: WebDAV URL, username, and password must be set.")
            print("Use the following commands to set them:")
            print("  webdav url <url>")
            print("  webdav username <username>")
            print("  webdav password <password>")
            return

        try:
            # 初始化 WebDAV 客户端
            self.webdav = WebDAVClient(webdav_config)
            print("Successfully logged in to WebDAV.")
            self._is_online = True  # 登录成功，状态为 Online
            # 登录后立即同步一次
            # self.webdav.list_remote_files('')
            self.webdav.sync(self.pwd_manager, self.map_manager)
            print("Initial sync completed.")
            # 启动同步线程
            self._start_sync()
        except Exception as e:
            print(f"Login failed: {e}")
            self._is_online = False  # 登录失败，状态为 Local

    def do_add(self, arg):
        """Add password: add <password> or add <file> <password>"""
        args = arg.split()
        if len(args) == 1:
            self.pwd_manager.add(args[0])
            print("Password added")
        elif len(args) == 2:
            self.map_manager.add(*args)
            print("Mapping added")
        else:
            print("Invalid arguments")

    def do_import(self, arg):
        """Import data: import [passwords|mappings] <file>"""
        args = arg.split()
        if len(args) != 2:
            print("Usage: import [passwords|mappings] <file>")
            return
        
        if args[0] == 'passwords':
            with open(args[1], 'r') as f:
                self.pwd_manager.merge([line.strip() for line in f])
            print("Passwords imported")
        elif args[0] == 'mappings':
            with open(args[1], 'r') as f:
                self.map_manager.mappings.update(json.load(f))
            self.map_manager._save()
            print("Mappings imported")

    def do_export(self, arg):
        """Export data: export [directory]"""
        dir = arg or '.'
        os.makedirs(dir, exist_ok=True)
        # Export passwords
        with open(f"{dir}/passwords.txt", 'w') as f:
            f.write('\n'.join(self.pwd_manager.passwords))
        # Export mappings
        with open(f"{dir}/mappings.json", 'w') as f:
            json.dump(self.map_manager.mappings, f)
        print(f"Data exported to {dir}")

    def default(self, line):
        """Handle file decompression: <file> [output_dir]"""
        args = line.split()
        if len(args) not in (1, 2):
            print("Invalid command")
            return
        
        file_path = args[0]
        output_dir = args[1] if len(args) == 2 else None
        
        # Try known passwords
        passwords = [None] + self.pwd_manager.passwords
        for pwd in passwords:
            if self.extractor.extract(file_path, output_dir, pwd):
                print(f"Successfully extracted with password: {pwd}")
                if pwd:
                    self.map_manager.add(file_path, pwd)
                return
        print("Failed to extract with all passwords")

    def do_exit(self, arg):
        """Exit the program"""
        print("Exiting...")
        return True
    
    def do_upload(self, arg):
        """Upload and sync data to WebDAV: upload"""
        if not self._is_online:
            print("Error: You must be logged in to WebDAV to upload.")
            return

        try:
            self.webdav.upload_and_sync(self.pwd_manager, self.map_manager)
        except Exception as e:
            print(f"Upload failed: {e}")

    def postcmd(self, stop, line):
        # 常驻状态显示
        status = "Online" if self._is_online else "Local"
        print(f"Status: {status}")
        return stop