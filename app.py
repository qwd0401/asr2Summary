from flask import Flask, request, jsonify, send_file, render_template
from werkzeug.utils import secure_filename
import os
import requests
import datetime
import time
import json
import logging
import zipfile
from pathlib import Path
from functools import wraps

app = Flask(__name__)

# 配置
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size
ALLOWED_EXTENSIONS = {'wav', 'mp3', 'pcm', 'opus', 'webm'}

# 确保上传目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('summaries', exist_ok=True)
os.makedirs('logs', exist_ok=True)

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 使用统计数据存储
USAGE_STATS_FILE = 'logs/usage_stats.json'

def load_usage_stats():
    """加载使用统计数据"""
    if os.path.exists(USAGE_STATS_FILE):
        try:
            with open(USAGE_STATS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {
        'total_requests': 0,
        'successful_requests': 0,
        'failed_requests': 0,
        'total_processing_time': 0,
        'total_file_size': 0,
        'endpoints': {},
        'daily_stats': {},
        'file_types': {},
        'error_types': {},
        'recent_activities': []
    }

def save_usage_stats(stats):
    """保存使用统计数据"""
    try:
        with open(USAGE_STATS_FILE, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"保存统计数据失败: {e}")

def log_request(endpoint):
    """请求日志装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = time.time()
            request_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            
            # 记录请求开始
            logger.info(f"[{request_id}] 开始处理 {endpoint} 请求")
            
            # 获取文件信息
            file_size = 0
            file_type = None
            if 'file' in request.files:
                file = request.files['file']
                if file and file.filename:
                    file_size = len(file.read())
                    file.seek(0)  # 重置文件指针
                    file_type = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'unknown'
            
            try:
                # 执行原函数
                result = f(*args, **kwargs)
                processing_time = time.time() - start_time
                
                # 判断是否成功
                is_success = True
                if hasattr(result, 'status_code'):
                    is_success = result.status_code < 400
                elif isinstance(result, tuple) and len(result) > 1:
                    is_success = result[1] < 400
                
                # 记录统计数据
                stats = load_usage_stats()
                today = datetime.datetime.now().strftime("%Y-%m-%d")
                
                stats['total_requests'] += 1
                if is_success:
                    stats['successful_requests'] += 1
                else:
                    stats['failed_requests'] += 1
                
                stats['total_processing_time'] += processing_time
                stats['total_file_size'] += file_size
                
                # 端点统计
                if endpoint not in stats['endpoints']:
                    stats['endpoints'][endpoint] = {'count': 0, 'success': 0, 'total_time': 0, 'avg_time': 0}
                stats['endpoints'][endpoint]['count'] += 1
                stats['endpoints'][endpoint]['total_time'] += processing_time
                stats['endpoints'][endpoint]['avg_time'] = stats['endpoints'][endpoint]['total_time'] / stats['endpoints'][endpoint]['count']
                if is_success:
                    stats['endpoints'][endpoint]['success'] += 1
                
                # 每日统计
                if today not in stats['daily_stats']:
                    stats['daily_stats'][today] = {'requests': 0, 'success': 0, 'processing_time': 0, 'file_size': 0}
                stats['daily_stats'][today]['requests'] += 1
                if is_success:
                    stats['daily_stats'][today]['success'] += 1
                stats['daily_stats'][today]['processing_time'] += processing_time
                stats['daily_stats'][today]['file_size'] += file_size
                
                # 文件类型统计
                if file_type:
                    if file_type not in stats['file_types']:
                        stats['file_types'][file_type] = {'count': 0, 'total_size': 0}
                    stats['file_types'][file_type]['count'] += 1
                    stats['file_types'][file_type]['total_size'] += file_size
                
                # 最近活动记录（保留最近50条）
                activity = {
                    'timestamp': datetime.datetime.now().isoformat(),
                    'endpoint': endpoint,
                    'success': is_success,
                    'processing_time': round(processing_time, 3),
                    'file_size': file_size,
                    'file_type': file_type,
                    'request_id': request_id
                }
                stats['recent_activities'].insert(0, activity)
                stats['recent_activities'] = stats['recent_activities'][:50]
                
                save_usage_stats(stats)
                
                logger.info(f"[{request_id}] {endpoint} 请求完成 - 耗时: {processing_time:.3f}s, 成功: {is_success}")
                return result
                
            except Exception as e:
                processing_time = time.time() - start_time
                
                # 记录错误统计
                stats = load_usage_stats()
                stats['total_requests'] += 1
                stats['failed_requests'] += 1
                
                error_type = type(e).__name__
                if error_type not in stats['error_types']:
                    stats['error_types'][error_type] = 0
                stats['error_types'][error_type] += 1
                
                save_usage_stats(stats)
                
                logger.error(f"[{request_id}] {endpoint} 请求失败 - 耗时: {processing_time:.3f}s, 错误: {str(e)}")
                raise
                
        return decorated_function
    return decorator

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_unique_filename(base_name="meeting_summary", extension=".md", directory="summaries"):
    """生成唯一的文件名（避免覆盖）"""
    timestamp = datetime.datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    filename = f"{base_name}_{timestamp}{extension}"
    filepath = os.path.join(directory, filename)
    
    # 如果文件仍然存在，添加序号
    counter = 1
    while os.path.exists(filepath):
        filename = f"{base_name}_{timestamp}_{counter:02d}{extension}"
        filepath = os.path.join(directory, filename)
        counter += 1
    
    return filepath

def create_zip_file(transcription_file, summary_file, audio_filename, timestamp=None):
    """创建包含转录文件和总结文件的zip文件"""
    if timestamp is None:
        timestamp = datetime.datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    
    zip_filename = f"meeting_files_{timestamp}.zip"
    zip_path = os.path.join('summaries', zip_filename)
    
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 添加转录文件
            if os.path.exists(transcription_file):
                zipf.write(transcription_file, os.path.basename(transcription_file))
            
            # 添加总结文件
            if os.path.exists(summary_file):
                zipf.write(summary_file, os.path.basename(summary_file))
            
            # 添加原始音频文件信息（创建一个info.txt文件）
            # 使用传入的时间戳确保时间一致性
            timestamp_obj = datetime.datetime.strptime(timestamp, "%Y%m%d_%H%M%S")
            formatted_time = timestamp_obj.strftime('%Y-%m-%d %H:%M:%S')
            info_content = f"原始音频文件: {audio_filename}\n生成时间: {formatted_time}\n"
            zipf.writestr("info.txt", info_content)
        
        logger.info(f"ZIP文件创建成功: {zip_filename}")
        return zip_filename
    except Exception as e:
        logger.error(f"创建ZIP文件失败: {str(e)}")
        return None

def speech_to_text(audio_file_path):
    """语音转文字功能"""
    url = "https://api.siliconflow.cn/v1/audio/transcriptions"
    
    try:
        # 检查文件是否存在
        if not os.path.exists(audio_file_path):
            logger.error(f"音频文件不存在: {audio_file_path}")
            return {"error": f"音频文件不存在: {audio_file_path}"}
        
        # 检查文件大小
        file_size = os.path.getsize(audio_file_path)
        logger.info(f"开始转录音频文件: {audio_file_path}, 大小: {file_size} bytes")
        
        with open(audio_file_path, 'rb') as f:
            files = {"file": f}
            data = {"model": "FunAudioLLM/SenseVoiceSmall"}
            headers = {
                "Authorization": "Bearer sk-breyqcjehyljoocgimftfmhndccaxntudloarkfpdqlwjqxs"
            }
            
            try:
                logger.info(f"发送转录请求到: {url}")
                response = requests.post(url, files=files, data=data, headers=headers, timeout=300)
                logger.info(f"转录API响应状态码: {response.status_code}")
                
                response.raise_for_status()
                result = response.json()
                logger.info("转录API调用成功")
                return result
            except requests.exceptions.Timeout:
                logger.error("转录API请求超时")
                return {"error": "转录API请求超时，请稍后重试"}
            except requests.exceptions.HTTPError as e:
                logger.error(f"转录API HTTP错误: {e}, 响应内容: {response.text if 'response' in locals() else 'N/A'}")
                return {"error": f"转录API HTTP错误: {str(e)}"}
            except requests.exceptions.RequestException as e:
                logger.error(f"转录API请求异常: {str(e)}")
                return {"error": f"转录API请求失败: {str(e)}"}
    except Exception as e:
        logger.error(f"转录函数异常: {str(e)}")
        return {"error": f"转录函数异常: {str(e)}"}

def load_templates_config():
    """加载模板配置"""
    try:
        with open('templates_config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载模板配置失败: {str(e)}")
        return None

def generate_meeting_summary(transcription_text, template_type="product"):
    """生成会议总结"""
    url = "https://api.linkapi.org/v1/chat/completions"
    
    # 加载模板配置
    templates_config = load_templates_config()
    if not templates_config or template_type not in templates_config['templates']:
        logger.warning(f"模板 {template_type} 不存在，使用默认产品模板")
        template_type = "product"
    
    # 获取对应模板的提示词
    if templates_config and template_type in templates_config['templates']:
        system_prompt = templates_config['templates'][template_type]['prompt']
    else:
        # 默认产品模板提示词
        system_prompt = """
# CONTEXT (背景)
你是一位资深的互联网产品专家，专门负责产品会议记录和总结，深度理解产品开发流程、用户需求分析、技术实现和业务目标。

# OBJECTIVE (目标)
基于提供的产品会议转录内容，生成一份面向产品团队的结构化会议总结，重点关注产品决策、功能规划、用户体验和项目推进。

# STYLE (风格)
采用互联网产品团队常用的简洁明了风格，重点突出可执行性，使用产品术语和敏捷开发语言。

# TONE (语调)
保持务实、高效、目标导向的语调，关注用户价值和业务影响，体现产品思维。

# AUDIENCE (受众)
面向产品经理、开发工程师、设计师、测试工程师、运营同学等产品团队成员。

# RESPONSE (响应格式)
请严格按照以下Markdown格式输出：

## 📱 会议概览
- **会议类型**：[产品评审/需求讨论/迭代规划/用户反馈/技术方案等]
- **产品模块**：[涉及的产品功能模块]
- **参与角色**：[PM/开发/设计/测试/运营等]
- **会议时长**：[如果能推断出来]

## 🎯 产品议题
[按优先级排序，列出主要产品议题，如功能需求、用户体验、技术方案等]

## ✅ 产品决策
[明确列出产品相关决策，包括功能取舍、优先级调整、技术选型等]

## 📋 任务清单
[格式：- **任务描述** | 负责人：@XXX | 预期完成：XXX | 优先级：P0/P1/P2]

## 💭 讨论要点
[记录重要的产品讨论，如用户需求分析、技术可行性、竞品对比等]

## 🚨 风险识别
[产品风险、技术风险、时间风险、用户体验风险等]

## 📅 下步计划
[下个迭代安排、评审时间、上线计划、数据验证等]

## 📊 数据&指标
[如涉及数据分析、用户反馈、业务指标等]

请确保内容准确、完整，如某些信息在转录中不明确，请标注"[待确认]"。对于产品相关的专业术语和缩写，请保持原样。
        """
    
    payload = {
        "model": "gemini-2.5-flash-preview-05-20",
        "temperature": 0.2,
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": f"以下是需要总结的会议转录内容：\n\n{transcription_text}\n\n请按照上述格式要求生成会议总结。"
            }
        ]
    }
    
    headers = {
        "Authorization": "Bearer sk-ceh8SGEq8hYxwKWTE7Fe9e6bB25d4909Bf852396239d7b7d",
        "Content-Type": "application/json"
    }
    
    try:
        logger.info(f"发送总结请求到: {url}")
        logger.info(f"转录文本长度: {len(transcription_text)} 字符")
        
        response = requests.post(url, json=payload, headers=headers, timeout=300)
        logger.info(f"总结API响应状态码: {response.status_code}")
        
        response.raise_for_status()
        result = response.json()
        logger.info("总结API调用成功")
        return result
    except requests.exceptions.Timeout:
        logger.error("总结API请求超时")
        return {"error": "总结API请求超时，请稍后重试"}
    except requests.exceptions.HTTPError as e:
        logger.error(f"总结API HTTP错误: {e}, 响应内容: {response.text if 'response' in locals() else 'N/A'}")
        return {"error": f"总结API HTTP错误: {str(e)}"}
    except requests.exceptions.RequestException as e:
        logger.error(f"总结API请求异常: {str(e)}")
        return {"error": f"总结API请求失败: {str(e)}"}
    except Exception as e:
        logger.error(f"总结函数异常: {str(e)}")
        return {"error": f"总结函数异常: {str(e)}"}

@app.route('/', methods=['GET'])
def index():
    """Web界面首页"""
    return render_template('index.html')

@app.route('/api', methods=['GET'])
def api_info():
    """API信息接口"""
    return jsonify({
        "message": "会议助手 API 服务",
        "version": "1.0.0",
        "endpoints": {
            "/upload": "POST - 上传音频文件进行语音转文字",
            "/transcribe": "POST - 直接提供音频文件路径进行转录",
            "/summarize": "POST - 基于转录文本生成会议总结",
            "/process": "POST - 一键处理：上传音频 -> 转录 -> 生成总结",
            "/templates": "GET - 获取可用的总结模板列表",
            "/summaries": "GET - 获取所有总结文件列表",
            "/download/<filename>": "GET - 下载指定的总结文件"
        }
    })

@app.route('/templates', methods=['GET'])
@log_request('/templates')
def get_templates():
    """获取可用的总结模板列表"""
    try:
        templates_config = load_templates_config()
        if not templates_config:
            return jsonify({"error": "无法加载模板配置"}), 500
        
        # 提取模板信息，只返回必要的字段
        templates = {}
        for key, template in templates_config['templates'].items():
            templates[key] = {
                "name": template['name'],
                "description": template['description']
            }
        
        return jsonify({
            "success": True,
            "templates": templates
        })
    except Exception as e:
        logger.error(f"获取模板列表失败: {str(e)}")
        return jsonify({"error": "获取模板列表失败", "details": str(e)}), 500

@app.route('/upload', methods=['POST'])
@log_request('/upload')
def upload_audio():
    """上传音频文件并进行语音转文字"""
    if 'file' not in request.files:
        return jsonify({"error": "没有上传文件"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "没有选择文件"}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # 进行语音转文字
        result = speech_to_text(filepath)
        
        # 保存转录结果
        if 'text' in result:
            transcription_file = f"transcription_{timestamp}.txt"
            transcription_path = os.path.join('summaries', transcription_file)
            with open(transcription_path, 'w', encoding='utf-8') as f:
                f.write(result['text'])
            
            return jsonify({
                "success": True,
                "transcription": result['text'],
                "audio_file": filename,
                "transcription_file": transcription_file
            })
        else:
            return jsonify({"error": "转录失败", "details": result}), 500
    
    return jsonify({"error": "不支持的文件格式"}), 400

@app.route('/transcribe', methods=['POST'])
@log_request('/transcribe')
def transcribe_audio():
    """基于提供的音频文件路径进行转录"""
    data = request.get_json()
    if not data or 'audio_path' not in data:
        return jsonify({"error": "请提供音频文件路径"}), 400
    
    audio_path = data['audio_path']
    if not os.path.exists(audio_path):
        return jsonify({"error": "音频文件不存在"}), 404
    
    result = speech_to_text(audio_path)
    
    if 'text' in result:
        return jsonify({
            "success": True,
            "transcription": result['text']
        })
    else:
        return jsonify({"error": "转录失败", "details": result}), 500

@app.route('/summarize', methods=['POST'])
@log_request('/summarize')
def summarize_meeting():
    """基于转录文本生成会议总结"""
    data = request.get_json()
    if not data or 'transcription' not in data:
        return jsonify({"error": "请提供转录文本"}), 400
    
    transcription_text = data['transcription']
    template_type = data.get('template', 'product')  # 默认使用产品模板
    
    result = generate_meeting_summary(transcription_text, template_type)
    
    if 'choices' in result:
        summary_content = result['choices'][0]['message']['content']
        
        # 保存总结到文件
        summary_file = generate_unique_filename()
        # 从文件名中提取时间戳，确保生成时间与文件名一致
        import re
        timestamp_match = re.search(r'(\d{8}_\d{6})', summary_file)
        if timestamp_match:
            timestamp_str = timestamp_match.group(1)
            timestamp_obj = datetime.datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
            current_time = timestamp_obj.strftime("%Y-%m-%d %H:%M:%S")
        else:
            current_time = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
        
        # 获取模板名称用于文件标题
        templates_config = load_templates_config()
        template_name = "会议总结"
        if templates_config and template_type in templates_config['templates']:
            template_name = templates_config['templates'][template_type]['name'] + "总结"
        
        markdown_content = f"# {template_name}\n\n**生成时间：** {current_time}\n**使用模板：** {template_name}\n\n{summary_content}\n"
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        return jsonify({
            "success": True,
            "summary": summary_content,
            "template": template_type,
            "summary_file": os.path.basename(summary_file)
        })
    else:
        return jsonify({"error": "生成总结失败", "details": result}), 500

@app.route('/process', methods=['POST'])
@log_request('/process')
def process_audio():
    """一键处理：上传音频 -> 转录 -> 生成总结"""
    try:
        if 'file' not in request.files:
            logger.warning("请求中没有文件")
            return jsonify({"error": "没有上传文件"}), 400
        
        file = request.files['file']
        if file.filename == '':
            logger.warning("没有选择文件")
            return jsonify({"error": "没有选择文件"}), 400
        
        if not (file and allowed_file(file.filename)):
            logger.warning(f"不支持的文件格式: {file.filename}")
            return jsonify({"error": "不支持的文件格式"}), 400
        
        # 获取模板参数
        template_type = request.form.get('template', 'product')  # 默认使用产品模板
        
        # 保存上传的文件
        filename = secure_filename(file.filename)
        timestamp = datetime.datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        try:
            file.save(filepath)
            logger.info(f"文件保存成功: {filepath}")
        except Exception as e:
            logger.error(f"文件保存失败: {str(e)}")
            return jsonify({"error": "文件保存失败", "details": str(e)}), 500
        
        # 步骤1: 语音转文字
        logger.info("开始语音转文字处理")
        try:
            transcription_result = speech_to_text(filepath)
            if 'text' not in transcription_result:
                logger.error(f"转录失败: {transcription_result}")
                return jsonify({"error": "转录失败", "details": transcription_result}), 500
            
            transcription_text = transcription_result['text']
            logger.info(f"转录成功，文本长度: {len(transcription_text)}")
        except Exception as e:
            logger.error(f"转录过程异常: {str(e)}")
            return jsonify({"error": "转录过程异常", "details": str(e)}), 500
        
        # 步骤2: 生成会议总结
        logger.info(f"开始生成会议总结，使用模板: {template_type}")
        try:
            summary_result = generate_meeting_summary(transcription_text, template_type)
            if 'choices' not in summary_result:
                logger.error(f"生成总结失败: {summary_result}")
                return jsonify({"error": "生成总结失败", "details": summary_result}), 500
            
            summary_content = summary_result['choices'][0]['message']['content']
            logger.info("会议总结生成成功")
        except Exception as e:
            logger.error(f"生成总结过程异常: {str(e)}")
            return jsonify({"error": "生成总结过程异常", "details": str(e)}), 500
        
        # 保存文件
        try:
            transcription_file = f"transcription_{timestamp}.txt"
            transcription_path = os.path.join('summaries', transcription_file)
            with open(transcription_path, 'w', encoding='utf-8') as f:
                f.write(transcription_text)
            
            summary_file = generate_unique_filename()
            # 使用与文件名相同的时间戳，确保时间一致性
            timestamp_obj = datetime.datetime.strptime(timestamp, "%Y%m%d_%H%M%S")
            current_time = timestamp_obj.strftime("%Y-%m-%d %H:%M:%S")
            
            # 获取模板名称用于文件标题
            templates_config = load_templates_config()
            template_name = "会议总结"
            if templates_config and template_type in templates_config['templates']:
                template_name = templates_config['templates'][template_type]['name'] + "总结"
            
            markdown_content = f"# {template_name}\n\n**生成时间：** {current_time}\n**使用模板：** {template_name}\n\n{summary_content}\n"
            
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            logger.info(f"文件保存成功: {transcription_file}, {os.path.basename(summary_file)}")
            
            # 创建zip文件，传入timestamp确保时间一致性
            zip_filename = create_zip_file(transcription_path, summary_file, filename, timestamp)
            if not zip_filename:
                logger.warning("ZIP文件创建失败，返回单独文件链接")
                return jsonify({
                    "success": True,
                    "transcription": transcription_text,
                    "summary": summary_content,
                    "template": template_type,
                    "files": {
                        "audio": filename,
                        "transcription": transcription_file,
                        "summary": os.path.basename(summary_file)
                    }
                })
            
        except Exception as e:
            logger.error(f"保存结果文件失败: {str(e)}")
            return jsonify({"error": "保存结果文件失败", "details": str(e)}), 500
        
        return jsonify({
            "success": True,
            "transcription": transcription_text,
            "summary": summary_content,
            "template": template_type,
            "zip_file": zip_filename,
            "files": {
                "audio": filename,
                "transcription": transcription_file,
                "summary": os.path.basename(summary_file)
            }
        })
    
    except Exception as e:
        logger.error(f"/process 接口未捕获异常: {str(e)}")
        return jsonify({"error": "服务器内部错误", "details": str(e)}), 500

@app.route('/summaries', methods=['GET'])
@log_request('/summaries')
def list_summaries():
    """获取所有总结文件列表"""
    summaries_dir = 'summaries'
    if not os.path.exists(summaries_dir):
        return jsonify({"summaries": []})
    
    files = []
    for filename in os.listdir(summaries_dir):
        if filename.endswith('.md'):
            filepath = os.path.join(summaries_dir, filename)
            stat = os.stat(filepath)
            files.append({
                "filename": filename,
                "size": stat.st_size,
                "created_time": datetime.datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S"),
                "modified_time": datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            })
    
    # 按修改时间倒序排列
    files.sort(key=lambda x: x['modified_time'], reverse=True)
    
    return jsonify({"summaries": files})

@app.route('/download/<filename>', methods=['GET'])
@log_request('/download')
def download_summary(filename):
    """下载指定的总结文件"""
    summaries_dir = 'summaries'
    filepath = os.path.join(summaries_dir, filename)
    
    if not os.path.exists(filepath):
        return jsonify({"error": "文件不存在"}), 404
    
    return send_file(filepath, as_attachment=True)

@app.route('/download-zip/<zip_filename>', methods=['GET'])
@log_request('/download-zip')
def download_zip_file(zip_filename):
    """下载zip文件"""
    try:
        # 检查zip文件是否存在于summaries目录
        zip_path = os.path.join('summaries', zip_filename)
        if os.path.exists(zip_path):
            return send_file(zip_path, as_attachment=True, download_name=zip_filename, mimetype='application/zip')
        else:
            return jsonify({"error": "ZIP文件不存在"}), 404
    except Exception as e:
        logger.error(f"下载ZIP文件失败: {str(e)}")
        return jsonify({"error": "下载ZIP文件失败", "details": str(e)}), 500

@app.route('/stats', methods=['GET'])
def get_usage_stats():
    """获取使用统计数据"""
    stats = load_usage_stats()
    
    # 计算成功率
    success_rate = 0
    if stats['total_requests'] > 0:
        success_rate = round((stats['successful_requests'] / stats['total_requests']) * 100, 2)
    
    # 计算平均处理时间
    avg_processing_time = 0
    if stats['total_requests'] > 0:
        avg_processing_time = round(stats['total_processing_time'] / stats['total_requests'], 3)
    
    # 格式化文件大小
    def format_file_size(size_bytes):
        if size_bytes == 0:
            return "0 B"
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        return f"{size_bytes:.2f} {size_names[i]}"
    
    # 获取最近7天的统计
    recent_days = []
    for i in range(7):
        date = (datetime.datetime.now() - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
        day_stats = stats['daily_stats'].get(date, {'requests': 0, 'success': 0, 'processing_time': 0, 'file_size': 0})
        recent_days.append({
            'date': date,
            'requests': day_stats['requests'],
            'success': day_stats['success'],
            'success_rate': round((day_stats['success'] / day_stats['requests']) * 100, 2) if day_stats['requests'] > 0 else 0,
            'processing_time': round(day_stats['processing_time'], 3),
            'file_size': format_file_size(day_stats['file_size'])
        })
    
    # 端点统计排序
    endpoint_stats = []
    for endpoint, data in stats['endpoints'].items():
        success_rate_ep = round((data['success'] / data['count']) * 100, 2) if data['count'] > 0 else 0
        endpoint_stats.append({
            'endpoint': endpoint,
            'count': data['count'],
            'success': data['success'],
            'success_rate': success_rate_ep,
            'avg_time': round(data['avg_time'], 3),
            'total_time': round(data['total_time'], 3)
        })
    endpoint_stats.sort(key=lambda x: x['count'], reverse=True)
    
    # 文件类型统计
    file_type_stats = []
    for file_type, data in stats['file_types'].items():
        file_type_stats.append({
            'type': file_type,
            'count': data['count'],
            'total_size': format_file_size(data['total_size']),
            'avg_size': format_file_size(data['total_size'] / data['count']) if data['count'] > 0 else "0 B"
        })
    file_type_stats.sort(key=lambda x: x['count'], reverse=True)
    
    return jsonify({
        'overview': {
            'total_requests': stats['total_requests'],
            'successful_requests': stats['successful_requests'],
            'failed_requests': stats['failed_requests'],
            'success_rate': success_rate,
            'total_processing_time': round(stats['total_processing_time'], 3),
            'avg_processing_time': avg_processing_time,
            'total_file_size': format_file_size(stats['total_file_size'])
        },
        'recent_days': recent_days,
        'endpoints': endpoint_stats,
        'file_types': file_type_stats,
        'error_types': stats['error_types'],
        'recent_activities': stats['recent_activities'][:10]  # 只返回最近10条活动
    })

@app.route('/stats/dashboard', methods=['GET'])
def stats_dashboard():
    """统计数据仪表板页面"""
    return render_template('stats.html')

@app.route('/unified_dashboard', methods=['GET'])
def unified_dashboard():
    """统一仪表板页面 - 合并了stats和dashboard功能"""
    return render_template('unified_dashboard.html')

# API endpoints for unified dashboard
@app.route('/api/stats/overview', methods=['GET'])
def get_stats_overview():
    """获取统计概览"""
    stats = load_usage_stats()
    
    # 计算成功率
    success_rate = 0
    if stats['total_requests'] > 0:
        success_rate = round((stats['successful_requests'] / stats['total_requests']) * 100, 2)
    
    # 计算平均处理时间
    avg_processing_time = 0
    if stats['total_requests'] > 0:
        avg_processing_time = round(stats['total_processing_time'] / stats['total_requests'], 3)
    
    return jsonify({
        'success': True,
        'data': {
            'total_requests': stats['total_requests'],
            'successful_requests': stats['successful_requests'],
            'failed_requests': stats['failed_requests'],
            'success_rate': success_rate,
            'avg_processing_time': avg_processing_time,
            'total_file_size': stats['total_file_size']
        }
    })

@app.route('/api/stats/usage', methods=['GET'])
def get_usage_stats_api():
    """获取使用统计API"""
    stats = load_usage_stats()
    
    # 获取最近7天的统计
    recent_days = []
    for i in range(7):
        date = (datetime.datetime.now() - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
        day_stats = stats['daily_stats'].get(date, {'requests': 0, 'success': 0})
        recent_days.append({
            'date': date,
            'requests': day_stats['requests'],
            'success': day_stats['success']
        })
    
    return jsonify({
        'success': True,
        'data': recent_days
    })

@app.route('/api/stats/errors', methods=['GET'])
def get_error_stats():
    """获取错误统计"""
    stats = load_usage_stats()
    
    error_data = []
    for error_type, count in stats['error_types'].items():
        error_data.append({
            'type': error_type,
            'count': count
        })
    
    return jsonify({
        'success': True,
        'data': error_data
    })

@app.route('/api/stats/usage-table', methods=['GET'])
def get_usage_table():
    """获取使用记录表格数据"""
    stats = load_usage_stats()
    
    return jsonify({
        'success': True,
        'data': stats['recent_activities'][:20]  # 返回最近20条记录
    })

# Dashboard API endpoints (mock data for now)
@app.route('/api/database/stats', methods=['GET'])
def get_database_stats():
    """获取数据库统计"""
    return jsonify({
        'success': True,
        'data': {
            'total_records': 1250,
            'total_size': 45.6,
            'growth_rate': 12.5
        }
    })

@app.route('/api/database/storage', methods=['GET'])
def get_storage_stats():
    """获取存储统计"""
    return jsonify({
        'success': True,
        'data': {
            'used_space': 2.3,
            'total_space': 10.0,
            'usage_percentage': 23
        }
    })

@app.route('/api/database/compression', methods=['GET'])
def get_compression_stats():
    """获取压缩统计"""
    return jsonify({
        'success': True,
        'data': {
            'original_size': 100 * 1024 * 1024,  # 100MB
            'compressed_size': 35 * 1024 * 1024,  # 35MB
            'compression_ratio': 65
        }
    })

@app.route('/api/database/performance', methods=['GET'])
def get_performance_stats():
    """获取性能统计"""
    return jsonify({
        'success': True,
        'data': {
            'avg_query_time': 45.2
        }
    })

@app.route('/api/database/activity', methods=['GET'])
def get_recent_activity():
    """获取最近活动"""
    return jsonify({
        'success': True,
        'data': [
            {
                'timestamp': datetime.datetime.now().isoformat(),
                'operation': '数据备份',
                'status': 'success',
                'details': '备份完成，大小: 2.3GB'
            },
            {
                'timestamp': (datetime.datetime.now() - datetime.timedelta(hours=2)).isoformat(),
                'operation': '索引优化',
                'status': 'success',
                'details': '优化了3个索引'
            }
        ]
    })

# Database operation endpoints
@app.route('/api/database/optimize', methods=['POST'])
def optimize_database():
    """优化数据库"""
    try:
        # 模拟数据库优化操作
        import time
        time.sleep(1)  # 模拟处理时间
        
        return jsonify({
            'success': True,
            'message': '数据库优化完成',
            'optimized_tables': 5,
            'space_saved': '1.2MB'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'优化失败: {str(e)}'
        }), 500

@app.route('/api/database/export', methods=['POST'])
def export_database():
    """导出数据库"""
    try:
        # 模拟数据导出操作
        import time
        time.sleep(2)  # 模拟处理时间
        
        export_filename = f"database_export_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        
        return jsonify({
            'success': True,
            'message': '数据导出完成',
            'filename': export_filename,
            'size': '15.6MB'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'导出失败: {str(e)}'
        }), 500

@app.route('/api/database/cleanup', methods=['POST'])
def cleanup_database():
    """清理数据库"""
    try:
        # 模拟数据清理操作
        import time
        time.sleep(1)  # 模拟处理时间
        
        return jsonify({
            'success': True,
            'message': '数据清理完成',
            'deleted_count': 127
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'清理失败: {str(e)}'
        }), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)