from thinktank.import_process.base import NodeBase
from thinktank.import_process.state import ImportGraphState
from thinktank.tool.logger import logger
from pathlib import Path
import re
from thinktank.tool.json_format import json_format
from langchain_text_splitters import RecursiveCharacterTextSplitter

class NodeDocumentSplit(NodeBase):
    """
    文档内容切分：
    主要涉及的三个大的步骤：
    1、先拿到 md 的文档内容
        (1) 通过state拿到 文档的 md_path 和 file_title
        (2) 判断 md_path 的目录和文件路径是否存在。
        (3) 判断 标题是否为空
        (4) 最后需要读取文件内容并对里面的内容进行一定的替换，
            将 文本中 换行符替换成一致的内容。方便后面使用。
    2、进行粗分
        (1) 先按照 换行符将 整篇文档处理成列表。
        (2) 遍历列表中的每一个内容进行处理，先处理代码围栏的问题，因为代码中存在 #。
            通过状态机 和 检查标志以及正则匹配来完成这些内容。
        (3) 循环拼接，找到 # ，然后将#号之前的内容进行切片处理。得到一个列表。
        (4) 将列表的内容 拼接起来，最后返回一个字典列表数据。
    3、进行细切
        (1) 定义递归列表切分器。
        (2) 循环遍历每个字典中的内容，并将content提取出来。
            2.1 、然后判断 content 的长度和是否存在表格，因为这些内容都不行切分。
            2.2 、使用 递归字符切分器进行切分。并完成字典列表数据的处理。
        (4) 最后 将其添加到最终的字典列表中。
    """

    name = "node_document_split"

    def process(self, state: ImportGraphState):

        # 1、获取测试给的 md 内容集文件标题，内容需要进行换行符统一。
        file_title, md_content = self.get_md_content(state)

        # 2、粗切  根据每行是不是标题来进行粗切，以标题和它所属内容组成大块
        section_list = self.get_section_list(md_content,file_title)

        # 3、细切（长切短合）遍历上面粗切出来的每个大块进行判断长切短合。
        final_chunk_list = self.get_final_chunk_list(section_list,file_title)

        return final_chunk_list

    # 先获取到md 的数据，然后对md 的数据进行处理。
    def get_md_content(self,state):
        file_title = state.get("file_title")
        md_path = state.get("md_path")

        # 防御性编程，先判断文件路径和文件以及文件标题是否存在
        if not md_path:
            logger.info("01 文件路径不能为空")
            raise Exception("文件路径不能为空")

        md_path_obj = Path(md_path)
        if not md_path_obj.exists():
            logger.info("02 文件不能为空")
            raise Exception("文件不能为空")

        if not file_title:
            logger.info("03 标题不能为空")
            raise Exception("标题不能为空")

        with open(md_path_obj,'r',encoding="utf-8") as f:
            md_content = f.read()   # 将内容读出来并准备切分；

        md_content = md_content.replace("\r\n","\n").replace("\r","\n")

        return file_title, md_content

    # 粗切处理
    # 我们切分的思路是将 标题 和内容区分开。标题前面是 有 # 来表示；
    # 存在一个问题是 # 号的内容有可能是 代码块的注释（怎么来判断代码围栏的问题）
    def get_section_list(self,md_content,file_title):
        # 先按行切分，处理成一个列表。列表中的每个元素就是一行内容。
        splite_line_list = md_content.split("\n") # 按行切分获取到行的列表（每行都是一个字符串） 
        is_block = False
        start_index = 0

        # 匹配代码围栏的内容
        code_pattern = r"^(`{3,}|~{3,})"
        title_pattern = r'^\s*#{1,6}\s+.+'
        temp_section_list = []
        
        # 循环遍历每一个内容
        for idx, splite_line in enumerate(splite_line_list):
            # 将列表中元素的内容左右先建空格处理掉
            splite_line = splite_line.strip()  # 前后的空白全被剃得干干净净）
            # 先做 代码围栏 处理
            match = re.match(code_pattern,splite_line)
            if match:
                # 表示是第一次匹配到
                if not is_block:
                    is_block = True  # 替换成 True 表示是第一次匹配到。
                    marker = match.group(1)
                else:
                    if marker == match.group(1):
                        # 代码围栏结束
                        is_block = False
                        marker = None
            # 如果 是 True 并且 这是以 # 号开头（不管有多少个#号）
            if not is_block and re.match(title_pattern,splite_line):
                # # 号才是标题
                temp = splite_line_list[start_index:idx]  # 切完后是一个列表
                start_index = idx  # 这是新切完后的新的位置
                temp_section_list.append(temp)  # 编程二维列表

        # 主要是为了解决最后一步数据的问题，因为我们是找 # 号 切前面的内容
        temp_section_list.append(splite_line_list[start_index:])

        # 将每个列表中的内容拼接起来
        section_list = []
        for temp_section in temp_section_list:
            content = "\n".join(temp_section)
            title = temp_section[0] if content.startswith("#") else "无标题"

            section_list.append({
                "title":title,
                "content":content,
                "file_title":file_title,
            })
        return section_list

    def get_final_chunk_list(self,section_list,file_title):
        # 1.1 准备递归字符切分器
        spliter = RecursiveCharacterTextSplitter(
            separators=["\n\n", "\n", "。", "！", "？", "；", "!", "?", ";", " "],
            chunk_size=300,
            chunk_overlap=50,      # 防止语义切断才会有
            length_function=len,
            add_start_index=True,  
            # 在切分前如果使用加载器，就有 metadata，这个字典里面就会
            # 添加上每个 chunk 在内容当中的起始位置
            # 目前写不写没作用，因为我们没有用到加载器。
        )

        # 1.2、循环取判断每个 content 中的内容是否需要切分。
        #   如果需要切的话，就需要一个特殊的标识去标识，这个字符串被切分成多少个切片。
        final_chunk_list = []
        for section in section_list:
            title = section.get("title")
            content = section.get("content")

            # 获取真实的文本内容
            real_content = content[len(title) + 2 :] if content.startswith("#") else content

            # 长度小于 300的不切
            if len(real_content) <= 300:
                final_chunk_list.append({
                    **section,
                    "part":0
                })
                continue

            # 存在表格的不切
            if "<table" in real_content:
                final_chunk_list.append({
                    **section,
                    "part":0
                })
                continue

            # 这个位置在切分
            for idx, split_text in enumerate(spliter.split_text(real_content),start=1): 
                final_chunk_list.append({
                    "title":title,
                    "content":title + "\n\n" + split_text,
                    "file_title":file_title,
                    "part":idx
                })                

        # # 1.3 保存一份，用于后面节点的测试
        # with open(r"C:\Users\Administrator\Desktop\test1\万用表RS-12的使用\final_spilt_list.json", "w",encoding="utf-8") as f:
        #     f.write(json_format(final_chunk_list))

        # 1.4 返回即可
        return {
            "chunks":final_chunk_list
        }

if __name__ == "__main__":
    node = NodeDocumentSplit()
    init_state = {
        "md_path":r"C:\Users\Administrator\Desktop\test1\万用表RS-12的使用\万用表RS-12的使用_new.md",
        "file_title":"万用表RS-12的使用_new"
    }
    result = node(init_state)
    # print("result=",result)