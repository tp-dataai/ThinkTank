# thinktank/import_process/nodes/node_entry.py
import json
from datetime import datetime
from langchain.chat_models import init_chat_model
from pymilvus import DataType
import hashlib
from thinktank.tool.json_format import json_format

from thinktank.import_process.base import NodeBase
from thinktank.import_process.state import ImportGraphState
from thinktank.tool.logger import logger
from thinktank.config.config import LLMConfig
from thinktank.config.prompt import ITEM_NAME_SYSTEM_PROMPT,ITEM_NAME_USER_PROMPT_TEMPLATE
from thinktank.tool.tool_llm_init import get_llm_init
from thinktank.tool.tool_milvus_client import get_milvus_client
from thinktank.config.config import MilvusConfig
from thinktank.tool.bgem3_embedding_tool import get_bgem3_embeddings

class NodeItemNameRecognition(NodeBase):
    """
    主体识别：主体识别与标签提取
    """

    name = "node_item_name_recognition"

    def process(self, state: ImportGraphState):

        # 1、获取切分 好的 chunks 和 文件名称
        file_title, chunks = self.get_split_chunks(state)

        # 2、将 chunks的前10个内容提取出来进行拼接处理
        chunk_k_str = self.get_chunks_str(file_title, chunks)

        # 3、初始化大模型，对 chunk_k_str 进行总结，识别出来我们的主体名（商品名）
        item_name = self.get_item_name(file_title,chunk_k_str)

        # 4、创建向量数据库的表，后期需要将大模型识别出来的主体存储在 Milvus 中。
        collection_name, milvus_client = self.create_milvus_collection()

        # 5、将识别出来的内容插入到 Milvus 中。
        file_title_id = self.insert_item_name(item_name, collection_name, milvus_client, file_title)

        # 6、将识别出来的 主体名返回到 chunks 中，增强 chunks 的内容。
        self.back_item_name_to_chunk(file_title_id,chunks,item_name)
        # 7、最后需要返回 增强后的 chunks 和 item_name (主体名)
        return {
            "chunks":chunks,
            "item_name":item_name,
        }

    def get_split_chunks(self,state):
        #   1.1、先做防御性判断，看看这个 chunks文件 和文件名称是否存在。
        file_title = state.get("file_title")
        chunks = state.get("chunks")
        
        if not chunks:
            logger.warning("chunks文件不能为空")
            raise ValueError("chunks文件不能为空")

        if not file_title:
            logger.warning("file_title 不能为空")
            raise ValueError("file_title 不能为空")
        
        return file_title, chunks
    
    def get_chunks_str(self, file_title, chunks):
        # 进行主体内容识别。
        #   2.1、先在 chunks列表中提取出前 10 个元素的内容  
        #   2.2 通过循环的方式将这 10个 元素的内容进行合并处理
        #       还需要关注的是，在拼接过程中需要判断拼接的长度是否超过 10000.
        #       如果超过 10000 的话，剩余的内容就不进行拼接。最后返回拼接好的内容。
        #   拼接的过程中，需要用一下内容：
        # f"[切片:{idx}]\n[标题:{title}]\n[文件名:{file_title}]\n[内容:{content}]\n\n"

        chunks_k_list = chunks[:10]
        chunks_k_str = ""
        for idx, chunk in enumerate(chunks_k_list, start=1):
            # print("chunk=",chunk,"type=",type(chunk))
            title = chunk.get("title")
            content = chunk.get("content")
            chunk_content = f"[切片:{idx}]\n[标题:{title}]\n[文件名:{file_title}]\n[内容:{content}]\n\n"
            chunks_k_str += chunk_content
            if len(chunks_k_str) >= 10000:
                break

            chunks_k_str = chunks_k_str[:10000]

        #   2.3 最后返回 拼接的内容即可。
        return chunks_k_str

    def get_item_name(self,file_title,chunk_k_str):
        #   3.1、初始化大模型的内容。
        llm = get_llm_init()

        #   3.2、准备提示词内容
        message = [
            {"role":"system","content":ITEM_NAME_SYSTEM_PROMPT},
            {"role":"user","content":ITEM_NAME_USER_PROMPT_TEMPLATE.format(file_title=file_title,context=chunk_k_str)}
        ]

        #   3.3、调用invoke执行
        result = llm.invoke(message)

        #   3.4、将大模型返回的内容进行处理
        item_name = result.content.replace("\t","").replace("\n","").replace(" ","")
        if not item_name:
            item_name = file_title

        #   3.5、将最后识别出来的 商品名 返回即可。
        return item_name

    def create_milvus_collection(self):
        #   4.1、初始化一个 Minlvus 客户端
        milvus_client = get_milvus_client()
        collection_name = MilvusConfig.item_name_collection

        #   4.2、创建结构、创建索引（稠密向量和稀疏向量索引）、创建表
        if not milvus_client.has_collection(collection_name):
            # 创建表：1、创建结构  2、创建索引  3、创建表（创建表之前判断表在不在）
            schema = milvus_client.create_schema(
                auto_id=False,
            )
            schema.add_field(
                field_name="file_title_id",
                datatype=DataType.VARCHAR,
                max_length=100,
                is_primary=True,  # 主键
            ).add_field(
                field_name="item_name",
                datatype=DataType.VARCHAR,
                max_length=100
            ).add_field(
                field_name="file_title",
                datatype=DataType.VARCHAR,
                max_length=100
            ).add_field(
                field_name="dense_vector",
                datatype=DataType.FLOAT_VECTOR,
                dim=1024  # 必须加维度
            ).add_field(
                field_name="sparse_vector",
                datatype=DataType.SPARSE_FLOAT_VECTOR,
                # 千万别加维度
            ).add_field(
                field_name="create_date",
                datatype=DataType.VARCHAR,
                max_length=50,
            )

            # 创建索引
            index_params = milvus_client.prepare_index_params()

            # 稠密向量索引创建
            index_params.add_index(
                field_name="dense_vector",
                index_type="IVF_FLAT",
                index_name="dense_vector_index_ivf_flat",
                metric_type="COSINE",   # 求相似度
                params={
                    "nlist":128,
                    "nprobe":10,
                }
            )

            # 稀疏向量索引创建
            index_params.add_index(
                field_name="sparse_vector",
                index_type="SPARSE_INVERTED_INDEX",
                index_name="sparse_vector_index_sparse_inverted_index",
                metric_type="IP",
                params={"inverted_index_algo":"DAAT_MAXSCORE"}
                # 也是为了提升效率
                # 把chunk在稀疏检索的时候分为两组，一组是包含问题关键字，另一组不包含
                # 查找的时候先去找包含问题关键字的这一组，效率就会提升。
            )

            milvus_client.create_collection(
                collection_name=collection_name,
                schema=schema,
                index_params=index_params,
            )

            # print("collection_name=",collection_name)
            # print("milvus_client=",milvus_client)
        #   4.3、返回一个 表 和 Milvus 客户端
        return collection_name, milvus_client

    def insert_item_name(self, item_name, collection_name, milvus_client, file_title):
        #   5.1、先将识别出来的主体名进行向量化。
        file_title_id = hashlib.md5(file_title.encode('utf-8')).hexdigest()
        item_name_vector = get_bgem3_embeddings([item_name])
        dense_vector = item_name_vector["dense"][0]
        sparse_vector = item_name_vector["sparse"][0]
        create_date = str(datetime.now())

        milvus_client.load_collection(collection_name=collection_name)

        #   5.2、幂等性删除处理
        # 把filte_title可能出现的特殊字符处理一下
        # 按照文件的 标题来完成数据的删除和更新
        # filter_file_title = (
        #     file_title.replace("\\", "\\\\")
        #     .replace("\'", "\\'")
        #     .replace('\"', '\\"')
        # )

        # expr = f'id in ["{id}"]'  # 字符串值必须用双引号包裹

        milvus_client.delete(
            collection_name=collection_name,
            ids=[file_title_id]  # 直接传入主键字符串列表，SDK 会自动处理表达式生成
        )
        #   5.3、将数据插入到 Milvus中。
        data = {
            "file_title_id":file_title_id,
            "item_name":item_name,
            "file_title":file_title,
            "dense_vector":dense_vector,
            "sparse_vector":sparse_vector,
            "create_date":create_date,
        }

        res = milvus_client.insert(
            collection_name=collection_name,
            data=data,
        )

        return file_title_id

    def back_item_name_to_chunk(self, file_title_id: str, chunks: list, item_name: str):
        for chunk in chunks:
            chunk["item_name"] = item_name
            chunk["file_title_id"]=file_title_id  # 这个id 是根据 file_title 获得的id，主要用于后续的 幂等性删除
        
        # # 再去备份回填完的chunks到json文件
        # with open(r"C:\Users\Administrator\Desktop\test1\万用表RS-12的使用\final_spilt_list_new.json", "w", encoding="utf-8") as f:
        #     # json.dump(chunks, f, ensure_ascii=False, indent=4)
        #     f.write(json_format(chunks))    

if __name__ == "__main__":

    item_name = NodeItemNameRecognition()
    with open(r"C:\Users\Administrator\Desktop\test1\万用表RS-12的使用\final_spilt_list.json", "r", encoding="utf-8") as f:
        chunks = json.load(f)
        
    init_stata = {
        "chunks":chunks,
        "file_title":"万用表RS-12的使用"
    }

    result = item_name(init_stata)