"""
ExcelNLP 主程序
FastAPI应用入口
"""
import os
import uvicorn
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional, List
from loguru import logger
import tempfile
import shutil

from src.core import Config
from src.excel import ExcelProcessor
from src.rules import ExcelClassifier
from src.models import ModelFactory
from src.extraction import DataExtractor
from src.qa import QASystem


# 初始化配置
config = Config()

# 配置日志
log_config = config.get_logging_config()
logger.add(
    log_config.get('file', 'logs/excelnlp.log'),
    level=log_config.get('level', 'INFO'),
    format=log_config.get('format'),
    rotation=log_config.get('rotation', '10 MB'),
    retention=log_config.get('retention', '30 days')
)

# 创建FastAPI应用
app = FastAPI(
    title="ExcelNLP API",
    description="Excel自然语言处理工具 - 基于本地小模型的Excel表格分析和问答系统",
    version="0.1.0"
)

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="static"), name="static")

# 配置CORS
api_config = config.get_api_config()
if api_config.get('enable_cors', True):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=api_config.get('allowed_origins', ["*"]),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# 初始化各个模块
excel_processor = None
classifier = None
model_client = None
extractor = None
qa_system = None


def initialize_components():
    """初始化所有组件"""
    global excel_processor, classifier, model_client, extractor, qa_system
    
    try:
        # 初始化Excel处理器
        excel_config = config.get_excel_config()
        excel_processor = ExcelProcessor(
            max_rows=excel_config.get('max_rows', 10000),
            max_cols=excel_config.get('max_cols', 500)
        )
        logger.info("Excel处理器初始化成功")
        
        # 初始化模型客户端（可选）
        try:
            model_config = config.get_model_config()
            model_client = ModelFactory.create_client(model_config)
            logger.info("模型客户端初始化成功")
        except Exception as e:
            logger.warning(f"模型客户端初始化失败，将使用默认抽取方法: {e}")
            model_client = None
        
        # 初始化分类器
        rules_config = config.get_rules_config()
        classifier = ExcelClassifier(rules_config.get('classification_rules'))
        logger.info("分类器初始化成功")
        
        # 初始化信息抽取器
        if model_client:
            extraction_config = config.get_extraction_config()
            extractor = DataExtractor(
                model_client=model_client,
                prompt_templates_dir=extraction_config.get('prompt_templates', 'prompts/extraction/')
            )
            logger.info("信息抽取器初始化成功")
        else:
            extractor = None
            logger.info("信息抽取器未初始化（无模型客户端）")
        
        # 初始化问答系统
        if model_client:
            qa_config = config.get_qa_config()
            qa_system = QASystem(
                model_client=model_client,
                prompt_template_path=qa_config.get('prompt_template', 'prompts/qa/question_answering.txt')
            )
            logger.info("问答系统初始化成功")
        else:
            qa_system = None
            logger.info("问答系统未初始化（无模型客户端）")
        
    except Exception as e:
        logger.error(f"组件初始化失败: {e}")
        raise


# 启动时初始化
@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info("ExcelNLP应用启动中...")
    initialize_components()
    logger.info("ExcelNLP应用启动完成")


@app.get("/")
async def root():
    """根路径 - 返回前端页面"""
    with open("static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/api")
async def api_info():
    """API信息"""
    return {
        "message": "ExcelNLP API",
        "version": "0.1.0",
        "description": "Excel自然语言处理工具 - 基于本地小模型的Excel表格分析和问答系统",
        "endpoints": {
            "POST /upload": "上传Excel文件",
            "POST /analyze": "分析Excel文件",
            "POST /qa": "单个问题问答",
            "POST /batch_qa": "批量问题问答",
            "GET /health": "健康检查"
        }
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "components": {
            "excel_processor": excel_processor is not None,
            "classifier": classifier is not None,
            "model_client": model_client is not None,
            "extractor": extractor is not None,
            "qa_system": qa_system is not None
        }
    }


