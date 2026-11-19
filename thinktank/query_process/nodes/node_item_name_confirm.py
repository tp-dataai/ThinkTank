# atguigu/query_process/nodes/node_item_name_confirm.py

import json

from langchain.chat_models import init_chat_model
# from sympy.physics.units import temperature

from thinktank.config.config import LLMConfig, MilvusConfig
from thinktank.config.prompt import ITEM_NAME_EXTRACT_SYSTEM_PROMPT, ITEM_NAME_EXTRACT_TEMPLATE
from thinktank.query_process.base import NodeBase
from thinktank.query_process.state import QueryGraphState
from thinktank.tool.bgem3_embedding_tool import get_bgem3_embeddings
from thinktank.tool.json_format import json_format
from thinktank.tool.logger import logger
from thinktank.tool.tool_milvus_client import get_req_list, hybrid_search
from thinktank.tool.mongo_tool import save_chat_message, get_recent_message, update_history_item_names


class NodeItemNameConfirm(NodeBase):
    """
    节点功能：确认用户问题中的核心商品名称。
    """

    # 覆盖基类的 name 属性，标识节点名称
    name: str = "node_item_name_confirm"

    def process(self, state: QueryGraphState):

        #todo 一、获取原始问题和session_id，根据session_id得到历史记录列表，把历史记录列表转化为大串
        history_list_str, original_query, session_id,message_id = self.get_history_str(state)
        #todo 二、根据历史记录大串和原始问题让llm识别商品名字得到识别的商品名字
        item_names, rewritten_query = self.get_recognition_item_names(history_list_str, original_query)

        final_item_names = []
        answer = "不好意思，没有识别到您问的商品，请重新提问"
        #下面就是要根据识别的名称 和 milvus存储的名称进行混合检索相似度，在这必须要封装milvus混合检索工具
        if item_names:
            #todo 三、如果有识别的商品名字再去做混合检索（最终拿到milvus表当中的名字）和名称对齐
            search_item_names = self.hybrid_search_item_names(item_names)
            #todo 四、检索到的milvus表当中的所有名字进行名称对齐
            answer, final_item_names = self.aligin_item_names(answer, final_item_names, search_item_names)

        #todo 五、善后处理，把新加的历史记录添加好，把所有参与这次识别的历史记录和新记录全部回填最终的item_names和重写的问题
        message_id = self.handler_history(answer, final_item_names, rewritten_query, session_id,message_id)

        return {
            "original_query": original_query,
            "answer":answer,
            "item_names":final_item_names,
            "rewritten_query":rewritten_query,
            "history":get_recent_message(session_id), #一定要最终重新从mongo获取一次最近修改后的历史记录
            "session_id":session_id,
            "message_id":message_id
        }

    def handler_history(self, answer: str, final_item_names, rewritten_query, session_id: str,message_id: str):
        # 善后处理，其实就是对历史记录进行处理
        if answer:
            message_id = save_chat_message(session_id, "assistant", answer)
        
        # 不管有没有新记录，都要把识别到的最终确认的的final_item_names和重写的问题，回填给历史记录
        history_list = get_recent_message(session_id)
        ids = [item.get("_id") for item in history_list]
        if ids:
            update_history_item_names(ids, item_names=final_item_names, rewritten_query=rewritten_query)
        return message_id
    def aligin_item_names(self, answer: str, final_item_names, search_item_names):
        # 开始名称对齐
        confirm_item_names = [item.get("search_item_name") for item in search_item_names if item.get("score") >= 0.8]
        option_item_names = [
            item.get("search_item_name")
            for item in search_item_names
            if item.get("score") < 0.8 and item.get("score") >= 0.6
        ]
        # 如果确认有用户问的名字，那么没有答案
        if confirm_item_names:
            answer = ""
            final_item_names = confirm_item_names
        elif option_item_names:
            answer = f"请问您要咨询的商品名字是哪一个：{','.join(option_item_names)}"
            final_item_names = []
        else:
            final_item_names = []
            answer = "不好意思，没有识别到您问的商品，请重新提问"
        return answer, final_item_names

    def hybrid_search_item_names(self, item_names):
        search_item_names = []
        embeddings = get_bgem3_embeddings(item_names)
        for idx, item_name in enumerate(item_names):
            # 拿一个识别的名字，向量化，从milvus当中主题名表里面进行混合检索，检索出来也可能是多个
            dense = embeddings.get("dense","")[idx]
            sparse = embeddings.get("sparse","")[idx]

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
                ranker=(0.7, 0.3)
            )
            if not res:
                continue
            for search_item_name_dict in res[0]:
                search_item_names.append({
                    "score": search_item_name_dict.get("distance"),  # 分数
                    "search_item_name": search_item_name_dict.get("entity","").get("item_name"),  # 表中找的名字
                    "orginal_item_name": item_name
                })
        return search_item_names

    def get_recognition_item_names(self, history_list_str: str, original_query: str):
        # 初始化大模型对象，整理提示词，让大模型识别商品名称
        llm = init_chat_model(
            model_provider="openai",
            model=LLMConfig.llm_default_model,
            api_key=LLMConfig.openai_api_key,
            base_url=LLMConfig.openai_api_base,
            temperature=LLMConfig.llm_default_temperature
        )

        # 整理提示词
        messages = [
            {"role": "system", "content": ITEM_NAME_EXTRACT_SYSTEM_PROMPT},
            {"role": "user", "content": ITEM_NAME_EXTRACT_TEMPLATE.format(
                history_text=history_list_str,
                original_query=original_query
            )},
        ]

        res = llm.invoke(input=messages)
        # print(res.content,type(res.content))
        res_json = res.content
        # 防止大模型把json理解为json的代码块
        res_json = res_json.replace("```json", "").replace("```", "")
        res_data = json.loads(res_json)
        item_names = res_data.get("item_names", [])
        # 防止名称当中出现空格
        item_names = [
            item.replace("\n", "").replace("\t", "").replace(" ", "")
            for item in item_names
        ]
        rewritten_query = res_data.get("rewritten_query", original_query)
        print(item_names)
        return item_names, rewritten_query

    def get_history_str(self, state: QueryGraphState):
        original_query = state.get("original_query")
        session_id = state.get("session_id")
        if not original_query:
            logger.error("原始问题不能为空")
            raise Exception("原始问题不能为空")
        if not session_id:
            logger.error("会话id不能为空")
            raise Exception("会话不能为空")

        # 现在这个问题，就得变成一个记录，那么我们先去获取历史记录，然后再把当前问题保存历史记录
        history_list = get_recent_message(session_id)
        message_id = save_chat_message(session_id, role="user", text=original_query)

        # 把历史记录字典列表变成一个大串
        history_list_str = ""
        for history_item in history_list:
            history_str = f"{history_item.get("role")}:{history_item.get("text")}\n\n"
            history_list_str += history_str
        return history_list_str, original_query, session_id, message_id


if __name__ == "__main__":

    # 模拟会话历史
    # session_id = "test_001"
    # save_chat_message(session_id, "user", "咨询下万用表。")
    # save_chat_message(session_id, "assistant", "您好。请问是哪个型号")
    # save_chat_message(session_id, "user", "RS-12")
    # save_chat_message(session_id, "assistant", "具体有什么问题呢？")

    # 初始化图状态
    init_state = {
        "session_id": "test_001",
        "original_query": "咋用？"
    }

    # # 创建节点对象
    # node_item_name_confirm = NodeItemNameConfirm()
    # # 执行节点的单元测试
    # result = node_item_name_confirm(init_state)
    # # 将返回的图状态进行json序列化
    # logger.info(json_format(result))