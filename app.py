import gradio as gr
import PyPDF2
import docx
import requests
import json
from typing import Optional, Dict, List
from zhipuai import ZhipuAI  # 新增导入

# 智谱开放平台API配置
ZHIPU_API_KEY = "YOUR-API-KEY"  # 更新API密钥
ZHIPU_MODEL = "glm-4-flash-250414"  # 更新模型名称

# ------------------------------
# MCP协议工具函数（核心，需严格遵循规范）
# ------------------------------
def read_pdf(file_path: str) -> str:
    """读取PDF文件内容（MCP工具）
    Args:
        file_path: PDF文件的本地路径或临时路径
    Returns:
        str: 提取的PDF文本内容，若读取失败返回错误信息
    """
    try:
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
        return text
    except Exception as e:
        return f"PDF读取失败: {str(e)}"


def read_word(file_path: str) -> str:
    """读取Word文件内容（MCP工具）
    Args:
        file_path: Word文件的本地路径或临时路径（支持.docx）
    Returns:
        str: 提取的Word文本内容，若读取失败返回错误信息
    """
    try:
        doc = docx.Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs])
    except Exception as e:
        return f"Word读取失败: {str(e)}"


def read_txt(file_path: str) -> str:
    """读取TXT文件内容（MCP工具）
    Args:
        file_path: TXT文件的本地路径或临时路径
    Returns:
        str: 提取的TXT文本内容，若读取失败返回错误信息
    """
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception as e:
        return f"TXT读取失败: {str(e)}"


def parse_document(file_path: str) -> str:
    """根据文件类型解析文档内容（MCP核心工具）
    Args:
        file_path: 文档文件的本地路径或临时路径（支持.pdf/.docx/.txt）
    Returns:
        str: 解析后的文本内容；若格式不支持，返回错误提示
    """
    if not file_path:
        return "文件路径为空"
    
    if file_path.endswith(".pdf"):
        return read_pdf(file_path)
    elif file_path.endswith(".docx"):
        return read_word(file_path)
    elif file_path.endswith(".txt"):
        return read_txt(file_path)
    else:
        return "不支持的文件格式，仅支持PDF(.pdf)、Word(.docx)、TXT(.txt)"


