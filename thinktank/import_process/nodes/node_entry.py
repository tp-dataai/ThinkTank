from pathlib import Path

from thinktank.import_process.base import NodeBase
from thinktank.import_process.state import ImportGraphState
from thinktank.tool.logger import logger

class NodeEntry(NodeBase):
    """
    入口：通过判断输入的文件内容来路由到不同的节点进行处理
    主要实现三大步：
        (1) 数据校验：先判断上传的数据是否存在问题，包括路径是否存在 和 文件是否为空。
        (2) 信息提取：根据上传的文件路径获得 文件目录、文件标题以及文件类型（后缀）。
        (3) 路由分发：根据文件的类型分发不同的节点进行处理。
    """

    name = "node_entry"

    def process(self, state: ImportGraphState):

        # 1、先获取本地文件的文件路径
        local_file_path = state.get("local_file_path")

        # 2、防御性编程，合适文件的目录是否为空 和文件是否存在。
        if not local_file_path:
            logger.error("上传文件的目录不能为空")
            raise Exception("上传文件的目录不能为空")

        # 是一个完整的文件路径，不是文件目录。
        # C:\Users\Administrator\Desktop\test2\万用表RS-12的使用.pdf
        local_file_path_obj = Path(local_file_path)  

        # print("local_file_path_obj",local_file_path_obj)

        if not local_file_path_obj.exists():
            logger.error("上传文件不能不存在")
            raise Exception("上传文件不能不存在")
        
        # 3、文件存在的情况下，将文件的 路径 和 后缀提取出来

        file_name = local_file_path_obj.name              # 这是文件的标题和类型
        file_title = local_file_path_obj.stem             # 这是文件的标题
        file_suffix = local_file_path_obj.suffix.lower()  # 得到文件的后缀

        # print("file_name: ",file_name)
        # print("file_title: ",file_title)
        # print("file_suffix: ",file_suffix)

        # 4、基于提取的 文件 后缀来进行判断。并返回不同的值
        #    返回的值 有 file_title、流程控制标记、以及 md_path(放在本地路径中)
        # 如果需要处理多模态的数据，是否需要在这个位置来处理？？
        if file_suffix == ".pdf":
            # 得到想要的结果
            result = {
                "file_title":file_title,
                "is_pdf_read_enabled":True,
                "pdf_path":local_file_path
            }
            return result
        elif file_suffix == ".md":
            # 得到想要的结果
            result = {
                "file_title":file_title,
                "is_md_read_enabled":True,
                "md_path":local_file_path
            }
            return result
        else:
            logger.error("还不支持该类型文件的处理")
            raise Exception(f"还不支持该类型文件的处理")

if __name__ == "__main__":
   # 实例化节点
   node_entry = NodeEntry()

   # 初始数据
   init_state = {
       "local_dir":r"C:\Users\Administrator\Desktop\test2",
       "local_file_path":r"C:\Users\Administrator\Desktop\test2\万用表RS-12的使用.pdf"
   }

   result = node_entry(init_state)