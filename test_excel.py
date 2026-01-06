"""
测试Excel分析脚本
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.core import Config
from src.excel import ExcelProcessor
from src.rules import ExcelClassifier
from src.models import ModelFactory
from src.extraction import DataExtractor
from src.qa import QASystem
from loguru import logger


def main():
    """主测试函数"""
    logger.info("开始测试ExcelNLP系统")
    
    # 1. 初始化配置
    logger.info("1. 初始化配置...")
    config = Config()
    logger.info(f"模型配置: {config.get_model_config()}")
    
    # 2. 初始化Excel处理器
    logger.info("2. 初始化Excel处理器...")
    excel_config = config.get_excel_config()
    excel_processor = ExcelProcessor(
        max_rows=excel_config.get('max_rows', 10000),
        max_cols=excel_config.get('max_cols', 500)
    )
    
    # 3. 验证Excel文件
    file_path = "H:\\ExcelNLP\\250221tbjbmysb.xlsx"
    logger.info(f"3. 验证Excel文件: {file_path}")
    is_valid, errors = excel_processor.validate_excel(file_path)
    if not is_valid:
        logger.error(f"Excel文件验证失败: {errors}")
        return
    
    logger.info("Excel文件验证通过")
    
    # 4. 加载Excel信息
    logger.info("4. 加载Excel信息...")
    excel_info = excel_processor.load_excel(file_path)
    logger.info(f"文件名: {excel_info.file_name}")
    logger.info(f"工作表数量: {excel_info.total_sheets}")
    for sheet in excel_info.sheets:
        logger.info(f"  - {sheet.name}: {sheet.rows}行 x {sheet.cols}列")
    
    # 5. 获取工作表样本数据
    logger.info("5. 获取工作表样本数据...")
    sheet_samples = []
    for sheet in excel_info.sheets:
        sample = excel_processor.get_sheet_data_sample(file_path, sheet.name, n_rows=10)
        sheet_samples.append(sample)
        logger.info(f"工作表 '{sheet.name}' 样本:")
        logger.info(f"  列名: {sample.get('columns', [])}")
        logger.info(f"  数据行数: {sample.get('shape', [0, 0])[0]}")
    
    # 6. 初始化模型客户端
    logger.info("6. 初始化模型客户端...")
    try:
        model_config = config.get_model_config()
        model_client = ModelFactory.create_client(model_config)
        logger.info(f"模型客户端初始化成功: {model_config.get('name')}")
    except Exception as e:
        logger.error(f"模型客户端初始化失败: {e}")
        logger.info("将使用默认抽取方法（不使用模型）")
        model_client = None
    
    # 7. 初始化分类器
    logger.info("7. 初始化分类器...")
    rules_config = config.get_rules_config()
    classifier = ExcelClassifier(rules_config.get('classification_rules'))
    
    # 8. 分类
    logger.info("8. 对工作表进行分类...")
    classifications = classifier.classify(excel_info, sheet_samples)
    for sheet_name, classification in classifications.items():
        logger.info(f"工作表 '{sheet_name}': {classification.category} (置信度: {classification.confidence:.2f})")
    
    # 9. 初始化信息抽取器
    logger.info("9. 初始化信息抽取器...")
    if model_client:
        extraction_config = config.get_extraction_config()
        extractor = DataExtractor(
            model_client=model_client,
            prompt_templates_dir=extraction_config.get('prompt_templates', 'prompts/extraction/')
        )
    else:
        extractor = None
    
    # 10. 信息抽取
    logger.info("10. 进行信息抽取...")
    extractions = {}
    for sheet_sample in sheet_samples:
        sheet_name = sheet_sample.get('sheet_name', '')
        category = classifications.get(sheet_name).category
        
        if extractor:
            try:
                extraction = extractor.extract(sheet_sample, category, excel_info.file_name)
                extractions[sheet_name] = extraction
                logger.info(f"工作表 '{sheet_name}' 信息抽取完成")
            except Exception as e:
                logger.error(f"工作表 '{sheet_name}' 信息抽取失败: {e}")
                extractions[sheet_name] = {}
        else:
            logger.info(f"跳过工作表 '{sheet_name}' 的信息抽取（无模型客户端）")
    
    # 11. 初始化问答系统
    logger.info("11. 初始化问答系统...")
    if model_client:
        qa_config = config.get_qa_config()
        qa_system = QASystem(
            model_client=model_client,
            prompt_template_path=qa_config.get('prompt_template', 'prompts/qa/question_answering.txt')
        )
    else:
        qa_system = None
    
    # 12. 问答测试
    logger.info("12. 问答测试...")
    question = "项目支出金额最大的项目名称以及他的绩效目标是什么？"
    logger.info(f"用户问题: {question}")
    
    if qa_system and extractions:
        # 找到最相关的工作表
        best_sheet = qa_system._find_best_sheet(question, sheet_samples)
        if best_sheet:
            sheet_name = best_sheet.get('sheet_name', '')
            category = classifications.get(sheet_name).category
            extraction = extractions.get(sheet_name, {})
            
            try:
                result = qa_system.answer(question, best_sheet, category, extraction, excel_info.file_name)
                logger.info(f"问答结果:")
                logger.info(f"  答案: {result.get('answer', '')}")
                logger.info(f"  置信度: {result.get('confidence', 0)}")
                logger.info(f"  证据: {result.get('evidence', [])}")
            except Exception as e:
                logger.error(f"问答失败: {e}")
        else:
            logger.warning("未找到相关的工作表")
    else:
        logger.warning("问答系统未初始化，跳过问答测试")
    
    # 13. 输出详细数据分析
    logger.info("13. 输出详细数据分析...")
    for sheet_sample in sheet_samples:
        sheet_name = sheet_sample.get('sheet_name', '')
        logger.info(f"\n工作表 '{sheet_name}' 详细数据:")
        logger.info(f"列名: {sheet_sample.get('columns', [])}")
        logger.info(f"数据类型: {sheet_sample.get('dtypes', {})}")
        
        # 显示前几行数据
        data_rows = sheet_sample.get('data', [])
        logger.info(f"前5行数据:")
        for i, row in enumerate(data_rows[:5]):
            logger.info(f"  行{i+1}: {row}")
    
    logger.info("测试完成！")


if __name__ == "__main__":
    main()