@app.post("/upload")
async def upload_excel(file: UploadFile = File(...)):
    """
    上传Excel文件
    
    Args:
        file: Excel文件
        
    Returns:
        Dict: 上传结果
    """
    if not excel_processor:
        raise HTTPException(status_code=503, detail="Excel处理器未初始化")
    
    # 验证文件类型
    file_ext = os.path.splitext(file.filename)[1].lower()
    excel_config = config.get_excel_config()
    if file_ext not in excel_config.get('supported_formats', ['.xlsx', '.xls']):
        raise HTTPException(status_code=400, detail=f"不支持的文件格式: {file_ext}")
    
    # 保存临时文件
    temp_dir = tempfile.gettempdir()
    temp_file_path = os.path.join(temp_dir, file.filename)
    
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 验证Excel文件
        is_valid, errors = excel_processor.validate_excel(temp_file_path)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Excel文件验证失败: {errors}")
        
        # 加载Excel信息
        excel_info = excel_processor.load_excel(temp_file_path)
        
        return {
            "success": True,
            "file_name": file.filename,
            "file_path": temp_file_path,
            "excel_info": {
                "file_name": excel_info.file_name,
                "file_size": excel_info.file_size,
                "total_sheets": excel_info.total_sheets,
                "sheets": [
                    {
                        "name": sheet.name,
                        "rows": sheet.rows,
                        "cols": sheet.cols,
                        "has_merged_cells": sheet.has_merged_cells
                    }
                    for sheet in excel_info.sheets
                ]
            }
        }
    
    except Exception as e:
        logger.error(f"上传Excel文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@app.post("/analyze")
async def analyze_excel(
    file_path: str = Form(...),
    extract_data: bool = Form(True),
    classify: bool = Form(True)
):
    """
    分析Excel文件
    
    Args:
        file_path: Excel文件路径
        extract_data: 是否提取数据
        classify: 是否分类
        
    Returns:
        Dict: 分析结果
    """
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")
    
    try:
        # 加载Excel信息
        excel_info = excel_processor.load_excel(file_path)
        
        # 获取所有工作表的样本数据
        sheet_samples = []
        for sheet in excel_info.sheets:
            sample = excel_processor.get_sheet_data_sample(
                file_path, sheet.name, n_rows=10
            )
            sheet_samples.append(sample)
        
        results = {
            "file_name": excel_info.file_name,
            "total_sheets": excel_info.total_sheets,
            "sheets": {}
        }
        
        # 分类
        if classify and classifier:
            classifications = classifier.classify(excel_info, sheet_samples)
            for sheet_name, classification in classifications.items():
                if sheet_name not in results["sheets"]:
                    results["sheets"][sheet_name] = {}
                results["sheets"][sheet_name]["classification"] = {
                    "category": classification.category,
                    "confidence": classification.confidence,
                    "matched_rules": classification.matched_rules
                }
        
        # 信息抽取
        if extract_data and extractor:
            extractions = {}
            for sheet_sample in sheet_samples:
                sheet_name = sheet_sample.get('sheet_name', '')
                category = classifications.get(sheet_name, ClassificationResult(
                    category='unknown',
                    confidence=0.0,
                    matched_rules=[],
                    details={}
                )).category if classify else 'unknown'
                
                extraction = extractor.extract(sheet_sample, category, excel_info.file_name)
                extractions[sheet_name] = extraction
            
            for sheet_name, extraction in extractions.items():
                if sheet_name not in results["sheets"]:
                    results["sheets"][sheet_name] = {}
                results["sheets"][sheet_name]["extraction"] = extraction
        
        return {"success": True, "results": results}
    
    except Exception as e:
        logger.error(f"分析Excel文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@app.post("/simple_query")
async def simple_query(
    file_path: str = Form(...),
    question: str = Form(...)
):
    """
    简单查询接口（不依赖模型）
    
    Args:
        file_path: Excel文件路径
        question: 用户问题
        
    Returns:
        Dict: 查询结果
    """
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")
    
    try:
        import pandas as pd
        
        # 加载Excel信息
        excel_info = excel_processor.load_excel(file_path)
        
        # 分析问题类型
        question_lower = question.lower()
        
        # 尝试回答常见问题
        if "最大" in question and "金额" in question:
            # 查找金额最大的项目
            for sheet_idx, sheet in enumerate(excel_info.sheets):
                try:
                    df = pd.read_excel(file_path, sheet_name=sheet_idx, header=2)
                    # 查找包含金额的列
                    for col in df.columns:
                        if df[col].dtype in ['float64', 'int64']:
                            df_clean = df.dropna(subset=[col])
                            if len(df_clean) > 0:
                                max_row = df_clean.loc[df_clean[col].idxmax()]
                                # 尝试找到项目名称列
                                project_name = None
                                for c in df.columns:
                                    if df[c].dtype == 'object':
                                        project_name = max_row[c]
                                        break
                                
                                if project_name:
                                    return {
                                        "success": True,
                                        "question": question,
                                        "sheet_name": sheet.name,
                                        "result": {
                                            "answer": f"在'{sheet.name}'工作表中，金额最大的项目是：{project_name}，金额为：{max_row[col]:,.2f} 元",
                                            "source": f"工作表：{sheet.name}",
                                            "evidence": [f"项目：{project_name}", f"金额：{max_row[col]:,.2f} 元"]
                                        }
                                        }
                except Exception as e:
                    logger.warning(f"分析工作表 {sheet.name} 失败: {e}")
                    continue
        
        elif "总计" in question or "合计" in question or "总数" in question:
            # 计算总计
            for sheet_idx, sheet in enumerate(excel_info.sheets):
                try:
                    df = pd.read_excel(file_path, sheet_name=sheet_idx, header=2)
                    # 查找包含金额的列
                    for col in df.columns:
                        if df[col].dtype in ['float64', 'int64']:
                            total = df[col].sum()
                            if total > 0:
                                return {
                                    "success": True,
                                    "question": question,
                                    "sheet_name": sheet.name,
                                    "result": {
                                        "answer": f"在'{sheet.name}'工作表中，{col}列的总计为：{total:,.2f} 元",
                                        "source": f"工作表：{sheet.name}",
                                        "evidence": [f"列名：{col}", f"总计：{total:,.2f} 元"]
                                    }
                                }
                except Exception as e:
                    logger.warning(f"分析工作表 {sheet.name} 失败: {e}")
                    continue
        
        # 如果无法回答，返回基本信息
        return {
            "success": True,
            "question": question,
            "result": {
                "answer": f"抱歉，我无法直接回答这个问题。当前系统未启用AI模型功能。\n\n文件信息：\n- 文件名：{excel_info.file_name}\n- 工作表数量：{excel_info.total_sheets}\n- 工作表列表：{', '.join([s.name for s in excel_info.sheets])}\n\n您可以尝试询问：\n- \"金额最大的项目是什么？\"\n- \"总计是多少？\"",
                "source": "Excel文件基本信息",
                "evidence": [f"工作表：{s.name} ({s.rows}行 x {s.cols}列)" for s in excel_info.sheets[:5]]
            }
        }
    
    except Exception as e:
        logger.error(f"简单查询失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@app.post("/qa")
async def question_answering(
    file_path: str = Form(...),
    question: str = Form(...),
    sheet_name: Optional[str] = Form(None)
):
    """
    问答接口（需要模型支持）
    
    Args:
        file_path: Excel文件路径
        question: 用户问题
        sheet_name: 工作表名称（可选）
        
    Returns:
        Dict: 问答结果
    """
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")
    
    if not qa_system:
        raise HTTPException(status_code=503, detail="问答系统未初始化，请先启动Ollama服务")
    
    try:
        # 加载Excel信息
        excel_info = excel_processor.load_excel(file_path)
        
        # 获取工作表样本
        if sheet_name:
            sheet_sample = excel_processor.get_sheet_data_sample(file_path, sheet_name)
            sheet_samples = [sheet_sample]
        else:
            sheet_samples = []
            for sheet in excel_info.sheets:
                sample = excel_processor.get_sheet_data_sample(file_path, sheet.name)
                sheet_samples.append(sample)
        
        # 分类
        classifications = classifier.classify(excel_info, sheet_samples)
        
        # 信息抽取
        extractions = {}
        for sheet_sample in sheet_samples:
            s_name = sheet_sample.get('sheet_name', '')
            category = classifications.get(s_name).category
            extraction = extractor.extract(sheet_sample, category, excel_info.file_name)
            extractions[s_name] = extraction
        
        # 找到最相关的工作表
        best_sheet = qa_system._find_best_sheet(question, sheet_samples)
        if not best_sheet:
            best_sheet = sheet_samples[0] if sheet_samples else None
        
        if not best_sheet:
            raise HTTPException(status_code=400, detail="无法找到相关工作表")
        
        # 回答问题
        s_name = best_sheet.get('sheet_name', '')
        category = classifications.get(s_name).category
        extraction = extractions.get(s_name, {})
        
        result = qa_system.answer(question, best_sheet, category, extraction, excel_info.file_name)
        
        return {
            "success": True,
            "question": question,
            "sheet_name": s_name,
            "category": category,
            "result": result
        }
    
    except Exception as e:
        logger.error(f"问答失败: {e}")
        raise HTTPException(status_code=500, detail=f"问答失败: {str(e)}")


@app.post("/batch_qa")
async def batch_question_answering(
    file_path: str = Form(...),
    questions: List[str] = Form(...)
):
    """
    批量问答接口
    
    Args:
        file_path: Excel文件路径
        questions: 问题列表
        
    Returns:
        Dict: 批量问答结果
    """
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")
    
    if not qa_system:
        raise HTTPException(status_code=503, detail="问答系统未初始化")
    
    try:
        # 加载Excel信息
        excel_info = excel_processor.load_excel(file_path)
        
        # 获取所有工作表样本
        sheet_samples = []
        for sheet in excel_info.sheets:
            sample = excel_processor.get_sheet_data_sample(file_path, sheet.name)
            sheet_samples.append(sample)
        
        # 分类
        classifications = classifier.classify(excel_info, sheet_samples)
        
        # 信息抽取
        extractions = {}
        for sheet_sample in sheet_samples:
            s_name = sheet_sample.get('sheet_name', '')
            category = classifications.get(s_name).category
            extraction = extractor.extract(sheet_sample, category, excel_info.file_name)
            extractions[s_name] = extraction
        
        # 批量回答
        results = qa_system.batch_answer(
            questions, sheet_samples, classifications, extractions, excel_info.file_name
        )
        
        return {
            "success": True,
            "file_name": excel_info.file_name,
            "results": results
        }
    
    except Exception as e:
        logger.error(f"批量问答失败: {e}")
        raise HTTPException(status_code=500, detail=f"批量问答失败: {str(e)}")


def main():
    """主函数"""
    api_config = config.get_api_config()
    uvicorn.run(
        "main:app",
        host=api_config.get('host', '0.0.0.0'),
        port=api_config.get('port', 8000),
        reload=True
    )


if __name__ == "__main__":
    main()