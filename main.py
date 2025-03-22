import argparse
from pathlib import Path
from log_config import logger
from config.settings import DATA_DIR  # 调整导入路径
from password_manager.manager import PasswordManager  # 调整导入路径
from archive.handler import ArchiveHandler  # 调整导入路径

def main():
    parser = argparse.ArgumentParser(description="DP - 文件处理工具")
    
    # 密码管理参数
    parser.add_argument("-a", "--add", metavar="PASSWORD", help="添加密码到全局库")
    parser.add_argument("-d", "--delete", metavar="PASSWORD", help="从全局库删除密码")
    parser.add_argument("--import_pass", metavar="DIR", help="导入密码文件")
    parser.add_argument("--import_map", metavar="DIR", help="导入密码映射文件")
    parser.add_argument("--export_pass", metavar="DIR", nargs="?", const="password_out")
    parser.add_argument("--export_map", metavar="DIR", nargs="?", const="map_out")
    parser.add_argument("--export", metavar="DIR", nargs="?", const="out")
    
    # 解压参数
    parser.add_argument("source", nargs="?", help="源文件路径")
    parser.add_argument("dest", nargs="?", help="目标目录")

    args = parser.parse_args()
    # args.source = r"C:\Users\hupo9\Downloads\新建文件夹\电xspy - 副本.rar"

    
    password_manager = PasswordManager()
    archive_handler = ArchiveHandler()

    # 处理密码管理操作
    if args.add:
        password_manager.add_password(args.add)
    elif args.delete:
        password_manager.delete_password(args.delete)
    elif args.import_pass:
        password_manager.import_passwords(Path(args.import_pass))
    elif args.import_map:
        password_manager.import_mappings(Path(args.import_map))  # 处理导入密码映射
    elif args.export_pass:
        output_dir = Path(args.export_pass) if args.export_pass != "password_out" else Path.cwd() / "password_out"
        output_dir.mkdir(exist_ok=True)
        password_manager.export_passwords(output_dir)
    elif args.export_map:
        output_dir = Path(args.export_map) if args.export_map != "map_out" else Path.cwd() / "map_out"
        output_dir.mkdir(exist_ok=True)
        password_manager.export_mappings(output_dir)
    elif args.export:
        output_dir = Path(args.export) if args.export != "out" else Path.cwd() / "out"
        output_dir.mkdir(exist_ok=True)
        password_manager.export_passwords(output_dir)
        password_manager.export_mappings(output_dir)
    elif args.source:
        source_path = Path(args.source)
        dest_path = Path(args.dest) if args.dest else source_path.with_suffix("")
        archive_handler.extract(source_path, dest_path)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
