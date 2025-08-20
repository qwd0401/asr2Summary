#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生产环境启动脚本
用于在生产环境中启动Flask应用
"""

import os
import sys
import logging
from production_config import ProductionConfig

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app

def setup_production_logging():
    """配置生产环境日志"""
    logging.basicConfig(
        level=getattr(logging, ProductionConfig.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(ProductionConfig.LOG_FILE),
            logging.StreamHandler(sys.stdout)
        ]
    )

def main():
    """主函数"""
    # 设置生产环境配置
    app.config.from_object(ProductionConfig)
    ProductionConfig.init_app(app)
    
    # 配置日志
    setup_production_logging()
    
    # 启动应用
    print(f"Starting production server on {ProductionConfig.HOST}:{ProductionConfig.PORT}")
    app.run(
        host=ProductionConfig.HOST,
        port=ProductionConfig.PORT,
        debug=ProductionConfig.DEBUG,
        threaded=True
    )

if __name__ == '__main__':
    main()