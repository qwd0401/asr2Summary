from flask import Flask, request, jsonify, send_file, render_template
from werkzeug.utils import secure_filename
import os
import requests
import datetime
import time
import json
import logging
import zipfile
import uuid
from pathlib import Path
from functools import wraps
from typing import Dict, List, Optional, Any

# 导入数据库服务
from database import get_database_service, DatabaseService

app = Flask(__name__)

# 配置
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size
ALLOWED_EXTENSIONS = {'wav', 'mp3', 'pcm', 'opus', 'webm'}

# 确保上传目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('summaries', exist_ok=True)  # 保留用于临时文件
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

# 初始化数据库服务
db_service: DatabaseService = get_database_service('meetassistant.db')
logger.info("数据库服务初始化完成")

def log_request(endpoint):
    """请求日志装饰器 - 数据库版本"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = time.time()
            request_id = str(uuid.uuid4())[:8]
            
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
            
            # 获取请求信息
            user_agent = request.headers.get('User-Agent', '')
            ip_address = request.remote_addr
            
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
                
                # 记录统计数据到数据库
                try:
                    db_service.usage_stats.create(
                        request_id=request_id,
                        endpoint=endpoint,
                        method=request.method,
                        success=is_success,
                        processing_time=processing_time,
                        file_size=file_size,
                        file_type=file_type,
                        user_agent=user_agent,
                        ip_address=ip_address
                    )
                except Exception as e:
                    logger.error(f"记录使用统计失败: {e}")
                
                logger.info(f"[{request_id}] {endpoint} 请求完成 - 耗时: {processing_time:.3f}s, 成功: {is_success}")
                return result
                
            except Exception as e:
                processing_time = time.time() - start_time
                error_type = type(e).__name__
                error_message = str(e)
                
                # 记录错误统计到数据库
                try:
                    db_service.usage_stats.create(
                        request_id=request_id,
                        endpoint=endpoint,
                        method=request.method,
                        success=False,
                        processing_time=processing_time,
                        file_size=file_size,
                        file_type=file_type,
                        error_type=error_type,
                        error_message=error_message,
                        user_agent=user_agent,
                        ip_address=ip_address
                    )
                except Exception as db_e:
                    logger.error(f"记录错误统计失败: {db_e}")
                
                logger.error(f"[{request_id}] {endpoint} 请求失败 - 耗时: {processing_time:.3f}s, 错误: {error_message}")
                raise
                
        return decorated_function
    return decorator

def allowed_file(filename):
    """检查文件扩展名是否允许"""
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
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info("转录请求成功")
                    return result
                else:
                    error_msg = f"转录API请求失败: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    return {"error": error_msg}
                    
            except requests.exceptions.Timeout:
                error_msg = "转录请求超时"
                logger.error(error_msg)
                return {"error": error_msg}
            except requests.exceptions.RequestException as e:
                error_msg = f"转录请求异常: {str(e)}"
                logger.error(error_msg)
                return {"error": error_msg}
                
    except Exception as e:
        error_msg = f"转录过程异常: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}

def generate_meeting_summary(transcription_text, template_type="product"):
    """生成会议总结"""
    # 从数据库获取模板配置
    template_config = db_service.templates.get_by_type(template_type)
    if not template_config:
        logger.warning(f"未找到模板类型: {template_type}，使用默认模板")
        template_config = db_service.templates.get_by_type('product')
    
    if not template_config:
        # 如果数据库中没有模板，使用默认的产品模板
        system_prompt = "你是一位资深的互联网产品专家，专门负责产品会议记录和总结，深度理解产品开发流程、用户需求分析、技术实现和业务目标。基于提供的产品会议转录内容，生成一份面向产品团队的结构化会议总结，重点关注产品决策、功能规划、用户体验和项目推进。"
    else:
        system_prompt = template_config['system_prompt']
    
    url = "https://api.linkapi.org/v1/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer sk-breyqcjehyljoocgimftfmhndccaxntudloarkfpdqlwjqxs"
    }
    
    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": f"请基于以下会议转录内容生成结构化总结：\n\n{transcription_text}"
            }
        ],
        "temperature": 0.7,
        "max_tokens": 4000
    }
    
    try:
        logger.info(f"发送总结生成请求，使用模板: {template_type}")
        response = requests.post(url, headers=headers, json=data, timeout=300)
        
        if response.status_code == 200:
            result = response.json()
            logger.info("总结生成成功")
            return result
        else:
            error_msg = f"总结生成API请求失败: {response.status_code} - {response.text}"
            logger.error(error_msg)
            return {"error": error_msg}
            
    except requests.exceptions.Timeout:
        error_msg = "总结生成请求超时"
        logger.error(error_msg)
        return {"error": error_msg}
    except requests.exceptions.RequestException as e:
        error_msg = f"总结生成请求异常: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}
    except Exception as e:
        error_msg = f"总结生成过程异常: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}

# API路由

@app.route('/', methods=['GET'])
def index():
    """首页"""
    return render_template('index.html')

@app.route('/api', methods=['GET'])
def api_info():
    """API信息"""
    return jsonify({
        "name": "MeetAssistant API",
        "version": "2.0.0",
        "description": "会议助手API - 数据库版本",
        "features": [
            "音频文件上传",
            "语音转文字",
            "会议总结生成",
            "多模板支持",
            "数据库存储",
            "使用统计"
        ],
        "endpoints": {
            "/upload": "上传音频文件并转录",
            "/transcribe": "转录音频文件",
            "/summarize": "生成会议总结",
            "/process": "一键处理（上传+转录+总结）",
            "/templates": "获取可用模板",
            "/records": "获取会议记录",
            "/stats": "获取使用统计"
        }
    })

@app.route('/templates', methods=['GET'])
@log_request('/templates')
def get_templates():
    """获取可用的模板列表"""
    try:
        templates = db_service.templates.get_all_active()
        
        template_list = []
        for template in templates:
            template_list.append({
                "type": template['template_type'],
                "name": template['template_name'],
                "description": template['description']
            })
        
        return jsonify({
            "success": True,
            "templates": template_list
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
        # 保存文件
        filename = secure_filename(file.filename)
        timestamp = datetime.datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        
        # 获取文件信息
        file_size = os.path.getsize(filepath)
        file_type = filename.rsplit('.', 1)[1].lower()
        
        # 记录音频文件到数据库
        try:
            audio_id = db_service.audio_files.create(
                filename=unique_filename,
                original_filename=file.filename,
                file_path=filepath,
                file_size=file_size,
                file_type=file_type
            )
            
            # 更新状态为处理中
            db_service.audio_files.update_status(audio_id, 'processing')
            
        except Exception as e:
            logger.error(f"记录音频文件到数据库失败: {e}")
            return jsonify({"error": "数据库记录失败", "details": str(e)}), 500
        
        # 进行语音转文字
        transcription_start = time.time()
        result = speech_to_text(filepath)
        transcription_time = time.time() - transcription_start
        
        if 'text' in result:
            # 保存转录结果到数据库
            try:
                transcription_id = db_service.transcriptions.create(
                    audio_file_id=audio_id,
                    transcription_text=result['text'],
                    processing_time=transcription_time,
                    confidence_score=result.get('confidence', None)
                )
                
                # 更新音频文件状态为完成
                db_service.audio_files.update_status(audio_id, 'completed')
                
                return jsonify({
                    "success": True,
                    "audio_id": audio_id,
                    "transcription_id": transcription_id,
                    "transcription": result['text'],
                    "processing_time": transcription_time
                })
                
            except Exception as e:
                logger.error(f"保存转录结果到数据库失败: {e}")
                db_service.audio_files.update_status(audio_id, 'failed')
                return jsonify({"error": "保存转录结果失败", "details": str(e)}), 500
        else:
            # 转录失败，更新状态
            db_service.audio_files.update_status(audio_id, 'failed')
            return jsonify({"error": "转录失败", "details": result}), 500
    
    return jsonify({"error": "不支持的文件格式"}), 400

@app.route('/transcribe', methods=['POST'])
@log_request('/transcribe')
def transcribe_audio():
    """基于音频文件ID进行转录"""
    data = request.get_json()
    if not data or 'audio_id' not in data:
        return jsonify({"error": "请提供音频文件ID"}), 400
    
    audio_id = data['audio_id']
    
    # 从数据库获取音频文件信息
    audio_file = db_service.audio_files.get_by_id(audio_id)
    if not audio_file:
        return jsonify({"error": "音频文件不存在"}), 404
    
    if not os.path.exists(audio_file['file_path']):
        return jsonify({"error": "音频文件已被删除"}), 404
    
    # 检查是否已有转录记录
    existing_transcription = db_service.transcriptions.get_by_audio_id(audio_id)
    if existing_transcription:
        return jsonify({
            "success": True,
            "transcription_id": existing_transcription['id'],
            "transcription": existing_transcription['transcription_text'],
            "cached": True
        })
    
    # 进行转录
    transcription_start = time.time()
    result = speech_to_text(audio_file['file_path'])
    transcription_time = time.time() - transcription_start
    
    if 'text' in result:
        try:
            transcription_id = db_service.transcriptions.create(
                audio_file_id=audio_id,
                transcription_text=result['text'],
                processing_time=transcription_time,
                confidence_score=result.get('confidence', None)
            )
            
            return jsonify({
                "success": True,
                "transcription_id": transcription_id,
                "transcription": result['text'],
                "processing_time": transcription_time
            })
            
        except Exception as e:
            logger.error(f"保存转录结果失败: {e}")
            return jsonify({"error": "保存转录结果失败", "details": str(e)}), 500
    else:
        return jsonify({"error": "转录失败", "details": result}), 500

@app.route('/summarize', methods=['POST'])
@log_request('/summarize')
def summarize_meeting():
    """基于转录ID生成会议总结"""
    data = request.get_json()
    if not data or 'transcription_id' not in data:
        return jsonify({"error": "请提供转录ID"}), 400
    
    transcription_id = data['transcription_id']
    template_type = data.get('template', 'product')  # 默认使用产品模板
    
    # 从数据库获取转录文本
    transcription = db_service.transcriptions.get_by_id(transcription_id)
    if not transcription:
        return jsonify({"error": "转录记录不存在"}), 404
    
    # 检查是否已有相同模板的总结
    existing_summary = db_service.summaries.get_by_transcription_id(transcription_id)
    if existing_summary and existing_summary['template_type'] == template_type:
        return jsonify({
            "success": True,
            "summary_id": existing_summary['id'],
            "summary": existing_summary['summary_content'],
            "template": template_type,
            "cached": True
        })
    
    # 生成总结
    summary_start = time.time()
    result = generate_meeting_summary(transcription['transcription_text'], template_type)
    summary_time = time.time() - summary_start
    
    if 'choices' in result:
        summary_content = result['choices'][0]['message']['content']
        
        try:
            summary_id = db_service.summaries.create(
                transcription_id=transcription_id,
                template_type=template_type,
                summary_content=summary_content,
                processing_time=summary_time
            )
            
            return jsonify({
                "success": True,
                "summary_id": summary_id,
                "summary": summary_content,
                "template": template_type,
                "processing_time": summary_time
            })
            
        except Exception as e:
            logger.error(f"保存总结到数据库失败: {e}")
            return jsonify({"error": "保存总结失败", "details": str(e)}), 500
    else:
        return jsonify({"error": "生成总结失败", "details": result}), 500

@app.route('/process', methods=['POST'])
@log_request('/process')
def process_audio():
    """一键处理：上传音频 -> 转录 -> 生成总结"""
    try:
        if 'file' not in request.files:
            return jsonify({"error": "没有上传文件"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "没有选择文件"}), 400
        
        if not (file and allowed_file(file.filename)):
            return jsonify({"error": "不支持的文件格式"}), 400
        
        # 获取模板参数
        template_type = request.form.get('template', 'product')
        
        # 步骤1: 保存文件并记录到数据库
        filename = secure_filename(file.filename)
        timestamp = datetime.datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        
        try:
            file.save(filepath)
            file_size = os.path.getsize(filepath)
            file_type = filename.rsplit('.', 1)[1].lower()
            
            audio_id = db_service.audio_files.create(
                filename=unique_filename,
                original_filename=file.filename,
                file_path=filepath,
                file_size=file_size,
                file_type=file_type
            )
            
            db_service.audio_files.update_status(audio_id, 'processing')
            logger.info(f"文件保存成功，音频ID: {audio_id}")
            
        except Exception as e:
            logger.error(f"文件保存或数据库记录失败: {e}")
            return jsonify({"error": "文件处理失败", "details": str(e)}), 500
        
        # 步骤2: 语音转文字
        logger.info("开始语音转文字处理")
        try:
            transcription_start = time.time()
            transcription_result = speech_to_text(filepath)
            transcription_time = time.time() - transcription_start
            
            if 'text' not in transcription_result:
                db_service.audio_files.update_status(audio_id, 'failed')
                return jsonify({"error": "转录失败", "details": transcription_result}), 500
            
            transcription_text = transcription_result['text']
            
            # 保存转录结果
            transcription_id = db_service.transcriptions.create(
                audio_file_id=audio_id,
                transcription_text=transcription_text,
                processing_time=transcription_time,
                confidence_score=transcription_result.get('confidence', None)
            )
            
            logger.info(f"转录成功，转录ID: {transcription_id}")
            
        except Exception as e:
            logger.error(f"转录过程异常: {e}")
            db_service.audio_files.update_status(audio_id, 'failed')
            return jsonify({"error": "转录过程异常", "details": str(e)}), 500
        
        # 步骤3: 生成会议总结
        logger.info(f"开始生成会议总结，使用模板: {template_type}")
        try:
            summary_start = time.time()
            summary_result = generate_meeting_summary(transcription_text, template_type)
            summary_time = time.time() - summary_start
            
            if 'choices' not in summary_result:
                db_service.audio_files.update_status(audio_id, 'failed')
                return jsonify({"error": "生成总结失败", "details": summary_result}), 500
            
            summary_content = summary_result['choices'][0]['message']['content']
            
            # 保存总结结果
            summary_id = db_service.summaries.create(
                transcription_id=transcription_id,
                template_type=template_type,
                summary_content=summary_content,
                processing_time=summary_time
            )
            
            # 更新音频文件状态为完成
            db_service.audio_files.update_status(audio_id, 'completed')
            
            logger.info(f"总结生成成功，总结ID: {summary_id}")
            
            return jsonify({
                "success": True,
                "audio_id": audio_id,
                "transcription_id": transcription_id,
                "summary_id": summary_id,
                "transcription": transcription_text,
                "summary": summary_content,
                "template": template_type,
                "processing_times": {
                    "transcription": transcription_time,
                    "summary": summary_time,
                    "total": transcription_time + summary_time
                }
            })
            
        except Exception as e:
            logger.error(f"总结生成过程异常: {e}")
            db_service.audio_files.update_status(audio_id, 'failed')
            return jsonify({"error": "总结生成过程异常", "details": str(e)}), 500
            
    except Exception as e:
        logger.error(f"处理过程异常: {e}")
        return jsonify({"error": "处理过程异常", "details": str(e)}), 500

@app.route('/records', methods=['GET'])
@log_request('/records')
def list_records():
    """获取会议记录列表"""
    try:
        limit = request.args.get('limit', 20, type=int)
        limit = min(limit, 100)  # 限制最大返回数量
        
        records = db_service.records.list_recent_records(limit)
        
        # 格式化返回数据
        formatted_records = []
        for record in records:
            formatted_record = {
                "audio_id": record['audio_id'],
                "filename": record['filename'],
                "original_filename": record['original_filename'],
                "file_size": record['file_size'],
                "upload_time": record['upload_time'],
                "transcription_id": record.get('transcription_id'),
                "summary_id": record.get('summary_id'),
                "template_type": record.get('template_type'),
                "summary_created_at": record.get('summary_created_at'),
                "has_transcription": record.get('transcription_id') is not None,
                "has_summary": record.get('summary_id') is not None
            }
            formatted_records.append(formatted_record)
        
        return jsonify({
            "success": True,
            "records": formatted_records,
            "count": len(formatted_records)
        })
        
    except Exception as e:
        logger.error(f"获取记录列表失败: {e}")
        return jsonify({"error": "获取记录列表失败", "details": str(e)}), 500

@app.route('/records/<int:audio_id>', methods=['GET'])
@log_request('/records/detail')
def get_record_detail(audio_id):
    """获取完整的会议记录详情"""
    try:
        record = db_service.records.get_complete_record(audio_id)
        if not record:
            return jsonify({"error": "记录不存在"}), 404
        
        return jsonify({
            "success": True,
            "record": record
        })
        
    except Exception as e:
        logger.error(f"获取记录详情失败: {e}")
        return jsonify({"error": "获取记录详情失败", "details": str(e)}), 500

@app.route('/download/transcription/<int:transcription_id>', methods=['GET'])
@log_request('/download/transcription')
def download_transcription(transcription_id):
    """下载转录文本文件"""
    try:
        transcription = db_service.transcriptions.get_by_id(transcription_id)
        if not transcription:
            return jsonify({"error": "转录记录不存在"}), 404
        
        # 创建临时文件
        temp_filename = f"transcription_{transcription_id}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        temp_path = os.path.join('summaries', temp_filename)
        
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(f"转录文本\n生成时间: {transcription['created_at']}\n\n")
            f.write(transcription['transcription_text'])
        
        return send_file(temp_path, as_attachment=True, download_name=temp_filename)
        
    except Exception as e:
        logger.error(f"下载转录文件失败: {e}")
        return jsonify({"error": "下载失败", "details": str(e)}), 500

@app.route('/download/summary/<int:summary_id>', methods=['GET'])
@log_request('/download/summary')
def download_summary(summary_id):
    """下载会议总结文件"""
    try:
        summary = db_service.summaries.get_by_id(summary_id)
        if not summary:
            return jsonify({"error": "总结记录不存在"}), 404
        
        # 获取模板信息
        template_config = db_service.templates.get_by_type(summary['template_type'])
        template_name = template_config['template_name'] if template_config else '会议总结'
        
        # 创建临时Markdown文件
        temp_filename = f"summary_{summary_id}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        temp_path = os.path.join('summaries', temp_filename)
        
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(f"# {template_name}\n\n")
            f.write(f"**生成时间：** {summary['created_at']}\n")
            f.write(f"**使用模板：** {template_name}\n\n")
            f.write(summary['summary_content'])
        
        return send_file(temp_path, as_attachment=True, download_name=temp_filename)
        
    except Exception as e:
        logger.error(f"下载总结文件失败: {e}")
        return jsonify({"error": "下载失败", "details": str(e)}), 500

@app.route('/stats', methods=['GET'])
@log_request('/stats')
def get_usage_stats():
    """获取使用统计数据"""
    try:
        # 获取每日统计
        days = request.args.get('days', 7, type=int)
        daily_stats = db_service.usage_stats.get_daily_stats(days)
        
        # 获取端点统计
        endpoint_stats = db_service.usage_stats.get_endpoint_stats()
        
        # 获取数据库统计
        db_stats = db_service.get_database_stats()
        
        return jsonify({
            "success": True,
            "daily_statistics": daily_stats,
            "endpoint_statistics": endpoint_stats,
            "database_statistics": db_stats
        })
        
    except Exception as e:
        logger.error(f"获取统计数据失败: {e}")
        return jsonify({"error": "获取统计数据失败", "details": str(e)}), 500

@app.route('/stats/dashboard', methods=['GET'])
def stats_dashboard():
    """统计数据仪表板页面"""
    return render_template('stats_dashboard.html')

@app.route('/dashboard', methods=['GET'])
def dashboard():
    """数据库管理面板"""
    return render_template('dashboard.html')

@app.route('/admin', methods=['GET'])
def admin_panel():
    """管理面板主页"""
    return render_template('dashboard.html')

@app.route('/admin/database', methods=['GET'])
def database_management():
    """数据库管理界面"""
    return render_template('dashboard.html')

@app.route('/admin/cleanup', methods=['POST'])
@log_request('/admin/cleanup')
def cleanup_old_data():
    """清理过期数据"""
    try:
        retention_days = request.json.get('retention_days', 90) if request.is_json else 90
        
        # 执行清理
        db_service.cleanup_old_data(retention_days)
        
        return jsonify({
            "success": True,
            "message": f"已清理 {retention_days} 天前的过期数据"
        })
        
    except Exception as e:
        logger.error(f"数据清理失败: {e}")
        return jsonify({"error": "数据清理失败", "details": str(e)}), 500

@app.route('/admin/optimize', methods=['POST'])
@log_request('/admin/optimize')
def optimize_database():
    """优化数据库"""
    try:
        db_service.optimize_database()
        
        return jsonify({
            "success": True,
            "message": "数据库优化完成"
        })
        
    except Exception as e:
        logger.error(f"数据库优化失败: {e}")
        return jsonify({"error": "数据库优化失败", "details": str(e)}), 500

# 数据查询接口
@app.route('/api/audio-files', methods=['GET'])
@log_request('/api/audio-files')
def list_audio_files():
    """获取音频文件列表"""
    try:
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        audio_files = db_service.audio_files.list_recent(limit, offset)
        
        return jsonify({
            'success': True,
            'data': audio_files,
            'total': len(audio_files)
        })
    except Exception as e:
        logger.error(f"获取音频文件列表失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/transcriptions', methods=['GET'])
@log_request('/api/transcriptions')
def list_transcriptions():
    """获取转录记录列表"""
    try:
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        transcriptions = db_service.transcriptions.list_recent(limit, offset)
        
        return jsonify({
            'success': True,
            'data': transcriptions,
            'total': len(transcriptions)
        })
    except Exception as e:
        logger.error(f"获取转录记录列表失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/summaries', methods=['GET'])
@log_request('/api/summaries')
def list_summaries():
    """获取总结记录列表"""
    try:
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        summaries = db_service.summaries.list_recent(limit, offset)
        
        return jsonify({
            'success': True,
            'data': summaries,
            'total': len(summaries)
        })
    except Exception as e:
        logger.error(f"获取总结记录列表失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# 统计分析接口
@app.route('/api/stats/overview', methods=['GET'])
@log_request('/api/stats/overview')
def get_stats_overview():
    """获取统计概览"""
    try:
        stats = db_service.get_database_stats()
        
        # 获取最近7天的活动统计
        recent_stats = db_service.usage_stats.get_daily_stats(7)
        
        return jsonify({
            'success': True,
            'data': {
                'database_stats': stats,
                'recent_activity': recent_stats
            }
        })
    except Exception as e:
        logger.error(f"获取统计概览失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stats/usage', methods=['GET'])
@log_request('/api/stats/usage')
def get_usage_stats_api():
    """获取使用统计API"""
    try:
        days = request.args.get('days', 30, type=int)
        endpoint = request.args.get('endpoint')
        
        if endpoint:
            stats = db_service.usage_stats.get_endpoint_stats(endpoint, days)
        else:
            stats = db_service.usage_stats.get_daily_stats(days)
        
        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        logger.error(f"获取使用统计失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# 数据导出接口
@app.route('/api/export/transcriptions', methods=['GET'])
@log_request('/api/export/transcriptions')
def export_transcriptions():
    """导出转录数据"""
    try:
        format_type = request.args.get('format', 'json')
        limit = request.args.get('limit', 1000, type=int)
        
        transcriptions = db_service.transcriptions.list_recent(limit)
        
        if format_type == 'csv':
            # 生成CSV格式
            import csv
            import io
            from flask import make_response
            
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=['id', 'audio_file_id', 'transcription_text', 'created_at'])
            writer.writeheader()
            
            for trans in transcriptions:
                writer.writerow({
                    'id': trans['id'],
                    'audio_file_id': trans['audio_file_id'],
                    'transcription_text': trans['transcription_text'][:100] + '...' if len(trans['transcription_text']) > 100 else trans['transcription_text'],
                    'created_at': trans['created_at']
                })
            
            response = make_response(output.getvalue())
            response.headers['Content-Type'] = 'text/csv'
            response.headers['Content-Disposition'] = 'attachment; filename=transcriptions.csv'
            return response
        else:
            return jsonify({
                'success': True,
                'data': transcriptions,
                'format': 'json'
            })
    except Exception as e:
        logger.error(f"导出转录数据失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# 系统配置接口
@app.route('/api/config', methods=['GET'])
@log_request('/api/config')
def get_system_config():
    """获取系统配置"""
    try:
        configs = db_service.system_configs.get_all()
        
        # 转换为字典格式
        config_dict = {config['config_key']: config['config_value'] for config in configs}
        
        return jsonify({
            'success': True,
            'data': config_dict
        })
    except Exception as e:
        logger.error(f"获取系统配置失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/config', methods=['POST'])
@log_request('/api/config')
def update_system_config():
    """更新系统配置"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': '无效的请求数据'}), 400
        
        updated_configs = []
        for key, value in data.items():
            config_id = db_service.system_configs.update_config(key, str(value))
            updated_configs.append({'key': key, 'value': value, 'id': config_id})
        
        return jsonify({
            'success': True,
            'message': f'已更新 {len(updated_configs)} 个配置项',
            'data': updated_configs
        })
    except Exception as e:
        logger.error(f"更新系统配置失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    # 启动时进行数据库优化
    try:
        logger.info("启动时优化数据库...")
        db_service.optimize_database()
        logger.info("数据库优化完成")
    except Exception as e:
        logger.warning(f"启动时数据库优化失败: {e}")
    
    app.run(debug=True, host='0.0.0.0', port=5000)