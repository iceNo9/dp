# dp
智能解压，包含本地密码本，映射

<!-- 编译 -->
nuitka --standalone --output-dir=dict --onefile --include-data-files="bin/7z.exe=bin/7z.exe" --include-data-files="bin/7z.dll=bin/7z.dll" .\main.py
