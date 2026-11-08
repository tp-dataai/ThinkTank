# atguigu/import_process/state.py

from typing import TypedDict

class ImportGraphState(TypedDict):
    """
    图的状态定义，包含所有节点产生和消费的数据字段
    """
    task_id: str                # 任务唯一ID，用于追踪日志(一个任务可能会涉及很多个文件内容)

    # 流程控制标记
    # 问题：如果想要添加多模态的处理能力的话，是否需要在这个状态中添加更多的标记？
    # 例如：is_image_read_enabled, is_audio_read_enabled 等等
    is_md_read_enabled: bool    # 是否启用 Markdown 读取路径
    is_pdf_read_enabled: bool   # 是否启用 PDF 读取路径

    # 路径相关
    local_dir: str              # 当前工作目录或输出目录（实际工作中，不应该从本地读取，应该是先上传MinIO，再读取进行处理）
    local_file_path: str        # 原始输入文件路径
    file_title: str             # 文件标题（文件名去后缀）
    pdf_path: str               # PDF 文件路径 (如果输入是PDF)
    md_path: str                # Markdown 文件路径 (转换后或直接输入的)

    # 内容数据
    md_content: str             # Markdown 的全文内容
    chunks: list                # 切片列表
    item_name:str               # 识别主体的名称（例如：万用表）

    # 数据库关联
    embeddings_content: list    # 包含向量数的列表 ，准备写入 Milvus