"""
Excel表格分类器
基于规则引擎对Excel表格进行分类
"""
import re
import yaml
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from loguru import logger


@dataclass
class ClassificationResult:
    """分类结果"""
    category: str
    confidence: float
    matched_rules: List[str]
    details: Dict[str, any]


class ExcelClassifier:
    """Excel表格分类器"""
    
    def __init__(self, rules_file: str):
        """
        初始化分类器
        
        Args:
            rules_file: 分类规则配置文件路径
        """
        self.rules_file = rules_file
        self.rules = self._load_rules()
        logger.info(f"分类器初始化完成，加载了 {len(self.rules)} 个分类规则")
    
    def _load_rules(self) -> Dict[str, Dict]:
        """
        加载分类规则
        
        Returns:
            Dict: 规则字典
        """
        try:
            with open(self.rules_file, 'r', encoding='utf-8') as f:
                rules = yaml.safe_load(f)
            logger.info(f"成功加载分类规则: {self.rules_file}")
            return rules
        except Exception as e:
            logger.error(f"加载分类规则失败: {e}")
            raise
    
    def classify(self, excel_info, sheet_samples: List[Dict]) -> Dict[str, ClassificationResult]:
        """
        对Excel表格进行分类
        
        Args:
            excel_info: Excel信息对象
            sheet_samples: 工作表样本数据列表
            
        Returns:
            Dict[str, ClassificationResult]: 每个工作表的分类结果
        """
        results = {}
        
        for sheet_sample in sheet_samples:
            sheet_name = sheet_sample.get('sheet_name', '')
            result = self._classify_sheet(sheet_sample, excel_info.file_name)
            results[sheet_name] = result
            logger.info(f"工作表 '{sheet_name}' 分类结果: {result.category} (置信度: {result.confidence:.2f})")
        
        return results
    
    def _classify_sheet(self, sheet_sample: Dict, file_name: str) -> ClassificationResult:
        """
        对单个工作表进行分类
        
        Args:
            sheet_sample: 工作表样本数据
            file_name: 文件名
            
        Returns:
            ClassificationResult: 分类结果
        """
        scores = {}
        matched_rules = {}
        
        # 提取特征
        features = self._extract_features(sheet_sample, file_name)
        
        # 对每个分类规则进行评分
        for category, rule in self.rules.items():
            score, rules_used = self._calculate_score(category, rule, features)
            if score > 0:
                scores[category] = score
                matched_rules[category] = rules_used
        
        # 选择得分最高的分类
        if scores:
            best_category = max(scores, key=scores.get)
            confidence = scores[best_category]
        else:
            best_category = "unknown"
            confidence = 0.0
            matched_rules[best_category] = []
        
        return ClassificationResult(
            category=best_category,
            confidence=confidence,
            matched_rules=matched_rules.get(best_category, []),
            details={
                "all_scores": scores,
                "features": features
            }
        )
    
    def _extract_features(self, sheet_sample: Dict, file_name: str) -> Dict[str, any]:
        """
        提取工作表特征
        
        Args:
            sheet_sample: 工作表样本数据
            file_name: 文件名
            
        Returns:
            Dict: 特征字典
        """
        features = {
            "file_name": file_name.lower(),
            "sheet_name": sheet_sample.get('sheet_name', '').lower(),
            "headers": [h.lower() if h else '' for h in sheet_sample.get('columns', [])],
            "data_sample": sheet_sample.get('data', []),
            "row_count": sheet_sample.get('shape', [0, 0])[0],
            "col_count": sheet_sample.get('shape', [0, 0])[1],
            "dtypes": sheet_sample.get('dtypes', {})
        }
        
        # 提取所有文本内容
        all_text = []
        all_text.append(file_name.lower())
        all_text.append(sheet_sample.get('sheet_name', '').lower())
        all_text.extend([h.lower() if h else '' for h in sheet_sample.get('columns', [])])
        
        for row in sheet_sample.get('data', [])[:5]:  # 只取前5行数据
            for value in row.values():
                if value is not None:
                    all_text.append(str(value).lower())
        
        features["all_text"] = " ".join(all_text)
        
        return features
    
    def _calculate_score(self, category: str, rule: Dict, 
                        features: Dict) -> Tuple[float, List[str]]:
        """
        计算分类得分
        
        Args:
            category: 分类名称
            rule: 分类规则
            features: 特征字典
            
        Returns:
            Tuple[float, List[str]]: (得分, 使用的规则列表)
        """
        score = 0.0
        rules_used = []
        
        # 1. 关键词匹配 (权重: 0.4)
        if 'keywords' in rule:
            keyword_score, keyword_matches = self._match_keywords(
                rule['keywords'], features['all_text']
            )
            if keyword_score > 0:
                score += keyword_score * 0.4
                rules_used.extend([f"关键词: {kw}" for kw in keyword_matches])
        
        # 2. 模式匹配 (权重: 0.3)
        if 'patterns' in rule:
            pattern_score, pattern_matches = self._match_patterns(
                rule['patterns'], features['file_name'], features['sheet_name']
            )
            if pattern_score > 0:
                score += pattern_score * 0.3
                rules_used.extend([f"模式: {pm}" for pm in pattern_matches])
        
        # 3. 表头匹配 (权重: 0.2)
        if 'keywords' in rule and features['headers']:
            header_score, header_matches = self._match_headers(
                rule['keywords'], features['headers']
            )
            if header_score > 0:
                score += header_score * 0.2
                rules_used.extend([f"表头: {hm}" for hm in header_matches])
        
        # 4. 结构特征匹配 (权重: 0.1)
        if 'structure_features' in rule:
            structure_score = self._match_structure(
                rule['structure_features'], features
            )
            if structure_score > 0:
                score += structure_score * 0.1
                rules_used.append("结构特征匹配")
        
        return min(score, 1.0), rules_used
    
    def _match_keywords(self, keywords: List[str], text: str) -> Tuple[float, List[str]]:
        """
        匹配关键词
        
        Args:
            keywords: 关键词列表
            text: 待匹配文本
            
        Returns:
            Tuple[float, List[str]]: (得分, 匹配的关键词列表)
        """
        matched = []
        for keyword in keywords:
            if keyword.lower() in text:
                matched.append(keyword)
        
        score = len(matched) / len(keywords) if keywords else 0
        return score, matched
    
    def _match_patterns(self, patterns: List[str], file_name: str, 
                       sheet_name: str) -> Tuple[float, List[str]]:
        """
        匹配正则表达式模式
        
        Args:
            patterns: 模式列表
            file_name: 文件名
            sheet_name: 工作表名
            
        Returns:
            Tuple[float, List[str]]: (得分, 匹配的模式列表)
        """
        matched = []
        full_name = f"{file_name} {sheet_name}"
        
        for pattern in patterns:
            try:
                if re.search(pattern, full_name, re.IGNORECASE):
                    matched.append(pattern)
            except re.error:
                continue
        
        score = len(matched) / len(patterns) if patterns else 0
        return score, matched
    
    def _match_headers(self, keywords: List[str], 
                      headers: List[str]) -> Tuple[float, List[str]]:
        """
        匹配表头
        
        Args:
            keywords: 关键词列表
            headers: 表头列表
            
        Returns:
            Tuple[float, List[str]]: (得分, 匹配的表头列表)
        """
        matched = []
        header_text = " ".join([h.lower() for h in headers])
        
        for keyword in keywords:
            if keyword.lower() in header_text:
                matched.append(keyword)
        
        score = len(matched) / len(keywords) if keywords else 0
        return score, matched
    
    def _match_structure(self, structure_features: List[str], 
                        features: Dict) -> float:
        """
        匹配结构特征
        
        Args:
            structure_features: 结构特征列表
            features: 特征字典
            
        Returns:
            float: 得分
        """
        score = 0.0
        
        # 检查时间序列数据
        if "时间序列数据" in structure_features:
            # 检查是否有日期类型的列
            date_cols = sum(1 for dtype in features['dtypes'].values() 
                          if 'date' in dtype.lower() or 'time' in dtype.lower())
            if date_cols > 0:
                score += 0.3
        
        # 检查指标列
        if "指标列" in structure_features:
            # 检查是否有数值类型的列
            numeric_cols = sum(1 for dtype in features['dtypes'].values() 
                             if 'int' in dtype.lower() or 'float' in dtype.lower())
            if numeric_cols > 0:
                score += 0.3
        
        # 检查多维度汇总
        if "多维度汇总" in structure_features:
            if features['col_count'] > 5:
                score += 0.2
        
        # 检查百分比计算
        if "百分比计算" in structure_features:
            for header in features['headers']:
                if '%' in header or '率' in header or '比' in header:
                    score += 0.2
                    break
        
        return score
    
    def get_all_categories(self) -> List[str]:
        """
        获取所有分类类别
        
        Returns:
            List[str]: 分类类别列表
        """
        return list(self.rules.keys())
    
    def get_category_rules(self, category: str) -> Optional[Dict]:
        """
        获取指定分类的规则
        
        Args:
            category: 分类名称
            
        Returns:
            Optional[Dict]: 分类规则
        """
        return self.rules.get(category)