# 🚀 MeetAssistant - 智能会议助手

[![中文](https://img.shields.io/badge/README-中文-blue)](README.md) [![English](https://img.shields.io/badge/README-English-red)](README_EN.md)

一个基于Flask的智能会议助手系统，提供语音转文字、会议总结和数据管理功能。支持多种会议类型的专业化总结模板，让会议记录更高效、更专业。

## ✨ 核心功能

### 🎤 语音处理
- **多格式支持**: 支持 MP3、WAV、M4A、FLAC 等主流音频格式
- **高精度转录**: 基于先进的语音识别技术，提供准确的语音转文字服务
- **大文件处理**: 支持最大 100MB 的音频文件上传
- **实时进度**: 处理过程中提供实时进度反馈

### 📝 智能总结
- **多模板支持**: 内置8种专业会议模板
  - 🏢 **产品会议**: 产品规划、需求讨论、功能评审
  - 🤝 **商务会议**: 商务谈判、合作洽谈、销售会议
  - 🔧 **技术会议**: 技术评审、架构设计、代码审查
  - 👥 **管理会议**: 团队管理、项目管理、战略规划
  - 📈 **市场营销**: 市场策略、营销活动、品牌推广
  - 💰 **财务会议**: 财务分析、预算规划、成本控制
  - 🧪 **用例评审**: 测试用例评审、测试策略制定
  - 📋 **需求评审**: 需求分析、需求变更讨论
  - 📄 **通用会议**: 适用于各种一般性会议场景

- **结构化输出**: 生成包含议题、决策、任务清单、风险识别等结构化内容
- **专业术语**: 针对不同会议类型使用相应的专业术语和表达方式

### 🌐 Web界面
- **直观操作**: 拖拽上传、一键处理、实时反馈
- **统一仪表板**: 集成使用统计和数据库管理功能
- **响应式设计**: 支持桌面和移动设备访问
- **文件管理**: 自动保存处理结果，支持批量下载

### 📊 数据统计
- **使用分析**: 详细的API调用统计和性能指标
- **错误监控**: 实时错误追踪和日志记录
- **可视化图表**: 直观的数据展示和趋势分析

### 🗄️ 数据管理
- **SQLite数据库**: 轻量级数据存储解决方案
- **数据备份**: 支持数据库备份和恢复
- **管理界面**: 提供完整的数据库管理功能

## 🛠️ 技术栈

- **后端框架**: Flask 2.3.3
- **数据库**: SQLite
- **前端**: HTML5 + CSS3 + JavaScript
- **图表库**: Chart.js
- **HTTP客户端**: Requests 2.31.0
- **Web服务器**: Werkzeug 2.3.7

## 📦 快速开始

### 环境要求
- Python 3.8+
- 至少 2GB RAM
- 至少 10GB 磁盘空间

### 安装步骤

1. **克隆项目**
   ```bash
   git clone https://github.com/qwd0401/asr2Summary.git
   cd asr2Summary
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **启动服务**
   ```bash
   python app.py
   ```

4. **访问应用**
   - 主页面: http://localhost:5000
   - 统一仪表板: http://localhost:5000/unified_dashboard
   - API文档: 查看 [API_README.md](API_README.md)

## 🎯 使用指南

### Web界面使用

1. **上传音频文件**
   - 访问主页 http://localhost:5000
   - 拖拽音频文件到上传区域或点击选择文件
   - 支持的格式：MP3、WAV、M4A、FLAC等

2. **处理音频**
   - 点击"开始处理"按钮
   - 系统将自动完成语音转录和会议总结
   - 可随时点击"取消处理"中断任务

3. **查看结果**
   - 处理完成后可在线查看转录文本和会议总结
   - 支持下载生成的文件（.txt 和 .md 格式）

4. **数据统计**
   - 点击"📊 查看使用统计"访问统一仪表板
   - 查看详细的使用数据和性能指标
   - 管理数据库和系统设置

### API调用

详细的API文档请参考 [API_README.md](API_README.md)，包含：
- 文件上传接口
- 语音转录接口
- 会议总结接口
- 一键处理接口
- 统计数据接口

## 📁 项目结构

```
meetassistant/
├── app.py                 # 主应用程序
├── app_db.py             # 数据库管理应用
├── asr2text.py           # 语音转文字模块
├── meetassistant.py      # 核心处理逻辑
├── database.py           # 数据库操作
├── compression_utils.py  # 文件压缩工具
├── templates/            # HTML模板
│   ├── index.html        # 主页面
│   ├── dashboard.html    # 管理仪表板
│   └── unified_dashboard.html # 统一仪表板
├── templates_config.json # 会议模板配置
├── uploads/              # 上传文件目录
├── summaries/            # 处理结果目录
├── logs/                 # 日志文件目录
├── requirements.txt      # Python依赖
├── API_README.md         # API文档
├── DEPLOYMENT.md         # 部署指南
└── README.md            # 项目说明
```

## 🚀 部署指南

### 开发环境
```bash
# 启动开发服务器
python app.py
```

### 生产环境
详细的生产环境部署指南请参考 [DEPLOYMENT.md](DEPLOYMENT.md)，包含：
- 传统部署方式
- Docker容器化部署
- Nginx反向代理配置
- 系统服务配置

### Docker部署
```bash
# 构建镜像
docker build -t meetassistant .

# 运行容器
docker run -p 5000:5000 meetassistant

# 或使用docker-compose
docker-compose up -d
```

## 📊 功能特色

### 🎯 专业化模板
- 针对不同行业和会议类型定制的专业模板
- 结构化输出格式，便于后续处理和归档
- 支持自定义模板扩展

### 📈 数据洞察
- 实时使用统计和性能监控
- 错误追踪和日志分析
- 可视化数据展示

### 🔧 易于集成
- RESTful API设计，易于第三方集成
- 完整的API文档和示例代码
- 支持批量处理和自动化工作流

## 🤝 贡献指南

欢迎提交Issue和Pull Request来帮助改进项目！

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 📞 支持与反馈

如果您在使用过程中遇到问题或有改进建议，请：
- 提交 [Issue](../../issues)
- 发送邮件至项目维护者
- 查看 [API文档](API_README.md) 和 [部署指南](DEPLOYMENT.md)

---

**MeetAssistant** - 让会议记录更智能，让工作更高效！ 🚀
