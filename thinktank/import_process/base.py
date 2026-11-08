from abc import ABC, abstractmethod
from thinktank.tool.logger import logger

class NodeBase(ABC):

    name = "node_base"

    def __init__(self):
        if self.name == "node_base":
            logger.error(f"子类{self.__class__.__name__}必须配置name属性")
            raise Exception(f"子类{self.__class__.__name__}必须配置name属性")

    def __call__(self, state):
        try:
            logger.info(f"节点[{self.name}]开始处理")
            result = self.process(state)
            logger.info(f"节点[{self.name}]处理完成")
            return result
        except Exception as e:
            logger.error(f"节点[{self.name}]处理失败: {e}")
            raise e
    
    # 抽象方法必须存在关键字
    @abstractmethod
    def process(self, state):
        pass