"""
Excel处理器测试
"""
import pytest
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.excel import ExcelProcessor


def test_excel_processor_initialization():
    """测试Excel处理器初始化"""
    processor = ExcelProcessor(max_rows=1000, max_cols=100)
    assert processor.max_rows == 1000
    assert processor.max_cols == 100


def test_validate_nonexistent_file():
    """测试验证不存在的文件"""
    processor = ExcelProcessor()
    is_valid, errors = processor.validate_excel("nonexistent.xlsx")
    assert is_valid == False
    assert len(errors) > 0


def test_validate_unsupported_format():
    """测试验证不支持的格式"""
    processor = ExcelProcessor()
    # 创建一个临时文件
    temp_file = "temp_test.txt"
    with open(temp_file, 'w') as f:
        f.write("test")
    
    is_valid, errors = processor.validate_excel(temp_file)
    assert is_valid == False
    assert any("不支持的文件格式" in error for error in errors)
    
    # 清理
    os.remove(temp_file)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])