"""
配置管理模块
"""
import yaml
import os
from typing import Dict, Any
from loguru import logger


class Config:
    """配置类"""
    
    def __init__(self, config_path: str = "configs/config.yaml"):
        """
        初始化配置
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.config = self._load_config()
        logger.info(f"配置加载完成: {config_path}")
    
    def _load_config(self) -> Dict[str, Any]:
        """
        加载配置文件
        
        Returns:
            Dict: 配置字典
        """
        if not os.path.exists(self.config_path):
            logger.warning(f"配置文件不存在: {self.config_path}，使用默认配置")
            return self._get_default_config()
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            return config
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}，使用默认配置")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """
        获取默认配置
        
        Returns:
            Dict: 默认配置字典
        """
        return {
            "model": {
                "type": "ollama",
                "name": "qwen2.5:7b",
                "host": "http://localhost:11434",
                "timeout": 120,
                "max_tokens": 2048,
                "temperature": 0.7
            },
            "excel": {
                "supported_formats": [".xlsx", ".xls", ".xlsm"],
                "max_file_size": 50,
                "max_sheets": 20,
                "max_rows": 10000,
                "max_cols": 500
            },
            "rules": {
                "classification_rules": "configs/classification_rules.yaml",
                "enabled_classifiers": ["keyword_based", "structure_based", "pattern_based"]
            },
            "extraction": {
                "prompt_templates": "prompts/extraction/",
                "strategy": "hybrid",
                "entity_types": ["numeric", "date", "text", "formula", "currency", "percentage"]
            },
            "qa": {
                "prompt_template": "prompts/qa/question_answering.txt",
                "max_context_length": 8000,
                "question_types": ["data_query", "calculation", "comparison", "trend_analysis", "summary"]
            },
            "api": {
                "host": "0.0.0.0",
                "port": 8000,
                "enable_cors": True,
                "allowed_origins": ["*"]
            },
            "logging": {
                "level": "INFO",
                "format": "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
                "rotation": "10 MB",
                "retention": "30 days",
                "file": "logs/excelnlp.log"
            },
            "cache": {
                "enabled": True,
                "type": "memory",
                "ttl": 3600
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置项
        
        Args:
            key: 配置键（支持点号分隔的嵌套键）
            default: 默认值
            
        Returns:
            Any: 配置值
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_model_config(self) -> Dict[str, Any]:
        """获取模型配置"""
        return self.config.get('model', {})
    
    def get_excel_config(self) -> Dict[str, Any]:
        """获取Excel配置"""
        return self.config.get('excel', {})
    
    def get_rules_config(self) -> Dict[str, Any]:
        """获取规则引擎配置"""
        return self.config.get('rules', {})
    
    def get_extraction_config(self) -> Dict[str, Any]:
        """获取信息抽取配置"""
        return self.config.get('extraction', {})
    
    def get_qa_config(self) -> Dict[str, Any]:
        """获取问答系统配置"""
        return self.config.get('qa', {})
    
    def get_api_config(self) -> Dict[str, Any]:
        """获取API配置"""
        return self.config.get('api', {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """获取日志配置"""
        return self.config.get('logging', {})
    
    def get_cache_config(self) -> Dict[str, Any]:
        """获取缓存配置"""
        return self.config.get('cache', {})