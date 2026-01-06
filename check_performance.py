import pandas as pd

# 读取绩效目标表
df = pd.read_excel('H:\\ExcelNLP\\250221tbjbmysb.xlsx', sheet_name=8, header=None)
print('绩效目标表前20行:')
for idx in range(20):
    print(f'行{idx}: {df.iloc[idx].to_dict()}')