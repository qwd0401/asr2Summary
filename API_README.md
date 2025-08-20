# 会议助手 Flask API 服务

这是一个基于Flask的会议助手后端服务，提供语音转文字和会议总结功能的RESTful API接口。

## 功能特性

- 🎤 **音频转录**: 支持多种音频格式的语音转文字
- 📝 **会议总结**: 基于转录内容生成结构化会议总结
- 🔄 **一键处理**: 上传音频文件，自动完成转录和总结
- ❌ **中断处理**: 支持取消正在进行的处理任务
- ⬇️ **自动下载**: 处理完成后可选择自动下载生成的文件
- 📁 **文件管理**: 自动保存处理结果，支持文件下载
- 🌐 **Web界面**: 提供友好的网页操作界面
- 📊 **RESTful API**: 完整的API接口，支持程序化调用
- 📈 **使用统计**: 多维度记录和展示工具使用情况
- 📝 **日志记录**: 详细的请求日志和错误追踪

### Web界面功能

访问 `http://localhost:8181` 可以使用Web界面：

- 拖拽或点击上传音频文件
- 实时显示文件信息和处理进度
- **中断处理**: 处理过程中可随时点击"取消处理"按钮中断任务
- 查看转录和总结结果
- **自动下载**: 处理完成后弹出确认对话框，可选择自动下载生成的文件
- 手动下载生成的文件
- **使用统计**: 点击"📊 查看使用统计"查看详细的使用数据和性能指标

## 🚀 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 启动服务
```bash
python app.py
```

服务将在 `http://localhost:5000` 启动

## 📡 API 接口文档

### 1. 服务状态检查
**GET** `/`

返回API服务信息和可用接口列表。

**响应示例：**
```json
{
  "message": "会议助手 API 服务",
  "version": "1.0.0",
  "endpoints": {
    "/upload": "POST - 上传音频文件进行语音转文字",
    "/transcribe": "POST - 直接提供音频文件路径进行转录",
    "/summarize": "POST - 基于转录文本生成会议总结",
    "/process": "POST - 一键处理：上传音频 -> 转录 -> 生成总结",
    "/summaries": "GET - 获取所有总结文件列表",
            "/download/<filename>": "GET - 下载指定的总结文件",
            "/stats": "GET - 获取使用统计数据",
            "/stats/dashboard": "GET - 统计数据仪表板页面"
  }
}
```

### 2. 上传音频文件转录
**POST** `/upload`

上传音频文件并进行语音转文字。

**请求参数：**
- `file`: 音频文件（支持格式：wav, mp3, pcm, opus, webm）

**响应示例：**
```json
{
  "success": true,
  "transcription": "这是转录的文本内容...",
  "audio_file": "20241201_143022_meeting.mp3",
  "transcription_file": "transcription_20241201_143022.txt"
}
```

### 3. 基于文件路径转录
**POST** `/transcribe`

基于提供的音频文件路径进行转录。

**请求体：**
```json
{
  "audio_path": "/path/to/audio/file.mp3"
}
```

**响应示例：**
```json
{
  "success": true,
  "transcription": "这是转录的文本内容..."
}
```

### 4. 生成会议总结
**POST** `/summarize`

基于转录文本生成会议总结。

**请求体：**
```json
{
  "transcription": "这是需要总结的会议转录文本..."
}
```

**响应示例：**
```json
{
  "success": true,
  "summary": "# 会议总结\n\n## 📱 会议概览\n...",
  "summary_file": "meeting_summary_20241201_143022.md"
}
```

### 5. 一键处理（推荐）
**POST** `/process`

上传音频文件，自动完成转录和总结生成。

**请求参数：**
- `file`: 音频文件

**响应示例：**
```json
{
  "success": true,
  "transcription": "这是转录的文本内容...",
  "summary": "# 会议总结\n\n## 📱 会议概览\n...",
  "files": {
    "audio": "20241201_143022_meeting.mp3",
    "transcription": "transcription_20241201_143022.txt",
    "summary": "meeting_summary_20241201_143022.md"
  }
}
```

### 6. 获取总结文件列表
**GET** `/summaries`

获取所有已生成的会议总结文件列表。

**响应示例：**
```json
{
  "summaries": [
    {
      "filename": "meeting_summary_20241201_143022.md",
      "size": 2048,
      "created_time": "2024-12-01 14:30:22",
      "modified_time": "2024-12-01 14:30:22"
    }
  ]
}
```

### 7. 下载总结文件
**GET** `/download/<filename>`

下载指定的会议总结文件。

**示例：**
```
GET /download/meeting_summary_20241201_143022.md
```

## 🗂️ 文件结构

```
/Users/qwd/Desktop/code/
├── app.py                 # Flask应用主文件
├── requirements.txt       # Python依赖包
├── API_README.md         # API文档
├── uploads/              # 上传的音频文件目录
└── summaries/            # 转录文件和总结文件目录
    ├── transcription_*.txt
    └── meeting_summary_*.md
```

## 🔧 配置说明

### 文件上传限制
- 最大文件大小：100MB
- 支持格式：wav, mp3, pcm, opus, webm

### API密钥配置
请在 `app.py` 中更新以下API密钥：
- 语音转文字API密钥（第32行和第126行）
- 会议总结API密钥（第94行）

## 📝 使用示例

### 使用curl命令测试

1. **检查服务状态：**
```bash
curl http://localhost:5000/
```

2. **上传音频文件进行一键处理：**
```bash
curl -X POST -F "file=@meeting.mp3" http://localhost:5000/process
```

3. **获取总结文件列表：**
```bash
curl http://localhost:5000/summaries
```

4. **下载总结文件：**
```bash
curl -O http://localhost:5000/download/meeting_summary_20241201_143022.md
```

### 使用Python requests

```python
import requests

# 一键处理音频文件
with open('meeting.mp3', 'rb') as f:
    files = {'file': f}
    response = requests.post('http://localhost:5000/process', files=files)
    result = response.json()
    print(result)
```

## 🚨 注意事项

1. **API密钥安全**：请妥善保管API密钥，不要提交到公共代码仓库
2. **文件存储**：上传的文件和生成的总结会保存在本地，请定期清理
3. **网络连接**：需要稳定的网络连接访问外部API服务
4. **文件格式**：确保上传的音频文件格式正确且质量良好

## 🔄 从原有脚本迁移

原有的 `asr2text.py` 和 `meetassistant.py` 功能已完全集成到Flask API中：
- `asr2text.py` → `/upload` 或 `/transcribe` 接口
- `meetassistant.py` → `/summarize` 接口
- 完整流程 → `/process` 接口（推荐使用）

现在您可以通过HTTP API调用这些功能，支持远程访问和集成到其他应用中。