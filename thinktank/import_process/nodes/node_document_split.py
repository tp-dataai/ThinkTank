from thinktank.import_process.base import NodeBase
from thinktank.import_process.state import ImportGraphState
from thinktank.tool.logger import logger
from pathlib import Path
import re
from thinktank.tool.json_format import json_format
from langchain_text_splitters import RecursiveCharacterTextSplitter

class NodeDocumentSplit(NodeBase):
    """
    文档内容切分：将长文档转换为适合向量检索的微观语义单元(Chunk)。采用“先按标题切分，再按长度优化”的策略。
    主要涉及的三个大的步骤：
    (1) 数据获取: 从上一个节点拿到 md_path 得到文件内容及 state 得到 file_title,
        进行防护校验并对内容换行统一操作
    (2) 标题粗切：把内容按照 \n 切成行列表，遍历行列表：每个行去除两边空格，进行按照标题合并片段
        这部分的核心难点就在于代码围栏的匹配问题：
        -> 第一步：先将这个文档，按照行切分成一个大的列表，每个元素代码一行数据。
        -> 第二步：开始循环判断每行数据的内容。
        -> 第三步：在循环过程中进行代码围栏的判断,通过正则来匹配 # 是否是代码围栏中的内容，如果是那是第几次匹配到的内容 。
                  如果是第一次匹配到，那么我们就将匹配的表示 更改为True，如果是第二次就将其更改为False，通过这样的方式来完成代码围栏的问题处理。
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
        -> 第四步：通过找后切前的思路完成内容切分，这得到的是一个二维列表。
        -> 第五步：最后合并成一个列表输出。
    (3) 长度细切：通过 递归字符切分器(RecursiveCharacterTextSplitter) 完成长切短合。
        -> 第一步：循环遍历每个元素的内容。
        -> 第二步：根据切分的要求，来进行判断，是否需要切分，小于切分要求的不切，存在表格的不切。
    """

    name = "node_document_split"

    def process(self, state: ImportGraphState):

        # 1、获取测试给的 md 内容集文件标题，内容需要进行换行符统一。
        file_title, md_content = self.get_md_content(state)

        # 2、粗切：根据每行是不是标题来进行粗切，以标题和它所属内容组成大块。
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

            # 获取真实的文本内容,z只要文本，不要标题。
            real_content = content[len(title) + 2 :] if content.startswith("#") else content

            # 长度小于 300 的不切
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

        # 问题：上面的代码有没有完成短合的思路，短合应该是两个不同的内容之间，还是怎么样？


        # # 1.3 保存一份，用于后面节点的测试
        # with open(r"C:\Users\Administrator\Desktop\test2\万用表RS-12的使用\final_spilt_list.json", "w",encoding="utf-8") as f:
        #     f.write(json_format(final_chunk_list))

        # 1.4 返回即可,这个数据后期需要进行肢体识别，然后再经混合向量化，最后再进行持久化处理。
        return {
            "chunks":final_chunk_list
        }

if __name__ == "__main__":
    node = NodeDocumentSplit()
    
    init_state = {
        "md_path":r"C:\Users\Administrator\Desktop\test2\万用表RS-12的使用\万用表RS-12的使用_new.md",
        "file_title":"万用表RS-12的使用_new"
    }
    result = node(init_state)
    # print("result=",result)