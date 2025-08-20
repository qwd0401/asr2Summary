#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
会议助手 Flask 服务启动脚本

使用方法:
    python start_server.py
    
或者:
    python start_server.py --port 8080 --debug
"""

import argparse
import os
import sys
from app import app

def check_dependencies():
    """检查依赖包是否安装"""
    required_packages = ['flask', 'requests', 'werkzeug']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ 缺少以下依赖包:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n请运行以下命令安装依赖:")
        print("   pip install -r requirements.txt")
        return False
    
    return True

def create_directories():
    """创建必要的目录"""
    directories = ['uploads', 'summaries', 'templates']
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"✅ 创建目录: {directory}")

def main():
    parser = argparse.ArgumentParser(description='启动会议助手 Flask 服务')
    parser.add_argument('--port', type=int, default=8181, help='端口号 (默认: 8181)')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='服务主机 (默认: 0.0.0.0)')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    parser.add_argument('--no-check', action='store_true', help='跳过依赖检查')
    
    args = parser.parse_args()
    
    print("🚀 启动会议助手 Flask 服务...")
    print("=" * 50)
    
    # 检查依赖
    if not args.no_check and not check_dependencies():
        sys.exit(1)
    
    # 创建必要目录
    create_directories()
    
    print(f"\n📡 服务配置:")
    print(f"   主机: {args.host}")
    print(f"   端口: {args.port}")
    print(f"   调试模式: {'开启' if args.debug else '关闭'}")
    
    print(f"\n🌐 访问地址:")
    if args.host == '0.0.0.0':
        print(f"   本地访问: http://localhost:{args.port}")
        print(f"   网络访问: http://127.0.0.1:{args.port}")
    else:
        print(f"   访问地址: http://{args.host}:{args.port}")
    
    print(f"\n📚 API文档: http://localhost:{args.port}/api")
    
    print("\n" + "=" * 50)
    print("按 Ctrl+C 停止服务")
    print("=" * 50)
    
    try:
        app.run(
            host=args.host,
            port=args.port,
            debug=args.debug,
            threaded=True
        )
    except KeyboardInterrupt:
        print("\n\n👋 服务已停止")
    except Exception as e:
        print(f"\n❌ 服务启动失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()