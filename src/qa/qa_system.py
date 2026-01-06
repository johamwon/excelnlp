"""
问答系统模块
处理用户对Excel表格的自然语言问题
"""
import os
import json
from typing import Dict, List, Optional, Any
from loguru import logger
from ..models import ModelFactory


class QASystem:
    """问答系统"""
    
    def __init__(self, model_client, prompt_template_path: str = "prompts/qa/question_answering.txt"):
        """
        初始化问答系统
        
        Args:
            model_client: 模型客户端
            prompt_template_path: Prompt模板路径
        """
        self.model_client = model_client
        self.prompt_template_path = prompt_template_path
        self._load_prompt_template()
        logger.info("问答系统初始化完成")
    
    def _load_prompt_template(self):
        """加载Prompt模板"""
        if os.path.exists(self.prompt_template_path):
            with open(self.prompt_template_path, 'r', encoding='utf-8') as f:
                self.prompt_template = f.read()
            logger.info(f"加载问答Prompt模板: {self.prompt_template_path}")
        else:
            logger.warning(f"问答Prompt模板不存在: {self.prompt_template_path}")
            self.prompt_template = None
    
    def answer(self, question: str, sheet_sample: Dict, 
               category: str, extraction_results: Dict,
               file_name: str) -> Dict[str, Any]:
        """
        回答用户问题
        
        Args:
            question: 用户问题
            sheet_sample: 工作表样本数据
            category: 表格分类
            extraction_results: 信息抽取结果
            file_name: 文件名
            
        Returns:
            Dict: 问答结果
        """
        if not self.prompt_template:
            return self._default_answer(question, sheet_sample)
        
        # 准备抽取结果
        extraction_json = json.dumps(extraction_results, ensure_ascii=False, indent=2)
        
        # 构建prompt
        prompt = self.prompt_template.format(
            file_name=file_name,
            sheet_name=sheet_sample.get('sheet_name', ''),
            category=category,
            headers=json.dumps(sheet_sample.get('columns', []), ensure_ascii=False),
            extraction_results=extraction_json,
            question=question
        )
        
        try:
            # 调用模型回答问题
            result = self.model_client.chat_with_json(prompt)
            logger.info(f"问题回答成功: {question[:50]}...")
            return result
        except Exception as e:
            logger.error(f"问题回答失败: {e}")
            return self._default_answer(question, sheet_sample)
    
    def _default_answer(self, question: str, sheet_sample: Dict) -> Dict[str, Any]:
        """
        默认回答方法（不使用模型）
        
        Args:
            question: 用户问题
            sheet_sample: 工作表样本数据
            
        Returns:
            Dict: 问答结果
        """
        # 简单的关键词匹配
        data = sheet_sample.get('data', [])
        columns = sheet_sample.get('columns', [])
        
        answer = f"抱歉，我无法从表格中找到关于'{question}'的确切答案。"
        evidence = []
        confidence = 0.3
        
        # 检查问题是否包含表头关键词
        question_lower = question.lower()
        matched_columns = [col for col in columns 
                          if str(col).lower() in question_lower]
        
        if matched_columns:
            answer = f"表格中包含以下相关列: {', '.join(matched_columns)}"
            evidence = [{"column": col} for col in matched_columns]
            confidence = 0.5
        
        # 如果有数据，提供一些示例
        if data:
            sample_data = data[:3]
            answer += f"\n\n数据示例（前3行）:\n{json.dumps(sample_data, ensure_ascii=False, indent=2)}"
        
        return {
            "answer": answer,
            "evidence": evidence,
            "confidence": confidence,
            "related_data": sample_data if data else []
        }
    
    def batch_answer(self, questions: List[str], sheet_samples: List[Dict],
                    classifications: Dict[str, str],
                    extractions: Dict[str, Dict],
                    file_name: str) -> Dict[str, Dict[str, Any]]:
        """
        批量回答问题
        
        Args:
            questions: 问题列表
            sheet_samples: 工作表样本数据列表
            classifications: 分类结果
            extractions: 抽取结果
            file_name: 文件名
            
        Returns:
            Dict: 每个问题的回答结果
        """
        results = {}
        
        for i, question in enumerate(questions):
            question_key = f"question_{i+1}"
            
            # 找到最相关的工作表
            best_sheet = self._find_best_sheet(question, sheet_samples)
            
            if best_sheet:
                sheet_name = best_sheet.get('sheet_name', '')
                category = classifications.get(sheet_name, 'unknown')
                extraction = extractions.get(sheet_name, {})
                
                try:
                    result = self.answer(question, best_sheet, category, 
                                       extraction, file_name)
                    results[question_key] = {
                        "question": question,
                        "sheet_name": sheet_name,
                        "result": result
                    }
                    logger.info(f"问题 '{question[:30]}...' 回答完成")
                except Exception as e:
                    logger.error(f"问题 '{question[:30]}...' 回答失败: {e}")
                    results[question_key] = {
                        "question": question,
                        "error": str(e)
                    }
            else:
                results[question_key] = {
                    "question": question,
                    "error": "未找到相关的工作表"
                }
        
        return results
    
    def _find_best_sheet(self, question: str, 
                        sheet_samples: List[Dict]) -> Optional[Dict]:
        """
        找到最相关的工作表
        
        Args:
            question: 用户问题
            sheet_samples: 工作表样本数据列表
            
        Returns:
            Optional[Dict]: 最相关的工作表
        """
        question_lower = question.lower()
        best_sheet = None
        best_score = 0
        
        for sheet in sheet_samples:
            score = 0
            columns = sheet.get('columns', [])
            sheet_name = sheet.get('sheet_name', '')
            
            # 检查工作表名
            if sheet_name.lower() in question_lower:
                score += 2
            
            # 检查列名
            for col in columns:
                if col and str(col).lower() in question_lower:
                    score += 1
            
            if score > best_score:
                best_score = score
                best_sheet = sheet
        
        return best_sheet if best_score > 0 else sheet_samples[0] if sheet_samples else None
    
    def analyze_trend(self, sheet_sample: Dict, 
                     column_name: str) -> Dict[str, Any]:
        """
        分析数据趋势
        
        Args:
            sheet_sample: 工作表样本数据
            column_name: 要分析的列名
            
        Returns:
            Dict: 趋势分析结果
        """
        data = sheet_sample.get('data', [])
        values = []
        
        for row in data:
            if column_name in row and row[column_name] is not None:
                try:
                    values.append(float(row[column_name]))
                except (ValueError, TypeError):
                    continue
        
        if not values:
            return {
                "trend": "无法分析",
                "summary": f"列 '{column_name}' 中没有有效的数值数据"
            }
        
        # 计算基本统计信息
        avg_value = sum(values) / len(values)
        min_value = min(values)
        max_value = max(values)
        
        # 判断趋势
        if len(values) >= 2:
            first_half = values[:len(values)//2]
            second_half = values[len(values)//2:]
            avg_first = sum(first_half) / len(first_half)
            avg_second = sum(second_half) / len(second_half)
            
            if avg_second > avg_first * 1.1:
                trend = "上升"
            elif avg_second < avg_first * 0.9:
                trend = "下降"
            else:
                trend = "平稳"
        else:
            trend = "数据不足"
        
        return {
            "trend": trend,
            "average": avg_value,
            "min": min_value,
            "max": max_value,
            "count": len(values),
            "summary": f"列 '{column_name}' 的{trend}趋势，平均值: {avg_value:.2f}，最小值: {min_value:.2f}，最大值: {max_value:.2f}"
        }
    
    def calculate_summary(self, sheet_sample: Dict) -> Dict[str, Any]:
        """
        生成工作表摘要
        
        Args:
            sheet_sample: 工作表样本数据
            
        Returns:
            Dict: 摘要信息
        """
        shape = sheet_sample.get('shape', [0, 0])
        columns = sheet_sample.get('columns', [])
        dtypes = sheet_sample.get('dtypes', {})
        
        # 统计各类型列的数量
        numeric_cols = sum(1 for dtype in dtypes.values() 
                          if 'int' in dtype.lower() or 'float' in dtype.lower())
        text_cols = sum(1 for dtype in dtypes.values() 
                       if dtype == 'object')
        date_cols = sum(1 for dtype in dtypes.values() 
                       if 'date' in dtype.lower() or 'time' in dtype.lower())
        
        return {
            "sheet_name": sheet_sample.get('sheet_name', ''),
            "total_rows": shape[0],
            "total_columns": shape[1],
            "numeric_columns": numeric_cols,
            "text_columns": text_cols,
            "date_columns": date_cols,
            "column_names": columns,
            "summary": f"工作表包含 {shape[0]} 行 {shape[1]} 列数据，其中数值列 {numeric_cols} 个，文本列 {text_cols} 个，日期列 {date_cols} 个"
        }