import argparse
import cmd
import json
import os
import threading
import time
import shlex
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

    def parse_args(self, arg):
        """统一参数解析函数"""
        return argparse.ArgumentParser().parse_args(shlex.split(arg))

    def do_webdav(self, arg):
        """Set WebDAV credentials: webdav [url|username|password] <value>"""
        parser = argparse.ArgumentParser(description="Set WebDAV credentials.")
        parser.add_argument('key', type=str, help='url|username|password')
        parser.add_argument('value', type=str, help='The value to set for the key')

        try:
            args = parser.parse_args(shlex.split(arg))
        except SystemExit:
            print("Invalid command format for 'webdav'. Usage: webdav [url|username|password] <value>")
            return
        
        if args.key not in ['url', 'username', 'password']:
            print("Invalid key. Must be one of: url, username, password")
            return

        webdav_config = self.config.get_webdav_config()
        webdav_config[args.key] = args.value
        self.config.update_webdav_config(
            url=webdav_config['url'],
            username=webdav_config['username'],
            password=webdav_config['password']
        )
        print(f"WebDAV {args.key} updated.")

    def do_login(self, arg):
        """Login to WebDAV: login"""
        parser = argparse.ArgumentParser(description="Login to WebDAV.")
        try:
            parser.parse_args(shlex.split(arg))  # No specific args needed
        except SystemExit:
            print("Invalid command format for 'login'. Usage: login")
            return
        
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
            self.webdav.sync(self.pwd_manager, self.map_manager)
            print("Initial sync completed.")
            self._start_sync()
        except Exception as e:
            print(f"Login failed: {e}")
            self._is_online = False  # 登录失败，状态为 Local

    def do_add(self, arg):
        """Add password: add <password> or add <file> <password>"""
        parser = argparse.ArgumentParser(description="Add password or mapping.")
        parser.add_argument('password', type=str, nargs='?', help='Password or file path')
        parser.add_argument('map_password', type=str, nargs='?', help='Password for file mapping')

        try:
            args = parser.parse_args(shlex.split(arg))
        except SystemExit:
            print("Invalid arguments. Usage: add <password> or add <file> <password>")
            return

        if args.password and not args.map_password:
            self.pwd_manager.add(args.password)
            print("Password added")
        elif args.password and args.map_password:
            self.map_manager.add(args.password, args.map_password)
            print("Mapping added")
        else:
            print("Invalid arguments")

    def do_import(self, arg):
        """Import data: import [passwords|mappings] <file>"""
        parser = argparse.ArgumentParser(description="Import passwords or mappings.")
        parser.add_argument('type', type=str, choices=['passwords', 'mappings'], help="Type of data to import")
        parser.add_argument('file', type=str, help="The file to import from")

        try:
            args = parser.parse_args(shlex.split(arg))
        except SystemExit:
            print("Invalid command format for 'import'. Usage: import [passwords|mappings] <file>")
            return

        if args.type == 'passwords':
            with open(args.file, 'r') as f:
                self.pwd_manager.merge([line.strip() for line in f])
            print("Passwords imported")
        elif args.type == 'mappings':
            with open(args.file, 'r') as f:
                self.map_manager.mappings.update(json.load(f))
            self.map_manager._save()
            print("Mappings imported")

    def do_export(self, arg):
        """Export data: export [directory]"""
        parser = argparse.ArgumentParser(description="Export data.")
        parser.add_argument('dir', type=str, nargs='?', default='.', help="Directory to export to")

        try:
            args = parser.parse_args(shlex.split(arg))
        except SystemExit:
            print("Invalid command format for 'export'. Usage: export [directory]")
            return

        os.makedirs(args.dir, exist_ok=True)
        with open(f"{args.dir}/passwords.txt", 'w') as f:
            f.write('\n'.join(self.pwd_manager.passwords))
        with open(f"{args.dir}/mappings.json", 'w') as f:
            json.dump(self.map_manager.mappings, f)
        print(f"Data exported to {args.dir}")

    def do_dp(self, arg):
        """Decompress file: dp <file> [output_dir]"""
        parser = argparse.ArgumentParser(description="File decompression")
        parser.add_argument('file', type=str, help="The file to decompress")
        parser.add_argument('output_dir', type=str, nargs='?', help="The output directory (default: source file's directory)")

        try:
            args = parser.parse_args(shlex.split(arg))
        except SystemExit:
            print("Invalid command format for 'dp'. Usage: dp <file> [output_dir]")
            return

        file_path = args.file
        # 如果没有指定输出目录，则使用源文件的目录，并创建一个同名文件夹
        if not args.output_dir:
            output_dir = os.path.join(os.path.dirname(file_path), os.path.splitext(os.path.basename(file_path))[0])
            os.makedirs(output_dir, exist_ok=True)
        else:
            output_dir = args.output_dir

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

    def default(self, line):
        """Handle unknown commands"""
        print(f"Unknown command: '{line}'. Type 'help' for a list of commands.")
