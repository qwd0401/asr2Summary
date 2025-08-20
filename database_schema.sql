-- MeetAssistant 轻量级数据库架构设计
-- 使用 SQLite 作为轻量级数据库解决方案

-- 1. 音频文件表
CREATE TABLE audio_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size INTEGER NOT NULL,
    file_type VARCHAR(10) NOT NULL,
    upload_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'uploaded', -- uploaded, processing, completed, failed
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 2. 转录文本表
CREATE TABLE transcriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    audio_file_id INTEGER NOT NULL,
    transcription_text TEXT NOT NULL,
    compression_algorithm VARCHAR(20) DEFAULT 'zlib',
    text_length INTEGER NOT NULL,
    processing_time REAL,
    confidence_score REAL,
    language VARCHAR(10) DEFAULT 'zh-CN',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (audio_file_id) REFERENCES audio_files(id) ON DELETE CASCADE
);

-- 3. 会议总结表
CREATE TABLE meeting_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transcription_id INTEGER NOT NULL,
    template_type VARCHAR(50) NOT NULL DEFAULT 'product',
    summary_content TEXT NOT NULL,
    compression_algorithm VARCHAR(20) DEFAULT 'zlib',
    content_length INTEGER NOT NULL,
    processing_time REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (transcription_id) REFERENCES transcriptions(id) ON DELETE CASCADE
);

-- 4. 使用统计表
CREATE TABLE usage_statistics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id VARCHAR(50) UNIQUE NOT NULL,
    endpoint VARCHAR(100) NOT NULL,
    method VARCHAR(10) NOT NULL,
    success BOOLEAN NOT NULL,
    processing_time REAL NOT NULL,
    file_size INTEGER DEFAULT 0,
    file_type VARCHAR(10),
    error_type VARCHAR(100),
    error_message TEXT,
    user_agent TEXT,
    ip_address VARCHAR(45),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 5. 模板配置表
CREATE TABLE template_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_type VARCHAR(50) UNIQUE NOT NULL,
    template_name VARCHAR(100) NOT NULL,
    description TEXT,
    system_prompt TEXT NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 6. 系统配置表
CREATE TABLE system_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_key VARCHAR(100) UNIQUE NOT NULL,
    config_value TEXT NOT NULL,
    config_type VARCHAR(20) DEFAULT 'string', -- string, integer, float, boolean, json
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引优化查询性能

-- 音频文件索引
CREATE INDEX idx_audio_files_upload_time ON audio_files(upload_time);
CREATE INDEX idx_audio_files_status ON audio_files(status);
CREATE INDEX idx_audio_files_file_type ON audio_files(file_type);

-- 转录文本索引
CREATE INDEX idx_transcriptions_audio_file_id ON transcriptions(audio_file_id);
CREATE INDEX idx_transcriptions_created_at ON transcriptions(created_at);
CREATE INDEX idx_transcriptions_text_length ON transcriptions(text_length);
CREATE INDEX idx_transcriptions_compression ON transcriptions(compression_algorithm);

-- 会议总结索引
CREATE INDEX idx_summaries_transcription_id ON meeting_summaries(transcription_id);
CREATE INDEX idx_summaries_template_type ON meeting_summaries(template_type);
CREATE INDEX idx_summaries_created_at ON meeting_summaries(created_at);
CREATE INDEX idx_summaries_compression ON meeting_summaries(compression_algorithm);

-- 使用统计索引
CREATE INDEX idx_usage_stats_endpoint ON usage_statistics(endpoint);
CREATE INDEX idx_usage_stats_created_at ON usage_statistics(created_at);
CREATE INDEX idx_usage_stats_success ON usage_statistics(success);
CREATE INDEX idx_usage_stats_request_id ON usage_statistics(request_id);

-- 模板配置索引
CREATE INDEX idx_template_configs_type ON template_configs(template_type);
CREATE INDEX idx_template_configs_active ON template_configs(is_active);

-- 系统配置索引
CREATE INDEX idx_system_configs_key ON system_configs(config_key);

-- 创建视图简化常用查询

-- 完整会议记录视图
CREATE VIEW meeting_records AS
SELECT 
    af.id as audio_id,
    af.filename,
    af.original_filename,
    af.file_size,
    af.upload_time,
    t.id as transcription_id,
    t.transcription_text,
    t.text_length,
    t.processing_time as transcription_time,
    ms.id as summary_id,
    ms.template_type,
    ms.summary_content,
    ms.processing_time as summary_time,
    ms.created_at as summary_created_at
