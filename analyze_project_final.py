"""
直接分析Excel文件，找到项目支出金额最大的项目（最终修正版）
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
    
    # 文件路径
    file_path = "H:\\ExcelNLP\\250221tbjbmysb.xlsx"
    
    # 使用openpyxl获取所有工作表名称
    import openpyxl
    wb = openpyxl.load_workbook(file_path)
    sheet_names = wb.sheetnames
    wb.close()
    
    logger.info(f"所有工作表名称: {sheet_names}")
    
    # 找到项目支出预算表（索引7，第8个工作表）
    budget_sheet_name = sheet_names[7]  # "部门项目支出预算05-1"
    performance_sheet_name = sheet_names[8]  # "部门项目支出绩效目标05-2"
    
    logger.info(f"预算工作表: {budget_sheet_name}")
    logger.info(f"绩效工作表: {performance_sheet_name}")
    
    # 读取预算表
    df_budget = pd.read_excel(file_path, sheet_name=budget_sheet_name, header=None)
    logger.info(f"预算表形状: {df_budget.shape}")
    
    # 显示前10行
    logger.info(f"\n预算表前10行:")
    for idx in range(min(10, len(df_budget))):
        logger.info(f"行{idx}: {df_budget.iloc[idx].to_dict()}")
    
    # 使用第3行作为表头（索引为2）
    df_budget_clean = pd.read_excel(file_path, sheet_name=budget_sheet_name, header=2)
    logger.info(f"\n清洗后的列名: {df_budget_clean.columns.tolist()}")
    
    # 项目名称在第3列（索引为2）
    project_col = df_budget_clean.columns[2]
    logger.info(f"项目名称列索引: 2, 列名: {project_col}")
    
    # 合计金额在第9列（索引为8）
    amount_col = df_budget_clean.columns[8]
    logger.info(f"金额列索引: 8, 列名: {amount_col}")
    
    # 清理数据
    df_budget_clean[amount_col] = pd.to_numeric(df_budget_clean[amount_col], errors='coerce')
    df_budget_clean = df_budget_clean.dropna(subset=[amount_col, project_col]).copy()
    
    logger.info(f"\n清理后的数据行数: {len(df_budget_clean)}")
    
    # 按金额排序
    df_sorted = df_budget_clean.sort_values(by=amount_col, ascending=False)
    
    logger.info(f"\n按金额排序的前20个项目:")
    for idx, (orig_idx, row) in enumerate(df_sorted.head(20).iterrows()):
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
        
        # 在绩效目标表中查找该项目
        logger.info(f"\n在绩效目标表中查找该项目...")
        
        # 读取绩效目标表
        df_perf = pd.read_excel(file_path, sheet_name=performance_sheet_name, header=None)
        logger.info(f"绩效目标表形状: {df_perf.shape}")
        
        # 显示前10行
        logger.info(f"\n绩效目标表前10行:")
        for idx in range(min(10, len(df_perf))):
            logger.info(f"行{idx}: {df_perf.iloc[idx].to_dict()}")
        
        # 使用第3行作为表头
        df_perf_clean = pd.read_excel(file_path, sheet_name=performance_sheet_name, header=2)
        logger.info(f"\n绩效目标表清洗后的列名: {df_perf_clean.columns.tolist()}")
        
        # 查找项目名称列和绩效目标列
        perf_project_col = None
        perf_goal_col = None
        
        for idx, col in enumerate(df_perf_clean.columns):
            col_str = str(col)
            logger.info(f"列{idx}: {col_str}")
            if '项目名称' in col_str or '项目' in col_str:
                if perf_project_col is None:
                    perf_project_col = col
                    logger.info(f"  -> 识别为项目名称列")
            if '绩效' in col_str and '目标' in col_str:
                if perf_goal_col is None:
                    perf_goal_col = col
                    logger.info(f"  -> 识别为绩效目标列")
        
        logger.info(f"\n绩效目标表 - 项目名称列: {perf_project_col}")
        logger.info(f"绩效目标表 - 绩效目标列: {perf_goal_col}")
        
        if perf_project_col and perf_goal_col:
            # 查找匹配的项目
            found_performance = False
            for idx, row in df_perf_clean.iterrows():
                if pd.notna(row[perf_project_col]) and project_name in str(row[perf_project_col]):
                    performance_goal = row[perf_goal_col]
                    logger.info(f"  绩效目标: {performance_goal}")
                    found_performance = True
                    break
            
            if not found_performance:
                logger.info(f"  绩效目标: 未在绩效目标表中找到该项目")
        else:
            logger.info(f"  绩效目标: 无法识别项目名称列或绩效目标列")
        
        logger.info(f"{'='*80}")


if __name__ == "__main__":
    main()
