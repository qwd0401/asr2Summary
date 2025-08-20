#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本
将现有的文件存储数据迁移到新的数据库存储系统
"""

import os
import json
import logging
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import shutil

# 导入数据库服务
from database import get_database_service
from compression_utils import compress_text, compression_stats

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/migration.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DataMigrator:
    """
    数据迁移器
    负责将文件系统数据迁移到数据库
    """
    
    def __init__(self, db_path: str = 'meetassistant.db'):
        self.db_service = get_database_service(db_path)
        self.migration_stats = {
            'audio_files': {'total': 0, 'migrated': 0, 'failed': 0},
            'transcriptions': {'total': 0, 'migrated': 0, 'failed': 0},
            'summaries': {'total': 0, 'migrated': 0, 'failed': 0},
            'usage_stats': {'total': 0, 'migrated': 0, 'failed': 0}
        }
        
        # 确保必要的目录存在
        os.makedirs('logs', exist_ok=True)
        os.makedirs('backup', exist_ok=True)
    
    def migrate_all_data(self) -> Dict[str, Any]:
        """
        迁移所有数据
        """
        logger.info("开始数据迁移...")
        start_time = datetime.datetime.now()
        
        try:
            # 1. 备份现有数据
            self._backup_existing_data()
            
            # 2. 迁移音频文件记录
            self._migrate_audio_files()
            
            # 3. 迁移转录文件
            self._migrate_transcription_files()
            
            # 4. 迁移总结文件
            self._migrate_summary_files()
            
            # 5. 迁移使用统计
            self._migrate_usage_statistics()
            
            # 6. 生成迁移报告
            migration_time = datetime.datetime.now() - start_time
            report = self._generate_migration_report(migration_time)
            
            logger.info("数据迁移完成")
            return report
            
        except Exception as e:
            logger.error(f"数据迁移失败: {e}")
            raise
    
    def _backup_existing_data(self) -> None:
        """
        备份现有数据
        """
        logger.info("备份现有数据...")
        
        backup_dir = f"backup/migration_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.makedirs(backup_dir, exist_ok=True)
        
        # 备份目录
        directories_to_backup = ['uploads', 'summaries', 'logs']
        
        for directory in directories_to_backup:
            if os.path.exists(directory):
                backup_path = os.path.join(backup_dir, directory)
                try:
                    shutil.copytree(directory, backup_path)
                    logger.info(f"已备份目录: {directory} -> {backup_path}")
                except Exception as e:
                    logger.warning(f"备份目录失败 {directory}: {e}")
        
        logger.info(f"数据备份完成: {backup_dir}")
    
    def _migrate_audio_files(self) -> None:
        """
        迁移音频文件记录
        """
        logger.info("迁移音频文件记录...")
        
        uploads_dir = Path('uploads')
        if not uploads_dir.exists():
            logger.info("uploads目录不存在，跳过音频文件迁移")
            return
        
        audio_files = list(uploads_dir.glob('*'))
        self.migration_stats['audio_files']['total'] = len(audio_files)
        
        for audio_file in audio_files:
            if audio_file.is_file():
                try:
                    # 解析文件名获取时间戳
                    filename = audio_file.name
                    file_size = audio_file.stat().st_size
                    file_type = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'unknown'
                    
                    # 获取文件创建时间
                    created_time = datetime.datetime.fromtimestamp(audio_file.stat().st_ctime)
                    
                    # 解析原始文件名（如果是时间戳格式）
                    original_filename = filename
                    if '_' in filename and filename.startswith(('20', '19')):
                        parts = filename.split('_', 1)
                        if len(parts) > 1:
                            original_filename = parts[1]
                    
                    # 创建音频文件记录
                    audio_id = self.db_service.audio_files.create(
                        filename=filename,
                        original_filename=original_filename,
                        file_path=str(audio_file),
                        file_size=file_size,
                        file_type=file_type
                    )
                    
                    # 更新状态为已完成（假设现有文件都已处理完成）
                    self.db_service.audio_files.update_status(audio_id, 'completed')
                    
                    self.migration_stats['audio_files']['migrated'] += 1
                    logger.debug(f"已迁移音频文件: {filename} (ID: {audio_id})")
                    
                except Exception as e:
                    logger.error(f"迁移音频文件失败 {audio_file}: {e}")
                    self.migration_stats['audio_files']['failed'] += 1
        
        logger.info(f"音频文件迁移完成: {self.migration_stats['audio_files']['migrated']}/{self.migration_stats['audio_files']['total']}")
    
    def _migrate_transcription_files(self) -> None:
        """
        迁移转录文件
        """
        logger.info("迁移转录文件...")
        
        summaries_dir = Path('summaries')
        if not summaries_dir.exists():
            logger.info("summaries目录不存在，跳过转录文件迁移")
            return
        
        # 查找转录文件（通常以.txt结尾或包含transcription关键词）
        transcription_files = []
        for file_path in summaries_dir.glob('*'):
            if file_path.is_file():
                filename = file_path.name.lower()
                if (filename.endswith('.txt') or 
                    'transcription' in filename or 
                    'transcript' in filename):
                    transcription_files.append(file_path)
        
        self.migration_stats['transcriptions']['total'] = len(transcription_files)
        
        for trans_file in transcription_files:
            try:
                # 读取转录内容
                with open(trans_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if not content.strip():
                    logger.warning(f"转录文件为空: {trans_file}")
                    continue
                
                # 尝试匹配对应的音频文件
                audio_id = self._find_matching_audio_file(trans_file.name)
                
                if not audio_id:
                    # 如果找不到匹配的音频文件，创建一个虚拟的音频记录
                    audio_id = self._create_virtual_audio_record(trans_file)
                
                # 创建转录记录
                transcription_id = self.db_service.transcriptions.create(
                    audio_file_id=audio_id,
                    transcription_text=content,
                    processing_time=None,  # 历史数据无处理时间
                    confidence_score=None
                )
                
                self.migration_stats['transcriptions']['migrated'] += 1
                logger.debug(f"已迁移转录文件: {trans_file.name} (ID: {transcription_id})")
                
            except Exception as e:
                logger.error(f"迁移转录文件失败 {trans_file}: {e}")
                self.migration_stats['transcriptions']['failed'] += 1
        
        logger.info(f"转录文件迁移完成: {self.migration_stats['transcriptions']['migrated']}/{self.migration_stats['transcriptions']['total']}")
    
    def _migrate_summary_files(self) -> None:
        """
        迁移总结文件
        """
        logger.info("迁移总结文件...")
        
        summaries_dir = Path('summaries')
        if not summaries_dir.exists():
            logger.info("summaries目录不存在，跳过总结文件迁移")
            return
        
        # 查找总结文件（通常以.md结尾或包含summary关键词）
        summary_files = []
        for file_path in summaries_dir.glob('*'):
            if file_path.is_file():
                filename = file_path.name.lower()
                if (filename.endswith('.md') or 
                    'summary' in filename or 
                    'meeting' in filename):
                    summary_files.append(file_path)
        
        self.migration_stats['summaries']['total'] = len(summary_files)
        
        for summary_file in summary_files:
            try:
                # 读取总结内容
                with open(summary_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if not content.strip():
                    logger.warning(f"总结文件为空: {summary_file}")
                    continue
                
                # 尝试匹配对应的转录记录
                transcription_id = self._find_matching_transcription(summary_file.name)
                
                if not transcription_id:
                    # 如果找不到匹配的转录记录，创建一个虚拟的转录记录
                    transcription_id = self._create_virtual_transcription_record(summary_file)
                
                # 确定模板类型
                template_type = self._determine_template_type(content)
                
                # 创建总结记录
                summary_id = self.db_service.summaries.create(
                    transcription_id=transcription_id,
                    template_type=template_type,
                    summary_content=content,
                    processing_time=None  # 历史数据无处理时间
                )
                
                self.migration_stats['summaries']['migrated'] += 1
                logger.debug(f"已迁移总结文件: {summary_file.name} (ID: {summary_id})")
                
            except Exception as e:
                logger.error(f"迁移总结文件失败 {summary_file}: {e}")
                self.migration_stats['summaries']['failed'] += 1
        
        logger.info(f"总结文件迁移完成: {self.migration_stats['summaries']['migrated']}/{self.migration_stats['summaries']['total']}")
    
    def _migrate_usage_statistics(self) -> None:
        """
        迁移使用统计数据
        """
        logger.info("迁移使用统计数据...")
        
        usage_stats_file = Path('logs/usage_stats.json')
        if not usage_stats_file.exists():
            logger.info("使用统计文件不存在，跳过统计数据迁移")
            return
        
        try:
            with open(usage_stats_file, 'r', encoding='utf-8') as f:
                stats_data = json.load(f)
            
            # 迁移最近活动记录
            recent_activities = stats_data.get('recent_activities', [])
            self.migration_stats['usage_stats']['total'] = len(recent_activities)
            
            for activity in recent_activities:
                try:
                    # 创建使用统计记录
                    self.db_service.usage_stats.create(
                        request_id=activity.get('request_id', 'migrated'),
                        endpoint=activity.get('endpoint', 'unknown'),
                        method='POST',  # 大部分是POST请求
                        success=activity.get('success', True),
                        processing_time=activity.get('processing_time', 0),
                        file_size=activity.get('file_size', 0),
                        file_type=activity.get('file_type', 'unknown'),
                        user_agent='Migration Script',
                        ip_address='127.0.0.1'
                    )
                    
                    self.migration_stats['usage_stats']['migrated'] += 1
                    
                except Exception as e:
                    logger.error(f"迁移统计记录失败: {e}")
                    self.migration_stats['usage_stats']['failed'] += 1
            
            logger.info(f"使用统计迁移完成: {self.migration_stats['usage_stats']['migrated']}/{self.migration_stats['usage_stats']['total']}")
            
        except Exception as e:
            logger.error(f"迁移使用统计失败: {e}")
    
    def _find_matching_audio_file(self, transcription_filename: str) -> Optional[int]:
        """
        查找匹配的音频文件ID
        """
        # 尝试从文件名中提取时间戳或关键信息
        base_name = transcription_filename.lower()
        
        # 移除常见的转录文件后缀
        for suffix in ['_transcription', '_transcript', '.txt']:
            base_name = base_name.replace(suffix, '')
        
        # 查询数据库中的音频文件
        audio_files = self.db_service.audio_files.list_recent(100)  # 获取最近的音频文件
        
        for audio_file in audio_files:
            audio_name = audio_file['filename'].lower()
            if base_name in audio_name or audio_name.replace('.mp3', '').replace('.wav', '') in base_name:
                return audio_file['id']
        
        return None
    
    def _find_matching_transcription(self, summary_filename: str) -> Optional[int]:
        """
        查找匹配的转录记录ID
        """
        # 尝试从文件名中提取时间戳或关键信息
        base_name = summary_filename.lower()
        
        # 移除常见的总结文件后缀
        for suffix in ['_summary', '_meeting', '.md']:
            base_name = base_name.replace(suffix, '')
        
        # 查询数据库中的转录记录
        try:
            # 这里需要实现一个查询最近转录记录的方法
            # 暂时返回最新的转录记录
            transcriptions = self.db_service.transcriptions.list_recent(50)
            if transcriptions:
                return transcriptions[0]['id']
        except:
            pass
        
        return None
    
    def _create_virtual_audio_record(self, transcription_file: Path) -> int:
        """
        为孤立的转录文件创建虚拟音频记录
        """
        filename = f"virtual_{transcription_file.stem}.unknown"
        
        return self.db_service.audio_files.create(
            filename=filename,
            original_filename=filename,
            file_path="/virtual/path",
            file_size=0,
            file_type="unknown"
        )
    
    def _create_virtual_transcription_record(self, summary_file: Path) -> int:
        """
        为孤立的总结文件创建虚拟转录记录
        """
        # 创建虚拟音频记录
        audio_id = self._create_virtual_audio_record(summary_file)
        
        # 创建虚拟转录记录
        return self.db_service.transcriptions.create(
            audio_file_id=audio_id,
            transcription_text="[虚拟转录记录 - 从总结文件迁移]",
            processing_time=None,
            confidence_score=None
        )
    
    def _determine_template_type(self, content: str) -> str:
        """
        根据内容确定模板类型
        """
        content_lower = content.lower()
        
        # 简单的关键词匹配
        if any(keyword in content_lower for keyword in ['产品', '功能', '需求', 'product']):
            return 'product'
        elif any(keyword in content_lower for keyword in ['技术', '开发', '代码', 'technical']):
            return 'technical'
        elif any(keyword in content_lower for keyword in ['会议', '讨论', 'meeting']):
            return 'meeting'
        else:
            return 'product'  # 默认使用产品模板
    
    def _generate_migration_report(self, migration_time: datetime.timedelta) -> Dict[str, Any]:
        """
        生成迁移报告
        """
        total_migrated = sum(stats['migrated'] for stats in self.migration_stats.values())
        total_failed = sum(stats['failed'] for stats in self.migration_stats.values())
        total_items = sum(stats['total'] for stats in self.migration_stats.values())
        
        # 获取压缩统计
        compression_summary = compression_stats.get_summary()
        
        report = {
            'migration_completed_at': datetime.datetime.now().isoformat(),
            'migration_duration': str(migration_time),
            'summary': {
                'total_items': total_items,
                'total_migrated': total_migrated,
                'total_failed': total_failed,
                'success_rate': (total_migrated / total_items * 100) if total_items > 0 else 0
            },
            'details': self.migration_stats,
            'compression_stats': compression_summary
        }
        
        # 保存报告到文件
        report_file = f"logs/migration_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"迁移报告已保存: {report_file}")
        return report
    
    def verify_migration(self) -> Dict[str, Any]:
        """
        验证迁移结果
        """
        logger.info("验证迁移结果...")
        
        verification_results = {
            'database_stats': self.db_service.get_database_stats(),
            'data_integrity': {
                'audio_files_count': len(self.db_service.audio_files.list_recent(1000)),
                'transcriptions_count': len(self.db_service.transcriptions.list_recent(1000)),
                'summaries_count': len(self.db_service.summaries.list_recent(1000))
            },
            'compression_efficiency': compression_stats.get_summary()
        }
        
        logger.info("迁移验证完成")
        return verification_results

def main():
    """
    主函数 - 执行数据迁移
    """
    print("=== MeetAssistant 数据库迁移工具 ===")
    print("此工具将把现有的文件存储数据迁移到新的数据库存储系统")
    print()
    
    # 确认迁移
    confirm = input("是否继续执行迁移？(y/N): ").strip().lower()
    if confirm != 'y':
        print("迁移已取消")
        return
    
    try:
        # 创建迁移器
        migrator = DataMigrator()
        
        # 执行迁移
        print("\n开始数据迁移...")
        report = migrator.migrate_all_data()
        
        # 显示迁移结果
        print("\n=== 迁移完成 ===")
        print(f"总计项目: {report['summary']['total_items']}")
        print(f"成功迁移: {report['summary']['total_migrated']}")
        print(f"迁移失败: {report['summary']['total_failed']}")
        print(f"成功率: {report['summary']['success_rate']:.1f}%")
        print(f"迁移耗时: {report['migration_duration']}")
        
        # 验证迁移结果
        print("\n验证迁移结果...")
        verification = migrator.verify_migration()
        print(f"数据库中的记录数:")
        print(f"  音频文件: {verification['data_integrity']['audio_files_count']}")
        print(f"  转录记录: {verification['data_integrity']['transcriptions_count']}")
        print(f"  总结记录: {verification['data_integrity']['summaries_count']}")
        
        if 'total_items_compressed' in verification['compression_efficiency']:
            comp_stats = verification['compression_efficiency']
            print(f"\n压缩效果:")
            print(f"  压缩项目: {comp_stats['total_items_compressed']}")
            print(f"  空间节省: {comp_stats['space_saved_percent']:.1f}%")
            print(f"  节省空间: {comp_stats['space_saved_mb']:.2f} MB")
        
        print("\n迁移成功完成！")
        print("请检查日志文件以获取详细信息。")
        
    except Exception as e:
        logger.error(f"迁移过程中发生错误: {e}")
        print(f"\n迁移失败: {e}")
        print("请检查日志文件以获取详细错误信息。")

if __name__ == '__main__':
    main()