"""
Ollama本地模型客户端
"""
import json
from typing import Dict, List, Optional, Any
from loguru import logger
try:
    import ollama
except ImportError:
    ollama = None
    logger.warning("ollama库未安装，请运行: pip install ollama")


class OllamaClient:
    """Ollama客户端"""
    
    def __init__(self, host: str = "http://localhost:11434", 
                 model: str = "qwen2.5:7b",
                 timeout: int = 120):
        """
        初始化Ollama客户端
        
        Args:
            host: Ollama服务地址
            model: 模型名称
            timeout: 超时时间（秒）
        """
        self.host = host
        self.model = model
        self.timeout = timeout
        self._check_connection()
        logger.info(f"Ollama客户端初始化完成，模型: {model}, 地址: {host}")
    
    def _check_connection(self):
        """检查Ollama服务连接"""
        if ollama is None:
            raise ImportError("ollama库未安装，请运行: pip install ollama")
        
        try:
            # 尝试列出模型来验证连接
            models = ollama.list()
            # 处理不同版本的ollama库返回格式
            if hasattr(models, 'models'):
                model_list = models.models
            elif isinstance(models, dict) and 'models' in models:
                model_list = models['models']
            else:
                model_list = models if isinstance(models, list) else []
            
            # 提取模型名称
            model_names = []
            for m in model_list:
                if isinstance(m, dict):
                    if 'name' in m:
                        model_names.append(m['name'])
                    elif 'model' in m:
                        model_names.append(m['model'])
                elif hasattr(m, 'name'):
                    model_names.append(m.name)
                elif hasattr(m, 'model'):
                    model_names.append(m.model)
            
            logger.info(f"Ollama服务连接成功，可用模型: {model_names}")
        except Exception as e:
            logger.error(f"Ollama服务连接失败: {e}")
            raise ConnectionError(f"无法连接到Ollama服务: {e}")
    
    def chat(self, prompt: str, 
             system_prompt: Optional[str] = None,
             max_tokens: int = 2048,
             temperature: float = 0.7,
             stream: bool = False) -> str:
        """
        发送聊天请求
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示
            max_tokens: 最大token数
            temperature: 温度参数
            stream: 是否流式输出
            
        Returns:
            str: 模型响应
        """
        try:
            messages = []
            
            if system_prompt:
                messages.append({
                    'role': 'system',
                    'content': system_prompt
                })
            
            messages.append({
                'role': 'user',
                'content': prompt
            })
            
            response = ollama.chat(
                model=self.model,
                messages=messages,
                options={
                    'num_predict': max_tokens,
                    'temperature': temperature,
                },
                stream=stream
            )
            
            if stream:
                # 流式输出需要特殊处理
                full_response = ""
                for chunk in response:
                    if 'message' in chunk:
                        full_response += chunk['message'].get('content', '')
                return full_response
            else:
                return response['message']['content']
                
        except Exception as e:
            logger.error(f"Ollama聊天请求失败: {e}")
            raise
    
    def generate(self, prompt: str,
                 max_tokens: int = 2048,
                 temperature: float = 0.7) -> str:
        """
        生成文本
        
        Args:
            prompt: 提示文本
            max_tokens: 最大token数
            temperature: 温度参数
            
        Returns:
            str: 生成的文本
        """
        try:
            response = ollama.generate(
                model=self.model,
                prompt=prompt,
                options={
                    'num_predict': max_tokens,
                    'temperature': temperature,
                }
            )
            
            return response['response']
            
        except Exception as e:
            logger.error(f"Ollama生成请求失败: {e}")
            raise
    
    def list_models(self) -> List[Dict[str, Any]]:
        """
        列出所有可用模型
        
        Returns:
            List[Dict]: 模型列表
        """
        try:
            response = ollama.list()
            return response.get('models', [])
        except Exception as e:
            logger.error(f"获取模型列表失败: {e}")
            raise
    
    def pull_model(self, model_name: str) -> bool:
        """
        拉取模型
        
        Args:
            model_name: 模型名称
            
        Returns:
            bool: 是否成功
        """
        try:
            logger.info(f"开始拉取模型: {model_name}")
            ollama.pull(model_name)
            logger.info(f"模型拉取成功: {model_name}")
            return True
        except Exception as e:
            logger.error(f"模型拉取失败: {e}")
            return False
    
    def get_model_info(self, model_name: Optional[str] = None) -> Dict[str, Any]:
        """
        获取模型信息
        
        Args:
            model_name: 模型名称，如果为None则使用当前模型
            
        Returns:
            Dict: 模型信息
        """
        try:
            model_name = model_name or self.model
            response = ollama.show(model_name)
            return response
        except Exception as e:
            logger.error(f"获取模型信息失败: {e}")
            raise
    
    def set_model(self, model_name: str):
        """
        设置当前使用的模型
        
        Args:
            model_name: 模型名称
        """
        self.model = model_name
        logger.info(f"切换模型为: {model_name}")
    
    def chat_with_json(self, prompt: str,
                      system_prompt: Optional[str] = None,
                      schema: Optional[Dict] = None) -> Dict[str, Any]:
        """
        发送聊天请求并返回JSON格式结果
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示
            schema: JSON schema
            
        Returns:
            Dict: JSON格式结果
        """
        # 添加JSON输出指令
        json_instruction = "\n\n请以JSON格式返回结果，不要包含其他文字。"
        full_prompt = prompt + json_instruction
        
        if system_prompt:
            full_system = system_prompt + json_instruction
        else:
            full_system = None
        
        response = self.chat(
            prompt=full_prompt,
            system_prompt=full_system
        )
        
        # 尝试解析JSON
        try:
            # 清理可能的markdown代码块标记
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:]
            if response.startswith('```'):
                response = response[3:]
            if response.endswith('```'):
                response = response[:-3]
            response = response.strip()
            
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}, 原始响应: {response}")
            raise ValueError(f"模型返回的不是有效的JSON格式: {e}")