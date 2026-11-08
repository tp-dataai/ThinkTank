"""
该函数的作用主要是处理嵌入模型和通过嵌入模型完成 稀疏向量和 稠密向量的生成；
"""

from pymilvus.model.hybrid import BGEM3EmbeddingFunction
from typing import List

from thinktank.config.config import EmbeddingConfig
from thinktank.tool.json_format import json_format

embeddding_model = None

# 1、创建一个函数用于初始化嵌入模型
def get_embedding_model():
    global embeddding_model  # 定义一个全局变量

    if embeddding_model is None:
        embeddding_model=BGEM3EmbeddingFunction(
            model_name=EmbeddingConfig.bge_m3_path,
            device=EmbeddingConfig.bge_device,
            use_fp16=EmbeddingConfig.bge_fp16
        )
    return embeddding_model

def get_bgem3_embeddings(text_list:List[str]):
    # 先实例化一个对象。
    embeddding_model = get_embedding_model()
    """
    获取到的结果是一个字典列表的数据：
    主要有两部分构成：
        (1) dense: 稠密向量的数据;
        (2) sparse: 稀疏向量的数据;
    """
    result = embeddding_model.encode_documents(text_list)
    # print("result=",result)
    # todo 内容解析分析：
    # 就是需要去解析这个结果；
    # 获取稠密向量: -> 获取到的稠密向量 是一个列表数据，但是 每个列表中数据类型是 numpy.float16
    # 因此在最后我们需要将其转换为 python 中的 float 类型数据。
    # dense_vector = result["dense"]
    # print(f"dense_vector={dense_vector},type={type(dense_vector)}")
    # for dense_vector in dense_vector:
    #     print(f"dense_vector = {dense_vector}")
    #     res1 = dense_vector[0]
    #     print(f"res1={res1},type_res1={type(res1)}")
    #     res2 = dense_vector[0].tolist()
    #     print(f"res2={res2},type_res2={type(res2)}")
    dense_vector = [item.tolist() for item in result["dense"]]

    # 获取稀疏向量
    # print(f"sparse_vector={sparse_vector},type = {type(sparse_vector)}")
    # sparse_vector 本质上还是第一个字典数据
    # for item in sparse_vector:
    #     # print("item=",item.__dict__)
    #     item = dict(zip(item.indices.tolist(),item.data.tolist()))
    #     print("item_data=",item)

    """
    (1) zip()：将多个可迭代对象（如列表、数组）中对应的元素“拉链式”打包成一个个元组。
    (2) dict()：创建一个新的字典，或将由键值对组成的序列（如元组列表）快速转换为字典。
    (3) tolist()：将 NumPy 数组或 SciPy 矩阵等科学计算对象转换为 Python 原生的嵌套列表（List）。
    """
    sparse_vector =[ dict(zip(item.indices.tolist(),item.data.tolist())) for item in result["sparse"] ] 
    # print("sparse_vector= ",sparse_vector)

    return {
        "dense":dense_vector,
        "sparse":sparse_vector
    }

if __name__ == "__main__":
    embeddding_model = get_embedding_model()
    init_state = ["我爱学大模型", "我爱学习AI"]
    res = get_bgem3_embeddings(init_state)
    print("res=",json_format(res))