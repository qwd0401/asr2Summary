import os
import sys
import shutil
import subprocess
import zipfile
from datetime import datetime

class Deployer:
    def __init__(self):
        self.project_root = os.path.dirname(os.path.abspath(__file__))
        self.build_dir = os.path.join(self.project_root, 'build')
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
    def create_build_directory(self):
        """创建构建目录"""
        if os.path.exists(self.build_dir):
            shutil.rmtree(self.build_dir)
        os.makedirs(self.build_dir)
        print(f"✓ 创建构建目录: {self.build_dir}")
        
    def copy_source_files(self):
        """复制源文件到构建目录"""
        files_to_copy = [
            'app.py',
            'asr2text.py', 
            'meetassistant.py',
            'production_config.py',
            'production_start.py',
            'requirements.txt',
            'templates_config.json'
        ]
        
        dirs_to_copy = ['templates']
        
        # 复制文件
        for file in files_to_copy:
            src = os.path.join(self.project_root, file)
            dst = os.path.join(self.build_dir, file)
            if os.path.exists(src):
                shutil.copy2(src, dst)
                print(f"✓ 复制文件: {file}")
            else:
                print(f"⚠ 文件不存在: {file}")
                
        # 复制目录
        for dir_name in dirs_to_copy:
            src = os.path.join(self.project_root, dir_name)
            dst = os.path.join(self.build_dir, dir_name)
            if os.path.exists(src):
                shutil.copytree(src, dst)
                print(f"✓ 复制目录: {dir_name}")
            else:
                print(f"⚠ 目录不存在: {dir_name}")
                
        # 创建必要的空目录
        for dir_name in ['uploads', 'summaries', 'logs']:
            os.makedirs(os.path.join(self.build_dir, dir_name), exist_ok=True)
            print(f"✓ 创建目录: {dir_name}")
            
    def create_deployment_package(self):
        """创建部署包"""
        package_name = f"meetassistant_deploy_{self.timestamp}.zip"
        package_path = os.path.join(self.project_root, package_name)
        
        with zipfile.ZipFile(package_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(self.build_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arc_name = os.path.relpath(file_path, self.build_dir)
                    zipf.write(file_path, arc_name)
                    
        print(f"✓ 创建部署包: {package_name}")
        return package_path
        
    def create_install_script(self):
        """创建安装脚本"""
        install_script = os.path.join(self.build_dir, 'install.sh')
        
        script_content = '''#!/bin/bash
# 生产环境安装脚本

echo "开始安装 MeetAssistant..."

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到Python3，请先安装Python3"
    exit 1
fi

# 安装依赖
echo "安装Python依赖..."
pip3 install -r requirements.txt

# 设置权限
chmod +x production_start.py

# 创建systemd服务文件（可选）
cat > meetassistant.service << EOF
[Unit]
Description=MeetAssistant Flask Application
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=$(pwd)
ExecStart=/usr/bin/python3 production_start.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo "安装完成！"
echo "启动命令: python3 production_start.py"
echo "或者使用systemd: sudo systemctl enable meetassistant.service && sudo systemctl start meetassistant"
'''
        
        with open(install_script, 'w', encoding='utf-8') as f:
            f.write(script_content)
            
        print("✓ 创建安装脚本: install.sh")
        
    def deploy(self):
        """执行部署流程"""
        print("=== MeetAssistant 部署开始 ===")
        print(f"时间戳: {self.timestamp}")
        
        try:
            self.create_build_directory()
            self.copy_source_files()
            self.create_install_script()
            package_path = self.create_deployment_package()
            
            print("\n=== 部署完成 ===")
            print(f"部署包位置: {package_path}")
            print("\n下一步操作:")
            print("1. 将部署包上传到生产服务器")
            print("2. 解压部署包")
            print("3. 运行 bash install.sh 安装依赖")
            print("4. 运行 python3 production_start.py 启动服务")
            
        except Exception as e:
            print(f"❌ 部署失败: {str(e)}")
            sys.exit(1)

if __name__ == '__main__':
    deployer = Deployer()
    deployer.deploy()