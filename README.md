# ExcelNLP - Excel自然语言处理工具

基于本地小模型的Excel表格分析和问答系统，支持企业运营、财务报表、政府预算、政府统计等多种表格类型的智能分析和自然语言问答。

## 功能特性

- 📊 **Excel处理**: 支持读取和解析Excel文件（.xlsx, .xls, .xlsm）
- 🏷️ **智能分类**: 基于规则引擎自动分类表格类型（企业运营、财务报表、政府预算、政府统计等）
- 🔍 **信息抽取**: 使用本地小模型精确抽取表格中的关键信息
- 💬 **自然语言问答**: 支持用自然语言提问，自动从表格中查找答案
- 🤖 **本地模型**: 支持Ollama等本地小模型服务，数据隐私安全
- 🚀 **REST API**: 提供完整的REST API接口

## 技术栈

- **Python 3.9+**
- **FastAPI**: Web框架
- **Ollama**: 本地模型服务
- **openpyxl**: Excel文件处理
- **pandas**: 数据处理
- **PyYAML**: 配置管理

## 安装步骤

### 1. 安装Python依赖

```bash
pip install -r requirements.txt
```

### 2. 安装Ollama

访问 [Ollama官网](https://ollama.com/) 下载并安装Ollama。

### 3. 拉取模型

```bash
# 拉取Qwen2.5模型（推荐）
ollama pull qwen2.5:7b

# 或者拉取其他模型
ollama pull llama3.2:3b
ollama pull gemma2:9b
```

### 4. 启动Ollama服务

```bash
ollama serve
```

### 5. 配置系统

编辑 `configs/config.yaml` 文件，根据需要修改配置：

```yaml
model:
  type: "ollama"
  name: "qwen2.5:7b"  # 修改为你使用的模型名称
  host: "http://localhost:11434"
```

## 使用方法

### 启动服务

```bash
python main.py
```

服务将在 `http://localhost:8000` 启动。

### API接口

#### 1. 健康检查

```bash
GET http://localhost:8000/health
```

#### 2. 上传Excel文件

```bash
POST http://localhost:8000/upload
Content-Type: multipart/form-data

file: [Excel文件]
```

#### 3. 分析Excel文件

```bash
POST http://localhost:8000/analyze
Content-Type: multipart/form-data

file_path: [文件路径]
extract_data: true
classify: true
```

#### 4. 问答接口

```bash
POST http://localhost:8000/qa
Content-Type: multipart/form-data

file_path: [文件路径]
question: "这个表格的总销售额是多少？"
sheet_name: [可选，工作表名称]
```

#### 5. 批量问答

```bash
POST http://localhost:8000/batch_qa
Content-Type: multipart/form-data

file_path: [文件路径]
questions: ["问题1", "问题2", "问题3"]
```

### API文档

启动服务后，访问 `http://localhost:8000/docs` 查看完整的API文档。

## 项目结构

```
ExcelNLP/
├── src/
│   ├── core/              # 核心模块
│   │   └── config.py      # 配置管理
│   ├── excel/             # Excel处理
│   │   └── processor.py   # Excel处理器
│   ├── rules/             # 规则引擎
│   │   └── classifier.py  # 分类器
│   ├── models/            # 本地模型接口
│   │   ├── ollama_client.py
│   │   └── model_factory.py
│   ├── extraction/        # 信息抽取
│   │   └── extractor.py   # 数据抽取器
│   └── qa/                # 问答系统
│       └── qa_system.py   # 问答系统
├── configs/               # 配置文件
│   ├── config.yaml
│   └── classification_rules.yaml
├── prompts/               # Prompt模板
│   ├── extraction/
│   │   ├── general_extraction.txt
│   │   └── financial_extraction.txt
│   └── qa/
│       └── question_answering.txt
├── tests/                 # 测试
├── data/                  # 示例数据
├── logs/                  # 日志
├── main.py                # 主程序
└── requirements.txt       # 依赖列表
```

## 支持的表格类型

- 企业运营（销售、营收、成本、库存等）
- 财务报表（资产负债表、利润表、现金流量表）
- 政府预算（预算执行、财政支出等）
- 政府统计（GDP、CPI、人口统计等）
- 人力资源（员工、薪资、考勤等）
- 库存管理（库存、物料、盘点等）
- 销售管理（订单、客户、业绩等）

## 配置说明

### 模型配置

```yaml
model:
  type: "ollama"              # 模型类型
  name: "qwen2.5:7b"          # 模型名称
  host: "http://localhost:11434"  # Ollama服务地址
  timeout: 120                # 超时时间（秒）
  max_tokens: 2048            # 最大token数
  temperature: 0.7            # 温度参数
```

### Excel配置

```yaml
excel:
  supported_formats: [".xlsx", ".xls", ".xlsm"]
  max_file_size: 50           # 最大文件大小（MB）
  max_sheets: 20              # 最大工作表数
  max_rows: 10000             # 最大行数
  max_cols: 500               # 最大列数
```

### API配置

```yaml
api:
  host: "0.0.0.0"
  port: 8000
  enable_cors: true
  allowed_origins: ["*"]
```

## 注意事项

1. **Ollama服务**: 确保Ollama服务正在运行，并且已经拉取了所需的模型
2. **文件大小**: 默认最大支持50MB的Excel文件
3. **内存使用**: 处理大型Excel文件时可能需要较多内存
4. **模型性能**: 小模型的性能取决于硬件配置，建议使用至少8GB内存

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！