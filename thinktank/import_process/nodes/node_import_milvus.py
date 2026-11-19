import json
from pymilvus import DataType
import hashlib
from datetime import datetime

from thinktank.tool.json_format import json_format
from thinktank.import_process.base import NodeBase
from thinktank.import_process.state import ImportGraphState
from thinktank.tool.logger import logger
from thinktank.tool.tool_milvus_client import get_milvus_client
from thinktank.config.config import MilvusConfig

class NodeImportMilvus(NodeBase):
    """
    将数据向量化后插入到 Milvus 中进行存储。
    步骤：
    (1) 得到最终的 Chunk 内容。
    (2) 创建一个 Mivlus 客户端
    (3) 创建 collection: -> 创建结构、创建索引、创建collection
    (4) 幂等性设计，
    (5) 然后将 Chunk 中的数据插入collection中。
    """

    name = "node_import_milvus"

    def process(self, state: ImportGraphState):
        # print("01 第一步")
        # 1、先获得 chunks 的内容。
        chunks = state.get("chunks")
        file_title = state.get("file_title")

        # 2、然后对 chunks 的内容做防御性判断。
        if not chunks:
            logger.error("chunks 不能为空")
            raise Exception("chunks 不能为空")
        
        if not file_title:
            logger.error("file_title 不能为空")
            raise Exception("file_title 不能为空")
        
        # 3、创建一个 Milvus 客户端的内容 并通过配置文件获得 Milvus 中的collection 的名称。
        milvus_client = get_milvus_client()
        collection_name = MilvusConfig.chunks_collection

        # 4、先通过 has_collection() 去判断是否存在collection ，如果不存在的话
        # print("02 chunks获取成功，开始创建collection等内容")

        if not milvus_client.has_collection(collection_name=collection_name):
            # 4.0 就开始创建 schema 内容。
            schema = milvus_client.create_schema(
                auto_id=True
            ).add_field(
                field_name="id",
                datatype=DataType.INT64,
                is_primary=True,
            ).add_field(
                field_name="title",
                datatype=DataType.VARCHAR,
                max_length=100,
            ).add_field(
                field_name="file_title_id",
                datatype=DataType.VARCHAR,
                max_length=100,
            ).add_field(
                field_name="file_title",
                datatype=DataType.VARCHAR,
                max_length=100,
            ).add_field(
                field_name="content",
                datatype=DataType.VARCHAR,
                max_length=5000,
            ).add_field(
                field_name="part",
                datatype=DataType.INT64,
            ).add_field(
                field_name="item_name",
                datatype=DataType.VARCHAR,
                max_length=100
            ).add_field(
                field_name="dense_vector",
                datatype=DataType.FLOAT_VECTOR,
                dim=1024,
            ).add_field(
                field_name="sparse_vector",
                datatype=DataType.SPARSE_FLOAT_VECTOR,
            ).add_field(
                field_name="create_date",
                datatype=DataType.VARCHAR,
                max_length=100,
            )
            # 4.1、创建索引
            index_params = milvus_client.prepare_index_params()
            index_params.add_index(
                field_name="dense_vector",
                index_type="IVF_FLAT",
                index_name="dense_vector_ivf_flat",
                metric_type="COSINE",
                params={
                    "nlist":128,
                    "nprobe":10,
                }
            )

            index_params.add_index(
                field_name="sparse_vector",
                index_type="SPARSE_INVERTED_INDEX",
                index_name="sparse_vector_sparse_inverted_index",
                metric_type="IP",
                params={"inverted_index_algo":"DAAT_MAXSCORE"},
            )

            # 创建 collection
            milvus_client.create_collection(
                collection_name=collection_name,
                schema=schema,
                index_params=index_params,
            )
        # print("03 collection创建成功，开始幂等性删除") 

        milvus_client.load_collection(collection_name)

        # 4.2、幂等性删除
        file_title_id = chunks[0].get("file_title_id")
        # print("file_title_id=", file_title_id)

        milvus_client.delete(
            collection_name=collection_name,
            filter=f'file_title_id == "{file_title_id}"' 
        )

        # 💡 在插入之前，统一给每条数据打上创建时间
        create_date = str(datetime.now())

        # print("04 开始插入数据") 
        for chunk in chunks:
            # 给每个字典动态添加 create_date 键
            chunk["create_date"] = create_date

        # 4.3、将数据插入到 Milvus 中。
        res = milvus_client.insert(
            collection_name=collection_name,
            data=chunks
        )

        # print("所有数据完成向量化嵌入，并成功插入 Milvus 中~~~~~~~")

        # for idx, chunk in enumerate(chunks):
        #     chunk["id"]=res["ids"][idx]

        # return {
        #     "chunks":chunks
        # }

if __name__ == "__main__":

    node = NodeImportMilvus()

    with open(r"C:\Users\Administrator\Desktop\test2\万用表RS-12的使用\final_spilt_list_item_name_cunks_vector.json","r",encoding="utf-8") as f:
        chunks = json.load(f)

    init_state = {
        "chunks":chunks,
        "file_title":"万用表RS-12的使用",
    }

    result = node(init_state)
    # print("result=", json_format(result))