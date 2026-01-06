"""
直接分析Excel文件，找到项目支出金额最大的项目（优化版）
"""
import pandas as pd
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.core import Config
from src.excel import ExcelProcessor
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
    
    # 读取工作表数据，使用第3行作为表头（索引为2）
    df = pd.read_excel(file_path, sheet_name=target_sheet, header=2)
    logger.info(f"工作表 '{target_sheet}' 形状: {df.shape}")
    logger.info(f"列名: {df.columns.tolist()}")
    
    # 显示前10行数据
    logger.info(f"\n前10行数据:")
    for idx, row in df.head(10).iterrows():
        logger.info(f"行{idx}: {row.to_dict()}")
    
    # 识别关键列
    project_col = None
    amount_col = None
    performance_col = None
    
    for col in df.columns:
        col_str = str(col)
        if '项目名称' in col_str or '项目' in col_str:
            if project_col is None:
                project_col = col
                logger.info(f"找到项目名称列: {col}")
        if '合计' in col_str and ('预算' in col_str or '支出' in col_str):
            if amount_col is None:
                amount_col = col
                logger.info(f"找到金额列: {col}")
        if '绩效' in col_str and '目标' in col_str:
            performance_col = col
            logger.info(f"找到绩效目标列: {col}")
    
    logger.info(f"\n识别的列:")
    logger.info(f"  项目名称列: {project_col}")
    logger.info(f"  金额列: {amount_col}")
    logger.info(f"  绩效目标列: {performance_col}")
    
    # 分析数据
    if project_col and amount_col:
        # 清理金额列，转换为数值
        df[amount_col] = pd.to_numeric(df[amount_col], errors='coerce')
        
        # 移除空值
        df_clean = df.dropna(subset=[amount_col, project_col]).copy()
        
        logger.info(f"\n清理后的数据行数: {len(df_clean)}")
        
        # 按金额降序排序
        df_sorted = df_clean.sort_values(by=amount_col, ascending=False)
        
        logger.info(f"\n按金额排序的前15个项目:")
        for idx, (orig_idx, row) in enumerate(df_sorted.head(15).iterrows()):
            logger.info(f"  {idx+1}. {row[project_col]}: {row[amount_col]:,.2f}元")
        
        # 找到金额最大的项目
        if len(df_sorted) > 0:
            max_project = df_sorted.iloc[0]
            project_name = max_project[project_col]
            max_amount = max_project[amount_col]
            
            logger.info(f"\n{'='*80}")
            logger.info(f"项目支出金额最大的项目:")
            logger.info(f"  项目名称: {project_name}")
            logger.info(f"  支出金额: {max_amount:,.2f} 元")
            
            # 查找绩效目标
            if performance_col and performance_col in max_project and pd.notna(max_project[performance_col]):
                performance_goal = max_project[performance_col]
                logger.info(f"  绩效目标: {performance_goal}")
            else:
                logger.info(f"  绩效目标: 未在当前行找到")
                # 尝试在原始数据中查找该项目的绩效目标
                if performance_col:
                    for idx, row in df.iterrows():
                        if row[project_col] == project_name and pd.notna(row[performance_col]):
                            logger.info(f"  绩效目标: {row[performance_col]}")
                            break
            
            logger.info(f"{'='*80}")
        else:
            logger.warning("没有找到有效的项目数据")
    else:
        logger.error("无法识别项目名称列或金额列")
        logger.info(f"所有列名: {df.columns.tolist()}")


if __name__ == "__main__":
    main()