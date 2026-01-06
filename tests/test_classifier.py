"""
分类器测试
"""
import pytest
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.rules import ExcelClassifier, ClassificationResult


def test_classifier_initialization():
    """测试分类器初始化"""
    classifier = ExcelClassifier("configs/classification_rules.yaml")
    assert classifier is not None
    assert len(classifier.rules) > 0


def test_get_all_categories():
    """测试获取所有分类"""
    classifier = ExcelClassifier("configs/classification_rules.yaml")
    categories = classifier.get_all_categories()
    assert len(categories) > 0
    assert "financial_statements" in categories
    assert "enterprise_operations" in categories


def test_get_category_rules():
    """测试获取分类规则"""
    classifier = ExcelClassifier("configs/classification_rules.yaml")
    rules = classifier.get_category_rules("financial_statements")
    assert rules is not None
    assert "keywords" in rules
    assert len(rules["keywords"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])