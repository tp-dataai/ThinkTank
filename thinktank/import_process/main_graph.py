from langgraph.graph import StateGraph, START, END

from thinktank.import_process.state import ImportGraphState
from thinktank.tool.logger import logger
from thinktank.import_process.nodes.node_entry import NodeEntry
from thinktank.import_process.nodes.node_pdf_to_md import NodePDFToMD
from thinktank.import_process.nodes.node_md_img import NodeMDImg
from thinktank.import_process.nodes.node_document_split import NodeDocumentSplit
from thinktank.import_process.nodes.node_item_name_recognition import NodeItemNameRecognition
from thinktank.import_process.nodes.node_import_milvus import NodeImportMilvus
from thinktank.import_process.nodes.node_bge_embedding import NodeBGEEmbedding

class MainGraphRunner:
    def __init__(self):
        # 1、实例化构造器(builder) —— 专用于搭图
        self.builder = StateGraph(state_schema=ImportGraphState)
        
        # 2、添加节点
        self.add_nodes()
        
        # 3、添加边
        self.add_edges()

        # 4、懒加载，准备存放编译后的图
        self.graph = None

    def add_nodes(self):
        """添加节点"""
        self.builder.add_node(NodeEntry.name, NodeEntry())
        self.builder.add_node(NodePDFToMD.name, NodePDFToMD())
        self.builder.add_node(NodeMDImg.name, NodeMDImg())  # 修复：直接使用类属性
        self.builder.add_node(NodeDocumentSplit.name, NodeDocumentSplit())
        self.builder.add_node(NodeItemNameRecognition.name, NodeItemNameRecognition())
        self.builder.add_node(NodeBGEEmbedding.name, NodeBGEEmbedding())
        self.builder.add_node(NodeImportMilvus.name, NodeImportMilvus())

    def after_entry_router(self, state):
        """路由判断"""
        is_md_read_enabled = state.get("is_md_read_enabled", False)
        is_pdf_read_enabled = state.get("is_pdf_read_enabled", False)

        if is_pdf_read_enabled:
            return NodePDFToMD.name
        elif is_md_read_enabled:
            return NodeMDImg.name
        else:
            return END

    def add_edges(self):
        """添加边"""
        self.builder.add_edge(START, NodeEntry.name)

        # 条件边，建议加上路径映射
        self.builder.add_conditional_edges(
            NodeEntry.name,
            self.after_entry_router,
            {
                NodePDFToMD.name: NodePDFToMD.name,
                NodeMDImg.name: NodeMDImg.name,
                END: END
            }
        )

        # 顺序边（修复了漏连和死循环）
        self.builder.add_edge(NodePDFToMD.name, NodeMDImg.name)
        self.builder.add_edge(NodeMDImg.name, NodeDocumentSplit.name)
        self.builder.add_edge(NodeDocumentSplit.name, NodeItemNameRecognition.name)
        self.builder.add_edge(NodeItemNameRecognition.name, NodeBGEEmbedding.name) # 接上向量化
        self.builder.add_edge(NodeBGEEmbedding.name, NodeImportMilvus.name)        # 接上入库
        self.builder.add_edge(NodeImportMilvus.name, END)                          # 结束

    def run(self, state):
        # 懒加载的方式进行编译
        if self.graph is None:
            # 修复：把 builder 编译成 graph，并修正 compile 拼写
            self.graph = self.builder.compile() 
            
        # 执行
        result = self.graph.invoke(state)
        return result

    @classmethod
    def create_and_run(cls, state):
        return cls().run(state)

if __name__ == "__main__":
    # 初始数据
    init_state = {
        "local_dir":r"C:\Users\Administrator\Desktop\test1",
        "local_file_path": r"C:\Users\Administrator\Desktop\test1\万用表RS-12的使用.pdf"
    }
    result = MainGraphRunner.create_and_run(init_state)