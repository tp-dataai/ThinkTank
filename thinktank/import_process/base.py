import time
from abc import ABC,abstractmethod

from thinktank.import_process.state import ImportGraphState
from thinktank.tool.logger import logger
from thinktank.tool.task_utils import add_running_task, add_done_task, add_node_duration

class NodeBase(ABC):

    name = "node_base"

    def __init__(self):
        if self.name == "node_base":
            logger.error(f"子类{self.__class__.__name__}必须配置name属性")
            raise Exception(f"子类{self.__class__.__name__}必须配置name属性")

    def __call__(self, state):
        try:
            #统一处理异常
            #统一打印日志
            start_time = time.time()

            task_id = state.get("task_id")
            add_running_task(task_id,self.name) # 修改节点开始执行状态
            logger.info(f"节点{self.name}开始执行")

            result = self.process(state)

            logger.info(f"节点{self.name}执行结束")
            add_done_task(task_id,self.name)#修改节点结束执行状态
            end_time = time.time()

            add_node_duration(task_id,self.name,end_time-start_time) #设置节点执行的耗时

            return result
        except Exception as e:
            logger.error(f"节点{self.name}运行有误")
            raise e
    
    # 抽象方法必须存在关键字
    @abstractmethod
    def process(self, state):
        pass