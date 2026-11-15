import json

from thinktank.query_process.base import NodeBase
from thinktank.query_process.state import QueryGraphState
from thinktank.tool.logger import logger
from thinktank.tool.bgem3_embedding_tool import get_bgem3_embeddings
from thinktank.tool.tool_milvus_client import get_req_list, hybrid_search
from thinktank.config.config import MilvusConfig
from thinktank.tool.json_format import json_format

class NodeSearchEmbedding(NodeBase):
     """
    节点功能：基于已确认主体名+改写后的用户问题，执行Milvus向量数据库混合检索
    """

     # 覆盖基类的 name 属性，标识节点名称
     name: str = "node_search_embedding"

     def process(self, state: QueryGraphState):
         """
         节点逻辑
         :param state: 工作流状态对象
         :return: 更新后的状态对象
         """

         # 先拿到我们改写后的问题和检索出来的 item_names 
         rewritten_query = state.get("rewritten_query")  # 大模型重写后的问题。
         item_names = state.get("item_names")            # 主要是为了检索的时候过滤。

         # 对重写的问题进行向量化,并提取出稠密向量和稀疏向量
         embeddings = get_bgem3_embeddings([rewritten_query])
         dense = embeddings.get("dense","")[0]
         sparse = embeddings.get("sparse","")[0]

         # 用于过滤数据，减少检索数据 
         expr = f"item_name in {json.dumps(item_names)}"

         # 混合检索相似度高的 chunks
         reqs = get_req_list(
              dense_data=dense,
              sparse_data=sparse,
              dense_anns_field="dense_vector",
              sparse_anns_field="sparse_vector",
              expr=expr,
         )

         res = hybrid_search(
              collection_name=MilvusConfig.chunks_collection,
              reqs=reqs,
              output_fields=["id", "item_name", "file_title", "content", "title"],
              ranker=(0.6, 0.4)
         )

         # 把混合检索的chunks 整理成自己需要的
         chunks = [
              {
                   **item.get("entity",{}),  # ** 解包过程中不能对None进行，必须是一个字典对象
                   "score":item.get("distance"),
                   "source":"local",
              }
              for item in res[0]
         ]

         return {
              "embedding_chunks":chunks
         }

if __name__ == "__main__":
    init_state = {
        "rewritten_query": "关于RSPRORS-12数字万用表如何使用",
        "item_names": ["RSPRORS-12数字万用表"]
    }
    node_search_embedding = NodeSearchEmbedding()
    result = node_search_embedding(init_state)   # type: ignore
    logger.info(json_format(result))