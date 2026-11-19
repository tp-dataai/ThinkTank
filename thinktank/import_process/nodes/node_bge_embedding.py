import json

from thinktank.import_process.base import NodeBase
from thinktank.import_process.state import ImportGraphState
from thinktank.tool.logger import logger
from thinktank.tool.bgem3_embedding_tool import get_bgem3_embeddings
from thinktank.tool.json_format import json_format

class NodeBGEEmbedding(NodeBase):
    """
    混合向量化节点：使用 BGE-M3 模型将文本转换为向量。
    向量化的步骤：
    (1) 获取数据: 获取到需要进行向量化处理的数据, 也就是我们之前处理好的Chunk内容。
    (2) 批次处理: 按照3个一批的数据, 输入到大模型中进行向量化处理。
    (3) 数据回填: 将模型返回的 稠密向量和稀疏向量，回填到原始Chunk 中。
       -> 2和3, 通过两个for循环来完成处理。
    """

    name = "node_bge_embedding"

    def process(self, state: ImportGraphState):
        # 1、先判断 chunks 中的内容是否存在
        chunks = state.get("chunks")

        if not chunks:
            logger.error("chunks 的内容不能为空")
            raise Exception("chunks 的内容不能为空")

        # 进行已处理，将数据进行嵌入向量，并返回到我们的 chunks 中，用于后续 写入到 Milvus 中
        # 3 个为一批 --> 按批进行向量化处理
        for i in range(0,len(chunks),3):
            # 这是将里字典列表中的数据每个拿3个出来
            chunks_k_list = chunks[i : i + 3]

            # 先将这个字典列表的数据进行拼接后再处理。
            # item_name 是我们通过主体识别和标签构建出来的内容。
            chunks_k_list_str = [f"{item.get("item_name")}{item.get("content")}" for item in chunks_k_list]
            embedding = get_bgem3_embeddings(chunks_k_list_str)

            for idx,chunk in enumerate(chunks_k_list):
                chunk["dense_vector"] = embedding["dense"][idx]
                chunk["sparse_vector"] = embedding["sparse"][idx]

        # with open(r"C:\Users\Administrator\Desktop\test2\万用表RS-12的使用\final_spilt_list_item_name_cunks_vector.json","w",encoding="utf-8") as f:
        #     json.dump(chunks,f,ensure_ascii=False,indent=4)

        return {
            "chunks":chunks,
        }

if __name__ == "__main__":

    node = NodeBGEEmbedding()

    with open(r"C:\Users\Administrator\Desktop\test2\万用表RS-12的使用\final_spilt_list_item_name.json","r",encoding="utf-8") as f:
        chunks = json.load(f)

    init_state = {
        "chunks":chunks
    }
    
    result = node(init_state)
    # print("result=", json_format(result))
