from pymilvus import MilvusClient, AnnSearchRequest, RRFRanker, WeightedRanker
from thinktank.config.config import MilvusConfig


milvus_client = None

def get_milvus_client():

    global milvus_client

    if milvus_client is None:
        milvus_client = MilvusClient(
            uri=MilvusConfig.milvus_url
        )
    return milvus_client


# 封装混合检索的工具
# 1、创建稠密向量和稀疏向量检索的请求对象
# AnnSearchRequest

# 2、根据创建的请求对象列表真正的去混合检索
def get_req_list(
        dense_data,
        sparse_data,
        dense_anns_field,
        sparse_anns_field,
        dense_param=None,
        sparse_param=None,
        limit=10,
        expr=None
):

    if dense_param is None:
        dense_param ={
            "metric_type":"COSINE"
        }

    if sparse_param is None:
        sparse_param = {
            "metric_type":"IP"
        }
    # 稠密向量的内容
    dense_req = AnnSearchRequest(
        data=[dense_data],           # 后期检索的时候，大模型识别出来的某个商品名称的稠密向量
        anns_field=dense_anns_field,
        param=dense_param,
        limit=limit,
        expr=expr
    )

    # 稀疏向量
    sparse_req = AnnSearchRequest(
        data=[sparse_data],           # 后期检索的时候，大模型识别出来的某个商品名称的稀疏向量
        anns_field=sparse_anns_field,
        param=sparse_param,
        limit=limit,
        expr=expr        
    )

    return [dense_req, sparse_req]

# 混合检索的函数
def hybrid_search(collection_name,reqs,output_fields,limit=10,ranker=(0.5, 0.5)):
    milvus_client = get_milvus_client()

    weighted_ranker = WeightedRanker(*ranker)  # 加权排名排序器

    res = milvus_client.hybrid_search(
        collection_name=collection_name, # 差的是哪个表？
        reqs=reqs,       # 上一步拿到的稀疏向量和稠密向量的列表
        ranker=weighted_ranker,  # 排序器
        limit=limit,     # top-k
        output_fields=output_fields,
    )

    return res

if __name__ == "__main__":
    milvus_client = get_milvus_client()
    print("milvus_client=",milvus_client)