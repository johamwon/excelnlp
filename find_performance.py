import pandas as pd

# 读取绩效目标表
df_perf = pd.read_excel('H:\\ExcelNLP\\250221tbjbmysb.xlsx', sheet_name=8, header=2)
print('绩效目标表列名:', df_perf.columns.tolist())

project_name = '云南省文化和旅游事业发展专项经费'
print('\n查找项目:', project_name)

# 查找项目
for idx, row in df_perf.iterrows():
    if pd.notna(row[df_perf.columns[2]]) and project_name in str(row[df_perf.columns[2]]):
        print('找到项目!')
        print('绩效目标:', row[df_perf.columns[3]] if len(df_perf.columns) > 3 else '未找到绩效目标列')
        break