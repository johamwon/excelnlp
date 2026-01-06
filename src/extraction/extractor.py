"""
信息抽取模块
使用本地模型对Excel表格进行信息抽取
"""
import os
import json
from typing import Dict, List, Optional, Any
from loguru import logger
from ..models import ModelFactory


class DataExtractor:
    """数据抽取器"""
    
    def __init__(self, model_client, prompt_templates_dir: str = "prompts/extraction/"):
        """
        初始化数据抽取器
        
        Args:
            model_client: 模型客户端
            prompt_templates_dir: Prompt模板目录
        """
        self.model_client = model_client
        self.prompt_templates_dir = prompt_templates_dir
        self._load_prompt_templates()
        logger.info("数据抽取器初始化完成")
    
    def _load_prompt_templates(self):
        """加载Prompt模板"""
        self.templates = {}
        
        if not os.path.exists(self.prompt_templates_dir):
            logger.warning(f"Prompt模板目录不存在: {self.prompt_templates_dir}")
            return
        
        for filename in os.listdir(self.prompt_templates_dir):
            if filename.endswith('.txt'):
                template_name = filename.replace('.txt', '')
                filepath = os.path.join(self.prompt_templates_dir, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    self.templates[template_name] = f.read()
                logger.info(f"加载Prompt模板: {template_name}")
    
    def extract(self, sheet_sample: Dict, category: str, 
               file_name: str) -> Dict[str, Any]:
        """
        从工作表中抽取信息
        
        Args:
            sheet_sample: 工作表样本数据
            category: 表格分类
            file_name: 文件名
            
        Returns:
            Dict: 抽取结果
        """
        # 根据分类选择合适的抽取策略
        if category == "financial_statements":
            return self._extract_financial(sheet_sample, file_name)
        else:
            return self._extract_general(sheet_sample, category, file_name)
    
    def _extract_general(self, sheet_sample: Dict, category: str, 
                        file_name: str) -> Dict[str, Any]:
        """
        通用信息抽取
        
        Args:
            sheet_sample: 工作表样本数据
            category: 表格分类
            file_name: 文件名
            
        Returns:
            Dict: 抽取结果
        """
        template = self.templates.get('general_extraction', '')
        
        if not template:
            logger.warning("通用抽取模板未找到，使用默认抽取")
            return self._default_extraction(sheet_sample)
        
        # 准备数据样本（限制行数以避免token超限）
        data_sample = json.dumps(
            sheet_sample.get('data', [])[:10], 
            ensure_ascii=False,
            indent=2
        )
        
        # 构建prompt
        prompt = template.format(
            file_name=file_name,
            sheet_name=sheet_sample.get('sheet_name', ''),
            category=category,
            headers=json.dumps(sheet_sample.get('columns', []), ensure_ascii=False),
            row_count=sheet_sample.get('shape', [0, 0])[0],
            data_sample=data_sample
        )
        
        try:
            # 调用模型进行抽取
            result = self.model_client.chat_with_json(prompt)
            logger.info(f"通用信息抽取成功: {sheet_sample.get('sheet_name')}")
            return result
        except Exception as e:
            logger.error(f"通用信息抽取失败: {e}")
            return self._default_extraction(sheet_sample)
    
    def _extract_financial(self, sheet_sample: Dict, 
                          file_name: str) -> Dict[str, Any]:
        """
        财务数据抽取
        
        Args:
            sheet_sample: 工作表样本数据
            file_name: 文件名
            
        Returns:
            Dict: 抽取结果
        """
        template = self.templates.get('financial_extraction', '')
        
        if not template:
            logger.warning("财务抽取模板未找到，使用通用抽取")
            return self._extract_general(sheet_sample, "financial_statements", file_name)
        
        # 准备数据样本
        data_sample = json.dumps(
            sheet_sample.get('data', [])[:15],  # 财务数据可能需要更多行
            ensure_ascii=False,
            indent=2
        )
        
        # 构建prompt
        prompt = template.format(
            file_name=file_name,
            sheet_name=sheet_sample.get('sheet_name', ''),
            headers=json.dumps(sheet_sample.get('columns', []), ensure_ascii=False),
            row_count=sheet_sample.get('shape', [0, 0])[0],
            data_sample=data_sample
        )
        
        try:
            # 调用模型进行抽取
            result = self.model_client.chat_with_json(prompt)
            logger.info(f"财务数据抽取成功: {sheet_sample.get('sheet_name')}")
            return result
        except Exception as e:
            logger.error(f"财务数据抽取失败: {e}")
            return self._extract_general(sheet_sample, "financial_statements", file_name)
    
    def _default_extraction(self, sheet_sample: Dict) -> Dict[str, Any]:
        """
        默认抽取方法（不使用模型）
        
        Args:
            sheet_sample: 工作表样本数据
            
        Returns:
            Dict: 抽取结果
        """
        result = {
            "numeric_data": [],
            "date_data": [],
            "text_data": [],
            "key_metrics": [],
            "dimensions": [],
            "summary": f"工作表包含 {sheet_sample.get('shape', [0, 0])[0]} 行数据"
        }
        
        # 简单的规则抽取
        data = sheet_sample.get('data', [])
        columns = sheet_sample.get('columns', [])
        dtypes = sheet_sample.get('dtypes', {})
        
        # 识别数值列
        numeric_cols = [col for col, dtype in dtypes.items() 
                       if 'int' in dtype.lower() or 'float' in dtype.lower()]
        
        # 识别日期列
        date_cols = [col for col, dtype in dtypes.items() 
                    if 'date' in dtype.lower() or 'time' in dtype.lower()]
        
        # 抽取数值数据
        for row in data[:20]:  # 限制前20行
            for col in numeric_cols:
                if col in row and row[col] is not None:
                    result["numeric_data"].append({
                        "column": col,
                        "value": row[col]
                    })
        
        # 抽取日期数据
        for row in data[:20]:
            for col in date_cols:
                if col in row and row[col] is not None:
                    result["date_data"].append({
                        "column": col,
                        "value": str(row[col])
                    })
        
        # 识别关键指标（包含"金额"、"数量"、"率"等关键词的列）
        for col in columns:
            if any(keyword in str(col).lower() 
                  for keyword in ['金额', '数量', '率', '比', '总计', '合计']):
                result["key_metrics"].append(col)
        
        # 识别维度（文本类型的列）
        for col, dtype in dtypes.items():
            if dtype == 'object' and col not in numeric_cols and col not in date_cols:
                result["dimensions"].append(col)
        
        logger.info(f"默认抽取完成: {sheet_sample.get('sheet_name')}")
        return result
    
    def batch_extract(self, sheet_samples: List[Dict], 
                     classifications: Dict[str, str],
                     file_name: str) -> Dict[str, Dict[str, Any]]:
        """
        批量抽取多个工作表的信息
        
        Args:
            sheet_samples: 工作表样本数据列表
            classifications: 分类结果字典 {sheet_name: category}
            file_name: 文件名
            
        Returns:
            Dict: 每个工作表的抽取结果
        """
        results = {}
        
        for sheet_sample in sheet_samples:
            sheet_name = sheet_sample.get('sheet_name', '')
            category = classifications.get(sheet_name, 'unknown')
            
            try:
                result = self.extract(sheet_sample, category, file_name)
                results[sheet_name] = result
                logger.info(f"工作表 '{sheet_name}' 信息抽取完成")
            except Exception as e:
                logger.error(f"工作表 '{sheet_name}' 信息抽取失败: {e}")
                results[sheet_name] = {"error": str(e)}
        
        return results