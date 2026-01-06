"""
直接分析Excel文件，找到项目支出金额最大的项目（最终版）
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
    
    # 读取项目支出预算表（05-1）
    df_budget = pd.read_excel(file_path, sheet_name="部门项目支出预算05-1", header=None)
    logger.info(f"工作表 '部门项目支出预算05-1' 形状: {df_budget.shape}")
    
    # 读取项目支出绩效目标表（05-2）
    df_performance = pd.read_excel(file_path, sheet_name="部门项目支出绩效目标05-2", header=None)
    logger.info(f"工作表 '部门项目支出绩效目标05-2' 形状: {df_performance.shape}")
    
    # 显示预算表的前10行
    logger.info(f"\n预算表前10行:")
    for idx, row in df_budget.head(10).iterrows():
        logger.info(f"行{idx}: {row.to_dict()}")
    
    # 显示绩效目标表的前10行
    logger.info(f"\n绩效目标表前10行:")
    for idx, row in df_performance.head(10).iterrows():
        logger.info(f"行{idx}: {row.to_dict()}")
    
    # 分析预算表 - 找到第3行作为表头
    df_budget_clean = pd.read_excel(file_path, sheet_name="部门项目支出预算05-1", header=2)
    logger.info(f"\n预算表清洗后的列名: {df_budget_clean.columns.tolist()}")
    
    # 找到项目名称列（第3列，索引为2）
    project_col = df_budget_clean.columns[2]
    logger.info(f"项目名称列: {project_col}")
    
    # 找到合计列（第9列，索引为8）
    amount_col = df_budget_clean.columns[8]
    logger.info(f"金额列: {amount_col}")
    
    # 清理数据
    df_budget_clean[amount_col] = pd.to_numeric(df_budget_clean[amount_col], errors='coerce')
    df_budget_clean = df_budget_clean.dropna(subset=[amount_col, project_col])
    
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
        found_performance = False
        
        # 显示绩效目标表的列名
        df_perf_clean = pd.read_excel(file_path, sheet_name="部门项目支出绩效目标05-2", header=2)
        logger.info(f"绩效目标表列名: {df_perf_clean.columns.tolist()}")
        
        # 查找项目名称列和绩效目标列
        perf_project_col = None
        perf_goal_col = None
        
        for col in df_perf_clean.columns:
            col_str = str(col)
            if '项目名称' in col_str or '项目' in col_str:
                if perf_project_col is None:
                    perf_project_col = col
            if '绩效' in col_str or '目标' in col_str:
                if perf_goal_col is None:
                    perf_goal_col = col
        
        logger.info(f"绩效目标表 - 项目名称列: {perf_project_col}")
        logger.info(f"绩效目标表 - 绩效目标列: {perf_goal_col}")
        
        if perf_project_col and perf_goal_col:
            # 查找匹配的项目
            for idx, row in df_perf_clean.iterrows():
                if pd.notna(row[perf_project_col]) and project_name in str(row[perf_project_col]):
                    performance_goal = row[perf_goal_col]
                    logger.info(f"  绩效目标: {performance_goal}")
                    found_performance = True
                    break
        
        if not found_performance:
            logger.info(f"  绩效目标: 未在绩效目标表中找到")
        
        logger.info(f"{'='*80}")


if __name__ == "__main__":
    main()