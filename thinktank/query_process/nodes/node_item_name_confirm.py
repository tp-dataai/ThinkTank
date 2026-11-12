import json

from thinktank.tool.json_format import json_format
from thinktank.query_process.base import NodeBase
from thinktank.query_process.state import QueryGraphState
from thinktank.tool.logger import logger
from thinktank.tool.mongo_tool import get_recent_message
from thinktank.tool.tool_llm_init import get_llm_init
from thinktank.config.prompt import ITEM_NAME_EXTRACT_SYSTEM_PROMPT, ITEM_NAME_EXTRACT_TEMPLATE
from thinktank.tool.bgem3_embedding_tool import get_bgem3_embeddings
from thinktank.tool.tool_milvus_client import get_req_list, hybrid_search
from thinktank.config.config import MilvusConfig
from thinktank.tool.mongo_tool import save_chat_message,update_history_item_names

class NodeItemNameConfirm(NodeBase):
    """
    节点功能：确认用户问题中的核心商品名称。
    这只是和 Milvus 中的 item_name 进行相似度匹配。
    这个功能是否应该是这样的，在实际的业务场景中。意图识别的在不同业务场景中，有哪些考量？
    """

    # 覆盖基类的 name 属性，标识节点名称
    name: str = "node_item_name_confirm"

    def process(self, state: QueryGraphState):
        """
        节点逻辑
        :param state: 工作流状态对象
        :return: 更新后的状态对象
        """

        # 1、获取到原始的问题 和 session_id，并根据 session_id 得到所有的历史数据，
        #   在将历史数据中的每轮对话的 role 和 text 内容，进行拼接成字符串。
        # self.get_history_str(state)
        session_id, original_query, history_list_str = self.get_history_str(state)

        # 2、根据历史记录大串和原始问题让 llm 识别商品名字得到识别的商品名字
        # self.get_recognition_item_names(original_query,history_list_str)
        item_names, rewritten_query = self.get_recognition_item_names(original_query,history_list_str)

        # 3、下面就是要根据识别的名称 和 milvus存储的名称进行混合检索相似度，
        # 在这必须要封装milvus混合检索工具
        final_item_names = []
        answer = "不好意思，没有识别到您的问的商品，请重新提问。"

        if item_names:
            # 识别到再去做混合检索（最终拿到 milvus 表当中的名字） 和名称对齐。
            search_item_names = self.hybrid_item_names(item_names)

            # 检索到的 milvus 表当中的所有名字进行名称对齐
            answer, final_item_names = self.aligin_item_names(answer,final_item_names,search_item_names)


        # # 5、善后处理，把新家的历史记录添加好，把所有参与这些识别的历史记录全部回填最终的item_names 和重写问题。
        # self.handler_history(answer,final_item_names,rewritten_query,session_id)

        # return {
        #     "original_query":original_query,
        #     "answer":answer,
        #     "item_names":item_names,
        #     "rewritten_query":rewritten_query,
        #     "history":get_recent_message(session_id),
        #     "session_id":session_id,
        # }
    
    def get_history_str(self,state:QueryGraphState):
        # 获得 session_id 和 original_query 并完成防御性处理
        session_id = state.get("session_id")
        original_query = state.get("original_query")

        # 这个 session_id 一定会有，是前端传入的数据
        if not session_id:
            logger.error("session_id 不能为空")

        if not original_query:
            logger.error("问题不能为空")

        # 通过 session_id 去查找历史记录，如果存在就返回历史记录
        # 注意：记录可能存在多条数据。
        history_list = get_recent_message(session_id)

        # 获得历史的数据以后，要不要将这次的内容保存到历史记录中。
        # 现在还没有一个准确的回复。
        # print(json_format(history_list))
        message_id = save_chat_message(session_id=session_id, role="user",text=original_query)
        # print(message_id)

        history_list_str = ""
        # 将其拼接成 字符串
        for history_list_item in history_list:
            # LLM 需要根据每轮对话的内容来进行内容的提取和处理。
            # \n\n 对话的内容需要进行换行处理，每行是一个完整的内容
            history_str = f"{history_list_item.get("role")}:{history_list_item.get("text")}\n\n"
            history_list_str += history_str
        # print("history_list_str=",history_list_str)
        return session_id, original_query, history_list_str

    # 通过大模型来完成 问题改写 和 商品名称的识别。
    def get_recognition_item_names(self,original_query,history_list_str):
        # 初始化 llm。
        llm = get_llm_init()

        # 处理提示词的内容：
        messages = [
            {"role": "system", "content": ITEM_NAME_EXTRACT_SYSTEM_PROMPT},
            {"role": "user", "content": ITEM_NAME_EXTRACT_TEMPLATE.format(
                history_text=history_list_str,
                original_query=original_query,
            )},
        ]

        # 通过 llm 得到大模型返回的数据。
        # 大模型主要返回两个内容：item_names 和  rewritten_query
        res = llm.invoke(input=messages)

        res_json = res.content
        # 返回的内容中有可能存在 json 串，所以需要先对这些内容进行处理，将其替换。
        res_json = res_json.replace("```json","").replace("```","")
        # print("未序列化之前的数据类型：",type(res_json))
        # json.loads()将 JSON 格式的“字符串（String）”解析（反序列化）成 Python 的“字典（dict）”或“列表（list）”。
        res_data = json.loads(res_json)
        # print("序列化之前的数据类型：",type(res_json))
        # 这是大模型识别出来的 商品名称的列表，识别出来的结果可能存在多个数据。
        item_names = res_data.get("item_names",[]) # 如果没有返回值，就默认为空。

        # 识别出来的名称中可能还存在 空格，所以还需要进行一定的处理。
        # 每个元素单独，最后还是列表的形式。
        item_names = [ item.replace("\n","").replace("\t","").replace(" ","") for item in item_names ]

        # 得到重写后的内容：
        rewritten_query = res_data.get("rewritten_query",original_query)

        return item_names, rewritten_query

    # t通过混合检索得到了一个字典列表，这个字典列表中记录的是 我们的返回的所有内容中的得分情况。
    def hybrid_item_names(self, item_names):
        search_item_names = []
        # 先拿到 item_names 的稠密向量和混合向量
        item_names_vector = get_bgem3_embeddings(item_names)

        # 识别出来的 item_names 存在多个 商品名称，因此在这个地方完成 遍历循环。
        for idx, item_name in enumerate(item_names):
            # dense = item_names_vector["dense"][idx]
            # sparse = item_names_vector["sparse"][idx]

            # 注意：如果get返回的结果是 None ，那后面的[idx]就会导致直接报错。
            dense = item_names_vector.get("dense", [])[idx]
            sparse = item_names_vector.get("sparse", [])[idx]

            # 开始混合检索
            reqs = get_req_list(
                dense_data=dense,
                sparse_data=sparse,
                dense_anns_field="dense_vector",
                sparse_anns_field="sparse_vector",
            )

            res = hybrid_search(
                collection_name=MilvusConfig.item_name_collection,
                reqs=reqs,
                output_fields=["item_name", "file_title"],
                ranker=(0.7, 0.3),
            )

            print("res=",res)
            if not res:
                continue

            for search_item_name_dict in res[0]:
                search_item_names.append({
                    "score":search_item_name_dict.get("distance"),
                    "search_item_name":search_item_name_dict.get("entity").get("item_name"),  # type:ignore
                    "orginal_item_name":item_name,
                })
        return search_item_names

    # 命名对齐（内容归类：无非就是将我们查询返回和查询到的内容按照一个的条件进行分组归类）
    """
    智能路由：意图识别，智能分发。
    “在 RAG 的 查询路由 前置节点中，设计了一套基于置信度阈值的实体链接与消歧机制(Entity Linking and Disambiguation)。
    通过引入 高/中/低三级置信度切分：
        (1) 高分段(≥0.8)直接进行实体对齐并透传；
        (2) 中分段(0.6-0.8)触发澄清式追问(Clarifying Question)，引导用户明确意图；
        (3) 低分段(<0.6)触发兜底拒识(Fallback)。
    这套机制大幅降低了由于用户产品名输入模糊导致的后续检索幻觉。”
    """
    def aligin_item_names(self,answer,final_item_names,search_item_names):
        confirm_item_names = [ item.get("search_item_name") for item in search_item_names if item.get("score") >= 0.8]
        option_item_names = [ item.get("search_item_name") for item in search_item_names if item.get("score") > 0.6 and item.get("score") < 0.8]

        # 如果确认用户问的名字，那么没有答案
        if confirm_item_names:
            answer = ""
            final_item_names = confirm_item_names
        elif option_item_names:
            answer = f"请问您要咨询的商品名字是哪一个：{','.join(option_item_names)}"
            final_item_names = []
        else:
            answer = "不好意思，没有识别到您问的商品，请重新提问"
            final_item_names = []
        return answer, final_item_names

    def handler_history(self,answer,final_item_names,rewritten_query,session_id):
        # 善后处理，其实就是对历史记录进行处理
        if answer:
            message_id = save_chat_message(session_id,"assistant",answer)

        # 不管有没有新记录，都要把识别到的最终确认的 final_item_name 和重写的问题，回填给历史记录
        history_list = get_recent_message(session_id)
        ids = [item.get("_id") for item in history_list]
        if ids:
            update_history_item_names(ids,item_names=final_item_names, rewritten_query=rewritten_query)


if __name__ == "__main__":

    # 创建节点对象
    node = NodeItemNameConfirm()

    # 初始化图状态
    init_state = {
        "session_id": "test_001",
        "original_query": "万用表咋用？"
    }

    # 执行节点的单元测试
    result = node(init_state)  # type: ignore

    # 将返回的图状态进行json序列化
    logger.info(json_format(result))