# 生产环境配置文件
import os


class ProductionConfig:
    # Flask配置
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.environ.get("SECRET_KEY", "your-production-secret-key-here")

    # 服务器配置
    HOST = "0.0.0.0"
    PORT = int(os.environ.get("PORT", 5000))

    # 文件上传配置
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
    SUMMARIES_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "summaries")

    # 日志配置
    LOG_LEVEL = "INFO"
    LOG_FILE = "logs/production.log"

    # 安全配置
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    @staticmethod
    def init_app(app):
        # 确保必要的目录存在
        os.makedirs(ProductionConfig.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(ProductionConfig.SUMMARIES_FOLDER, exist_ok=True)
        os.makedirs(os.path.dirname(ProductionConfig.LOG_FILE), exist_ok=True)
