# thinktank/import_process/nodes/node_test.py

import json
from thinktank.import_process.base import NodeBase
from thinktank.import_process.state import ImportGraphState
from thinktank.tool.logger import logger

class NodeTest(NodeBase):
    """
    节点功能：测试
    """

    # 覆盖基类的 name 属性，标识节点名称
    name: str = "node_test"

    def process(self, state: ImportGraphState) -> ImportGraphState:

        logger.info(f"【{self.name}】节点逻辑")

        return state

if __name__ == "__main__":

    # 初始化图状态
    init_state = {"local_file_path":r"C:\Users\Administrator\Desktop\test1\万用表RS-12的使用.pdf"}

    # 创建节点对象
    node_test = NodeTest()
    # 执行节点的单元测试
    result = node_test(init_state)
    # 将返回的图状态进行json序列化
    json_state = json.dumps(result, ensure_ascii=False, indent=4)
    # 输出
    logger.info(json_state)