FROM audio_files af
LEFT JOIN transcriptions t ON af.id = t.audio_file_id
LEFT JOIN meeting_summaries ms ON t.id = ms.transcription_id
ORDER BY af.upload_time DESC;

-- 每日统计视图
CREATE VIEW daily_statistics AS
SELECT 
    DATE(created_at) as date,
    COUNT(*) as total_requests,
    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_requests,
    SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed_requests,
    ROUND(AVG(processing_time), 3) as avg_processing_time,
    SUM(file_size) as total_file_size,
    COUNT(DISTINCT endpoint) as unique_endpoints
FROM usage_statistics
GROUP BY DATE(created_at)
ORDER BY date DESC;

-- 端点统计视图
CREATE VIEW endpoint_statistics AS
SELECT 
    endpoint,
    COUNT(*) as total_requests,
    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_requests,
    ROUND(AVG(processing_time), 3) as avg_processing_time,
    MAX(processing_time) as max_processing_time,
    MIN(processing_time) as min_processing_time
FROM usage_statistics
GROUP BY endpoint
ORDER BY total_requests DESC;

-- 插入默认模板配置
INSERT INTO template_configs (template_type, template_name, description, system_prompt) VALUES
('product', '产品会议模板', '适用于产品团队会议的总结模板', 
'你是一位资深的互联网产品专家，专门负责产品会议记录和总结，深度理解产品开发流程、用户需求分析、技术实现和业务目标。基于提供的产品会议转录内容，生成一份面向产品团队的结构化会议总结，重点关注产品决策、功能规划、用户体验和项目推进。'),

('technical', '技术会议模板', '适用于技术团队会议的总结模板',
'你是一位资深的技术专家，专门负责技术会议记录和总结，深度理解软件开发流程、架构设计、技术选型和工程实践。基于提供的技术会议转录内容，生成一份面向技术团队的结构化会议总结，重点关注技术方案、架构决策、开发计划和技术风险。'),

('business', '商务会议模板', '适用于商务团队会议的总结模板',
'你是一位资深的商务专家，专门负责商务会议记录和总结，深度理解商业模式、市场策略、客户关系和业务发展。基于提供的商务会议转录内容，生成一份面向商务团队的结构化会议总结，重点关注商业决策、市场机会、客户需求和业务目标。'),

('general', '通用会议模板', '适用于一般性会议的总结模板',
'你是一位专业的会议记录专家，能够准确理解和总结各类会议内容。基于提供的会议转录内容，生成一份结构化的会议总结，重点关注会议议题、讨论要点、决策结果和后续行动。');

-- 插入默认系统配置
INSERT INTO system_configs (config_key, config_value, config_type, description) VALUES
('max_file_size', '104857600', 'integer', '最大文件上传大小（字节）'),
('allowed_extensions', '["wav", "mp3", "pcm", "opus", "webm"]', 'json', '允许的音频文件扩展名'),
('default_template', 'product', 'string', '默认使用的总结模板'),
('enable_compression', 'true', 'boolean', '是否启用数据压缩'),
('retention_days', '90', 'integer', '数据保留天数'),
('api_timeout', '300', 'integer', 'API请求超时时间（秒）');

-- 创建触发器自动更新时间戳
CREATE TRIGGER update_audio_files_timestamp 
    AFTER UPDATE ON audio_files
    BEGIN
        UPDATE audio_files SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

CREATE TRIGGER update_template_configs_timestamp 
    AFTER UPDATE ON template_configs
    BEGIN
        UPDATE template_configs SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

CREATE TRIGGER update_system_configs_timestamp 
    AFTER UPDATE ON system_configs
    BEGIN
        UPDATE system_configs SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

-- 创建数据清理存储过程（通过定期任务调用）
-- 注意：SQLite不支持存储过程，这里提供清理SQL语句供定期执行

-- 清理过期的使用统计数据（保留90天）
-- DELETE FROM usage_statistics WHERE created_at < datetime('now', '-90 days');

-- 清理孤立的转录记录（没有对应音频文件的记录）
-- DELETE FROM transcriptions WHERE audio_file_id NOT IN (SELECT id FROM audio_files);

-- 清理孤立的会议总结记录（没有对应转录记录的记录）
-- DELETE FROM meeting_summaries WHERE transcription_id NOT IN (SELECT id FROM transcriptions);

-- 数据库优化命令（定期执行）
-- VACUUM; -- 重建数据库，回收空间
-- ANALYZE; -- 更新查询优化器统计信息
-- PRAGMA optimize; -- 自动优化数据库