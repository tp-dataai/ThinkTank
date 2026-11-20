import re
from langchain.chat_models import init_chat_model

from thinktank.config.config import LLMConfig
from thinktank.config.prompt import ANSWER_PROMPT
from thinktank.query_process.base import NodeBase
from thinktank.query_process.state import QueryGraphState
from thinktank.tool.logger import logger
from thinktank.tool.mongo_tool import save_chat_message
from thinktank.tool.task_utils import put_data

class NodeAnswerOutput(NodeBase):
    """
    节点功能: 答案生成（支持流式输出与降级短路）
    具体的步骤：
    (1) 获取需要传输给大模型的所有数据。问题、检索到的相关chunks、MongoDB中的历史数据、url。
    (2) 将这些数据提供给大模型进行流式输出，输出结束后，根据输出的内容中的连接提取图片的内容。
    (3) 将输出的内容存储到MongoDB中。
    """
    name: str = "node_answer_output"

    def process(self, state: QueryGraphState):

        # 获取之前的数据
        answer = state.get("answer")
        task_id = state.get("task_id")
        reranked_docs = state.get("reranked_docs") or [] # 防 None
        history_list = state.get("history") or []
        item_names = state.get("item_names") or []
        rewritten_query = state.get("rewritten_query") or state.get("original_query", "")
        session_id = state.get("session_id")
        message_id = state.get("message_id")

        if answer:
            # 💡 修复 3：短路分支（比如意图反问），也要发送 final 并带上完整 answer
            logger.info(f"[{task_id}] 触发短路回答，直接推送 final")
            put_data(task_id=task_id, event="final", data={"answer": answer, "image_urls": []})
        else:
            # 💡 修复 1：进入大模型生成分支，务必初始化 answer 为空字符串
            answer = ""
            
            # 1. 整理 chunks 内容 context
            context = ""
            for item in reranked_docs:
                chunk_str = f"""
                    标题:{item.get("title", "")}
                    内容:{item.get("content", "")}
                    url:{item.get("url", "")}
                    来源:{item.get("source", "")}
                """
                context += chunk_str.strip() + "\n"

            # 2. 整理 history
            history = ""
            for item in history_list:
                history_str = f"{item.get('role', '')}:{item.get('text', '')}\n"
                history += history_str

            # 3. 整理 item_names 和 question
            item_names_str = ",".join(item_names)
            question = rewritten_query

            # 4. 提示词合并截断
            prompt = ANSWER_PROMPT.format(
                item_names=item_names_str,
                question=question,
                history=history,
                context=context,
            )[:10000]

            messages = [{"role": "user", "content": prompt}]

            llm = init_chat_model(
                model=LLMConfig.llm_default_model,
                model_provider="openai",
                api_key=LLMConfig.openai_api_key,
                base_url=LLMConfig.openai_api_base,
                temperature=LLMConfig.llm_default_temperature
            )

            # 5. 大模型流式输出
            res = llm.stream(messages)
            for item in res:
                chunk_content = item.content
                # 💡 修复 2：过滤掉空块，防止前端渲染卡顿
                if chunk_content:
                    put_data(task_id=task_id, event="delta", data={"delta": chunk_content})
                    answer += chunk_content

            # 6. 提取图片
            seen = set()
            md_img_pattern = re.compile(r'!\[.*?\]\((.*?)\)')
            for doc in reranked_docs:
                text = doc.get("content", "")
                matches = md_img_pattern.findall(text)
                for img_url in matches:
                    img_url = img_url.strip()
                    seen.add(img_url)
            image_list = list(seen)

            # 💡 修复 2：发送 final 时，必须把完整的 answer 和图片一起发给前端！
            put_data(task_id=task_id, event="final", data={"answer": answer, "image_urls": image_list})


        # 💡 修复 3：把保存历史记录移到最外层，保证无论走哪个分支都能保存
        if answer:
            message_id = save_chat_message(
                session_id=session_id,
                role="assistant",
                text=answer,
                rewritten_query=rewritten_query,
                item_names=item_names,
            )

        return {
            "message_id": message_id,
        }