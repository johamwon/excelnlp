"""
模型工厂
根据配置创建不同的模型客户端
"""
from typing import Dict, Any
from loguru import logger
from .ollama_client import OllamaClient


class ModelFactory:
    """模型工厂类"""
    
    @staticmethod
    def create_client(config: Dict[str, Any]):
        """
        根据配置创建模型客户端
        
        Args:
            config: 模型配置字典
            
        Returns:
            模型客户端实例
        """
        model_type = config.get('type', 'ollama')
        
        if model_type == 'ollama':
            return ModelFactory._create_ollama_client(config)
        else:
            raise ValueError(f"不支持的模型类型: {model_type}")
    
    @staticmethod
    def _create_ollama_client(config: Dict[str, Any]) -> OllamaClient:
        """
        创建Ollama客户端
        
        Args:
            config: Ollama配置
            
        Returns:
            OllamaClient: Ollama客户端实例
        """
        return OllamaClient(
            host=config.get('host', 'http://localhost:11434'),
            model=config.get('name', 'qwen2.5:7b'),
            timeout=config.get('timeout', 120)
        )
    
    @staticmethod
    def get_available_models() -> Dict[str, str]:
        """
        获取可用的模型类型
        
        Returns:
            Dict: 模型类型字典
        """
        return {
            'ollama': 'Ollama本地模型服务'
        }