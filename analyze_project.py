"""
直接分析Excel文件，找到项目支出金额最大的项目
"""
import pandas as pd
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.core import Config
from src.excel import ExcelProcessor
from src.rules import ExcelClassifier
from loguru import logger


def main():
    """主函数"""
    logger.info("开始分析Excel文件...")
    
    # 初始化配置
    config = Config()
    excel_config = config.get_excel_config()
    excel_processor = ExcelProcessor(
        max_rows=excel_config.get('max_rows', 10000),
        max_cols=excel_config.get('max_cols', 500)
    )
    
    # 文件路径
    file_path = "H:\\ExcelNLP\\250221tbjbmysb.xlsx"
    
    # 加载Excel信息
    excel_info = excel_processor.load_excel(file_path)
    logger.info(f"文件包含 {excel_info.total_sheets} 个工作表")
    
    # 查找包含项目支出信息的工作表
    target_sheet = None
    for sheet in excel_info.sheets:
        if "项目支出" in sheet.name:
            target_sheet = sheet.name
            logger.info(f"找到目标工作表: {target_sheet}")
            break
    
    if not target_sheet:
        # 如果没有找到，尝试其他相关的工作表
        for sheet in excel_info.sheets:
            if "项目" in sheet.name and ("支出" in sheet.name or "预算" in sheet.name):
                target_sheet = sheet.name
                logger.info(f"找到相关工作表: {target_sheet}")
                break
    
    if not target_sheet:
        logger.error("未找到包含项目支出信息的工作表")
        return
    
    # 读取工作表数据
    df = pd.read_excel(file_path, sheet_name=target_sheet, header=None)
    logger.info(f"工作表 '{target_sheet}' 形状: {df.shape}")
    
    # 显示前20行数据以便分析
    logger.info(f"\n工作表 '{target_sheet}' 前20行数据:")
    for idx, row in df.head(20).iterrows():
        logger.info(f"行{idx}: {row.to_dict()}")
    
    # 尝试识别表头行
    header_row = None
    for idx in range(min(10, len(df))):
        row = df.iloc[idx]
        # 检查是否包含项目、金额、绩效等关键词
        row_text = " ".join([str(v) for v in row if pd.notna(v)])
        if any(keyword in row_text for keyword in ['项目', '金额', '支出', '绩效', '目标']):
            header_row = idx
            logger.info(f"可能的表头行: {idx}")
            logger.info(f"表头内容: {row_text}")
            break
    
    if header_row is not None:
        # 使用识别的表头行
        df_clean = pd.read_excel(file_path, sheet_name=target_sheet, header=header_row)
    else:
        # 使用默认第一行作为表头
        df_clean = pd.read_excel(file_path, sheet_name=target_sheet, header=0)
    
    logger.info(f"\n清洗后的列名: {df_clean.columns.tolist()}")
    logger.info(f"清洗后的数据形状: {df_clean.shape}")
    
    # 显示前几行数据
    logger.info(f"\n清洗后的前10行数据:")
    for idx, row in df_clean.head(10).iterrows():
        logger.info(f"行{idx}: {row.to_dict()}")
    
    # 查找包含金额/支出/预算的列
    amount_col = None
    project_col = None
    performance_col = None
    
    for col in df_clean.columns:
        col_str = str(col).lower()
        if '金额' in col_str or '支出' in col_str or '预算' in col_str:
            if amount_col is None:  # 找到第一个金额列
                amount_col = col
                logger.info(f"找到金额列: {col}")
        if '项目' in col_str and '名称' in col_str:
            project_col = col
            logger.info(f"找到项目名称列: {col}")
        if '绩效' in col_str and '目标' in col_str:
            performance_col = col
            logger.info(f"找到绩效目标列: {col}")
    
    # 如果没有找到项目名称列，尝试其他可能的列名
    if project_col is None:
        for col in df_clean.columns:
            col_str = str(col)
            if '项目' in col_str:
                project_col = col
                logger.info(f"找到项目列: {col}")
                break
    
    # 如果没有找到绩效目标列
    if performance_col is None:
        for col in df_clean.columns:
            col_str = str(col)
            if '绩效' in col_str or '目标' in col_str:
                performance_col = col
                logger.info(f"找到绩效/目标列: {col}")
                break
    
    logger.info(f"\n最终识别的列:")
    logger.info(f"  项目名称列: {project_col}")
    logger.info(f"  金额列: {amount_col}")
    logger.info(f"  绩效目标列: {performance_col}")
    
    # 分析数据
    if amount_col and project_col:
        # 清理金额列，转换为数值
        df_clean[amount_col] = pd.to_numeric(df_clean[amount_col], errors='coerce')
        
        # 移除空值
        df_clean = df_clean.dropna(subset=[amount_col, project_col])
        
        # 按金额降序排序
        df_sorted = df_clean.sort_values(by=amount_col, ascending=False)
        
        logger.info(f"\n按金额排序的前10个项目:")
        for idx, row in df_sorted.head(10).iterrows():
            logger.info(f"  {row[project_col]}: {row[amount_col]}")
        
        # 找到金额最大的项目
        if len(df_sorted) > 0:
            max_project = df_sorted.iloc[0]
            project_name = max_project[project_col]
            max_amount = max_project[amount_col]
            
            logger.info(f"\n{'='*60}")
            logger.info(f"项目支出金额最大的项目:")
            logger.info(f"  项目名称: {project_name}")
            logger.info(f"  支出金额: {max_amount}")
            
            if performance_col and performance_col in max_project:
                performance_goal = max_project[performance_col]
                logger.info(f"  绩效目标: {performance_goal}")
            else:
                logger.info(f"  绩效目标: 未找到")
            
            logger.info(f"{'='*60}")
        else:
            logger.warning("没有找到有效的项目数据")
    else:
        logger.error("无法识别项目名称列或金额列")
        logger.info(f"所有列名: {df_clean.columns.tolist()}")


if __name__ == "__main__":
    main()