def call_model_api(prompt: str, max_tokens: int = 1024) -> str:
    """调用智谱模型API生成文本（MCP工具）
    Args:
        prompt: 模型输入提示词
        max_tokens: 生成文本的最大长度，默认1024
    Returns:
        str: 模型生成的文本；若调用失败，返回错误信息
    """
    if not ZHIPU_API_KEY:
        return "请配置智谱开放平台API密钥（ZHIPU_API_KEY）"
    
    try:
        client = ZhipuAI(api_key=ZHIPU_API_KEY)
        response = client.chat.completions.create(
            model=ZHIPU_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"API调用失败: {str(e)}"


def generate_summary(text: str) -> str:
    """生成文档摘要（MCP工具）
    Args:
        text: 待摘要的文档文本（建议长度50-3000字）
    Returns:
        str: 文档摘要（≤300字）；若文本过短，返回提示信息
    """
    if len(text) < 50:
        return "文档内容过短（少于50字），无法生成摘要"
    
    prompt = f"""请总结以下文档的核心内容，要求简洁明了，不超过300字：
    {text[:3000]}  # 限制输入长度，避免超出模型上下文
    """
    return call_model_api(prompt, max_tokens=300)


def extract_key_info(text: str) -> str:
    """提取文档关键信息（MCP工具）
    Args:
        text: 待提取信息的文档文本（建议长度50-3000字）
    Returns:
        str: 结构化的关键信息（含主要观点、数据、结论）；若文本过短，返回提示信息
    """
    if len(text) < 50:
        return "文档内容过短（少于50字），无法提取关键信息"
    
    prompt = f"""请从以下文档中提取关键信息，包括主要观点、重要数据、核心结论等，用结构化的方式（如分点、表格）呈现：
    {text[:3000]}
    """
    return call_model_api(prompt, max_tokens=500)


def document_qa(text: str, question: str) -> str:
    """基于文档内容回答问题（MCP工具）
    Args:
        text: 文档文本（建议长度50-3000字）
        question: 待回答的问题
    Returns:
        str: 基于文档的回答；若问题为空或文本过短，返回提示信息
    """
    if not question:
        return "请输入问题"
    if len(text) < 50:
        return "文档内容过短（少于50字），无法回答问题"
    
    prompt = f"""基于以下文档内容，回答问题：{question}
    文档内容：{text[:3000]}
    要求：只能根据文档内容回答，不编造信息；若文档无相关内容，需明确说明
    """
    return call_model_api(prompt, max_tokens=500)


def translate_text(text: str, target_lang: str) -> str:
    """翻译文本到目标语言（MCP工具）
    Args:
        text: 待翻译的文本（建议长度10-2000字）
        target_lang: 目标语言（支持：中文、英文、日文、韩文、法文、德文）
    Returns:
        str: 翻译后的文本；若文本过短，返回提示信息
    """
    if len(text) < 10:
        return "文本过短（少于10字），无法翻译"
    supported_langs = ["中文", "英文", "日文", "韩文", "法文", "德文"]
    if target_lang not in supported_langs:
        return f"不支持的目标语言：{target_lang}（支持：{','.join(supported_langs)}）"
    
    prompt = f"""请将以下文本翻译成{target_lang}，保持原意准确，语言流畅：
    {text[:2000]}
    """
    return call_model_api(prompt, max_tokens=2000)


def format_conversion(text: str, target_format: str) -> str:
    """转换文本格式（MCP工具）
    Args:
        text: 待转换的文本（建议长度50-3000字）
        target_format: 目标格式（支持：Markdown、表格、项目符号列表、编号列表）
    Returns:
        str: 转换后的文本；若文本过短，返回提示信息
    """
    if len(text) < 50:
        return "文本过短（少于50字），无法转换格式"
    supported_formats = ["Markdown", "表格", "项目符号列表", "编号列表"]
    if target_format not in supported_formats:
        return f"不支持的目标格式：{target_format}（支持：{','.join(supported_formats)}）"
    
    prompt = f"""请将以下文本转换为{target_format}格式，保持内容完整和结构清晰：
    {text[:3000]}
    """
    return call_model_api(prompt, max_tokens=1000)


# ------------------------------
# Gradio界面与MCP服务启动
# ------------------------------
def main():
    with gr.Blocks(title="智能文档处理助手") as demo:
        gr.Markdown("# 📄 智能文档处理助手")
        gr.Markdown("基于大模型的文档处理工具，支持摘要、问答、翻译等功能（MCP兼容）")
        
        with gr.Row():
            with gr.Column(scale=1):
                file_input = gr.File(label="上传文档", file_types=[".pdf", ".docx", ".txt"])
                load_btn = gr.Button("加载文档")
                
                with gr.Accordion("文档处理功能", open=True):
                    summary_btn = gr.Button("生成摘要")
                    key_info_btn = gr.Button("提取关键信息")
                
                with gr.Accordion("问答与翻译", open=True):
                    question_input = gr.Textbox(label="输入问题")
                    qa_btn = gr.Button("文档问答")
                    
                    target_lang = gr.Dropdown(
                        ["中文", "英文", "日文", "韩文", "法文", "德文"],
                        label="目标语言",
                        value="中文"
                    )
                    translate_btn = gr.Button("翻译文档")
                
                with gr.Accordion("格式转换", open=True):
                    target_format = gr.Dropdown(
                        ["Markdown", "表格", "项目符号列表", "编号列表"],
                        label="目标格式",
                        value="Markdown"
                    )
                    format_btn = gr.Button("转换格式")
            
            with gr.Column(scale=2):
                doc_content = gr.Textbox(label="文档内容", lines=10, interactive=False)
                result_output = gr.Markdown(label="处理结果")
        
        # 事件绑定（前端交互逻辑）
        def load_document(file):
            if not file:
                return "请上传文档"
            return parse_document(file.name)  # file.name为临时文件路径
        
        load_btn.click(
            fn=load_document,
            inputs=[file_input],
            outputs=[doc_content]
        )
        
        summary_btn.click(
            fn=generate_summary,
            inputs=[doc_content],
            outputs=[result_output]
        )
        
        key_info_btn.click(
            fn=extract_key_info,
            inputs=[doc_content],
            outputs=[result_output]
        )
        
        qa_btn.click(
            fn=document_qa,
            inputs=[doc_content, question_input],
            outputs=[result_output]
        )
        
        translate_btn.click(
            fn=translate_text,
            inputs=[doc_content, target_lang],
            outputs=[result_output]
        )
        
        format_btn.click(
            fn=format_conversion,
            inputs=[doc_content, target_format],
            outputs=[result_output]
        )
    
    # 启动服务
    demo.launch(
        mcp_server=True,
        server_name="0.0.0.0",
        server_port=7860,
        share=True  # 魔搭创空间部署时关闭share
    )


if __name__ == "__main__":
    main()
