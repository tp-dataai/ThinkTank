from pathlib import Path

from thinktank.import_process.base import NodeBase
from thinktank.import_process.state import ImportGraphState
from thinktank.tool.logger import logger

class NodeEntry(NodeBase):
    """
    入口：通过判断输入的文件内容来路由到不同的节点进行处理
    """

    name = "node_entry"

    def process(self, state: ImportGraphState):
        # 1、先获取本地文件的文件路径
        local_file_path = state.get("local_file_path")

        # 2、防御性编程，合适文件的目录是否为空 和文件是否存在。
        if not local_file_path:
            logger.error("上传文件的目录不能为空")
            raise Exception("上传文件的目录不能为空")

        local_file_path_obj = Path(local_file_path)

        if not local_file_path_obj.exists:
            logger.error("上传文件不能不存在")
            raise Exception("上传文件不能不存在")
        
        # 3、文件存在的情况下，将文件的 路径 和 后缀提取出来

        file_name = local_file_path_obj.name
        file_title = local_file_path_obj.stem
        file_suffix = local_file_path_obj.suffix  # 得到文件的后缀

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
       "local_dir":r"C:\Users\Administrator\Desktop\test1",
       "local_file_path":r"C:\Users\Administrator\Desktop\test1\hak180产品安全手册.pdf"
   }
   result = node_entry(init_state)