import json

from thinktank.query_process.base import NodeBase
from thinktank.query_process.state import QueryGraphState
from thinktank.tool.logger import logger
from thinktank.tool.tool_llm_init import get_llm_init
from thinktank.config.prompt import HYDE_PROMPT
from thinktank.tool.bgem3_embedding_tool import get_bgem3_embeddings
from thinktank.tool.tool_milvus_client import get_req_list,hybrid_search
from thinktank.config.config import MilvusConfig
from thinktank.tool.json_format import json_format

class NodeSearchEmbeddingHyde(NodeBase):
    """
    节点功能：HyDE (Hypothetical Document Embedding)
    先让 LLM 生成假设性答案，再对答案进行向量检索，提高召回率。
    """

    # 覆盖基类的 name 属性，标识节点名称
    name: str = "node_search_embedding_hyde"

    def process(self, state: QueryGraphState):
        """
        节点逻辑
        :param state: 工作流状态对象
        :return: 更新后的状态对象
        """
        # 先获得 LLM 重新生成的 问题，和 item_names 的内容
        rewritten_query = state.get("rewritten_query")
        item_names = state.get("item_names")

        # 初始化大模型
        llm = get_llm_init()

        message = [
            {"role":"user","content":HYDE_PROMPT.format(rewritten_query=rewritten_query)}
        ]

        res = llm.invoke(input=message)
        hyde_answer = res.content

        # 将 重写问题 和 假设答案拼接到一起作为新的问题，开始检索。
        query = rewritten_query + "\n" + hyde_answer


        # 对重写的问题进行向量化
        embeddings = get_bgem3_embeddings([query])
        dense = embeddings.get("dense","")[0]
        sparse = embeddings.get("sparse","")[0]
        # filter_item_names = [
        #     item.replace("\\","\\\\").replace("\'","\\'").replace('\"','\\"')
        #     for item in item_names
        # ]
        expr = f"item_name in {json.dumps(item_names)}"

        # 混合检索相似度高的chunks
        reqs = get_req_list(
            dense_data=dense,
            sparse_data=sparse,
            dense_anns_field="dense_vector",
            sparse_anns_field="sparse_vector",
            expr=expr
        )

        res = hybrid_search(
            collection_name=MilvusConfig.chunks_collection,
            reqs=reqs,
            output_fields=["id", "item_name", "file_title", "content", "title"],
            ranker=(0.7, 0.3)
        )
        # print(json_format(res))

        # 把混合检索到的chunks整理成自己需要的
        chunks = [
            {
                **item.get("entity",{}),
                "score": item.get("distance"),
                "source": "local"
            }
            for item in res[0]
        ]

        return {
            "hyde_embedding_chunks": chunks
        }

if __name__ == "__main__":
    init_state = {
        "rewritten_query": "关于RSPRORS-12数字万用表如何使用",
        "item_names": ["RSPRORS-12数字万用表"]
    }
    node_search_embedding_hyde = NodeSearchEmbeddingHyde()
    result = node_search_embedding_hyde(init_state)  # type:ignore
    logger.info(json_format(result))