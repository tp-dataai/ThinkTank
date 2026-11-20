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
     (1) 获取查询上下文: 从状态(state) 中提取经过改写的问题(rewritten_query) 以及在
                      上一节点确认的商品名称列表(item_names) 。
     (2) 文本向量化
          调用嵌入模型接口，将改写后的问题转换为向量表示。这里同时生成两种向量：
          - 稠密向量 (Dense Vector) ：用于捕捉语义相似度。
          - 稀疏向量 (Sparse Vector) ：用于捕捉关键词匹配。
     (3) 构建混合检索请求
          - 准备 Milvus 混合搜索参数：
          - 过滤条件：如果有确定的商品名，构造 item_name in [...] 过滤器，限定搜索范围。
          - 检索策略：结合稠密向量和稀疏向量进行多路召回。
     (4) 执行向量检索
          - 连接 Milvus 数据库的 CHUNKS_COLLECTION 集合，执行混合检索。
          - 加权融合：根据权重对稠密和稀疏得分进行重排序(Rerank) 。
          - 结果截取：返回 Top 5 最相关的文档切片(Chunks) 。
     (5) 更新状态: 将检索到的文档切片列表(embedding_chunks) 存入状态,供后续节点使用。
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
        "rewritten_query": "小学生每天合适的睡眠时长是多少？",
        "item_names": ["不同年龄段睡眠与屏幕时间参考","孩子入睡困难与作息混乱怎么调整","儿童性格心理学"]
    }
    node_search_embedding = NodeSearchEmbedding()
    result = node_search_embedding(init_state)   # type: ignore
    logger.info(json_format(result))