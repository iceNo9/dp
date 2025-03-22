# dp
智能解压，包含本地密码本，映射

<!-- 编译 -->
nuitka --standalone --output-dir=dict --onefile --include-data-files="bin/7za.exe=bin/7za.exe" .\main.py
nuitka --standalone --onefile --include-data-files="bin/7za.exe=bin/7za.exe" your_script.py
