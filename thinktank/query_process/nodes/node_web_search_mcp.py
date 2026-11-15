import json
from agents import Agent, Runner
from agents.mcp import MCPServerStreamableHttp
from agents.model_settings import ModelSettings
import asyncio

from thinktank.query_process.base import NodeBase
from thinktank.query_process.state import QueryGraphState
from thinktank.tool.logger import logger
from thinktank.config.config import MCPConfig
from thinktank.tool.json_format import json_format

class NodeWebSearchMcp(NodeBase):
    """
    节点功能，调用外部搜索引擎补充信息
    """

    # 覆盖基类的 name 属性，标识节点名称
    name: str = "node_web_search_mcp"

    def process(self, state: QueryGraphState):
        """
        节点逻辑
        :param state: 工作流状态对象
        :return: 更新后的状态对象
        """

        # 先获取 大模型 重写后的问题。
        rewritten_query = state.get("rewritten_query")
        result = asyncio.run(self.run_mcp(rewritten_query))

        assert result is not None, "MCP 服务返回了 None"

        data = json.loads(result.content[0].text).get("pages")
        chunks = [
            {
                "content":item.get("snippet"),
                "title":item.get("title"),
                "url":item.get("url"),
                "source":"web"
            }
            for item in data
        ]


        return {
            "web_search_doce":chunks
        }

    async def run_mcp(self,query,limit=10) -> None:
        token = MCPConfig.mcp_dashscope_api_key
        async with MCPServerStreamableHttp(
                name="网络搜索chunks的mcp工具",
                params={
                    "url": str(MCPConfig.mcp_dashscope_base_url),
                    "headers": {"Authorization": f"Bearer {token}"},
                    "timeout": 10,
                },
                cache_tools_list=True,
                max_retry_attempts=3,
        ) as server:
            result = await server.call_tool(
                tool_name="bailian_web_search",
                arguments={
                    "query":query,
                    "count":limit
                }
            )
            return result # type: ignore

if __name__ == "__main__":

    init_state = {
        "rewritten_query": "关于BrotherHAK180烫金机如何使用"
    }

    # 执行节点的业务调用
    node_web_search_mcp = NodeWebSearchMcp()
    result = node_web_search_mcp(init_state)  # type:ignore
    logger.info(json_format(result))