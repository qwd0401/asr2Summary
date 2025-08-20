# MeetAssistant 部署指南

本文档提供了 MeetAssistant 应用的完整部署指南，包括传统部署和容器化部署两种方式。

## 📋 部署前准备

### 系统要求
- Python 3.8+
- 至少 2GB RAM
- 至少 10GB 磁盘空间
- 网络连接（用于安装依赖）

### 环境变量配置
创建 `.env` 文件并配置以下环境变量：
```bash
SECRET_KEY=your-super-secret-key-here
PORT=5000
FLASK_ENV=production
```

## 🚀 方式一：传统部署

### 1. 上传部署包
将生成的 `meetassistant_deploy_*.zip` 文件上传到服务器并解压：
```bash
unzip meetassistant_deploy_*.zip
cd meetassistant_deploy_*/
```

### 2. 安装依赖
```bash
# 安装Python依赖
pip3 install -r requirements.txt

# 或使用安装脚本
bash install.sh
```

### 3. 启动服务
```bash
# 直接启动
python3 production_start.py

# 或使用nohup后台运行
nohup python3 production_start.py > app.log 2>&1 &
```

### 4. 使用systemd管理服务（推荐）
```bash
# 复制服务文件
sudo cp meetassistant.service /etc/systemd/system/

# 启用并启动服务
sudo systemctl daemon-reload
sudo systemctl enable meetassistant
sudo systemctl start meetassistant

# 查看服务状态
sudo systemctl status meetassistant
```

## 🐳 方式二：Docker容器化部署

### 1. 构建镜像
```bash
# 构建Docker镜像
docker build -t meetassistant:latest .

# 或使用Docker Compose
docker-compose build
```

### 2. 启动容器
```bash
# 使用Docker Compose（推荐）
docker-compose up -d

# 或直接使用Docker
docker run -d \
  --name meetassistant \
  -p 5000:5000 \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/summaries:/app/summaries \
  -v $(pwd)/logs:/app/logs \
  -e SECRET_KEY=your-secret-key \
  meetassistant:latest
```

### 3. 查看容器状态
```bash
# 查看运行状态
docker-compose ps

# 查看日志
docker-compose logs -f meetassistant

# 进入容器
docker-compose exec meetassistant bash
```

## 🔧 配置说明

### 生产环境配置
主要配置项在 `production_config.py` 中：
- `DEBUG = False`: 关闭调试模式
- `SECRET_KEY`: 设置安全密钥
- `MAX_CONTENT_LENGTH`: 文件上传大小限制
- 日志和安全配置

### Nginx反向代理配置
如果使用Nginx作为反向代理，请：
1. 修改 `nginx.conf` 中的域名配置
2. 配置SSL证书（生产环境）
3. 调整上传文件大小限制

## 🔍 部署验证

### 1. 健康检查
```bash
# 检查服务是否正常运行
curl http://localhost:5000/

# 检查API接口
curl http://localhost:5000/templates
```

### 2. 功能测试
1. 访问 Web 界面
2. 上传测试音频文件
3. 验证转录和总结功能
4. 检查文件下载功能

### 3. 日志检查
```bash
# 查看应用日志
tail -f logs/production.log

# 查看系统服务日志
sudo journalctl -u meetassistant -f

# 查看Docker日志
docker-compose logs -f
```

## 🛠️ 故障排除

### 常见问题
1. **端口被占用**: 修改配置文件中的端口号
2. **权限问题**: 确保应用有读写uploads和summaries目录的权限
3. **依赖缺失**: 重新安装requirements.txt中的依赖
4. **内存不足**: 增加服务器内存或优化配置

### 日志位置
- 应用日志: `logs/production.log`
- 系统日志: `/var/log/syslog`
- Nginx日志: `/var/log/nginx/`
- Docker日志: `docker logs <container_name>`

## 🔄 更新部署

### 传统部署更新
```bash
# 停止服务
sudo systemctl stop meetassistant

# 备份当前版本
cp -r /path/to/app /path/to/app.backup

# 部署新版本
# ... 重复部署步骤 ...

# 启动服务
sudo systemctl start meetassistant
```

### Docker部署更新
```bash
# 重新构建镜像
docker-compose build --no-cache

# 重启服务
docker-compose down
docker-compose up -d
```

## 📊 监控和维护

### 性能监控
- 使用 `htop` 监控系统资源
- 监控磁盘空间使用情况
- 定期清理日志文件

### 备份策略
- 定期备份 `uploads` 和 `summaries` 目录
- 备份配置文件
- 备份数据库（如果使用）

### 安全建议
- 定期更新系统和依赖包
- 配置防火墙规则
- 使用HTTPS（生产环境）
- 定期更换SECRET_KEY

---

如有问题，请查看日志文件或联系技术支持。