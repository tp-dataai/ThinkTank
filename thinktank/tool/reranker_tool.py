import dashscope

from thinktank.config.config import RerankConfig

# 初始化客户端
client = dashscope.Client(
    api_key = RerankConfig.rerank_api_key,
    workspace=RerankConfig.rerank_work_space,
    region="cn-beijing",
)

def text_rerank(query, documents):
    resp = client.rerank.create(
        model="qwen3.7-text-rerank",
        query=query,
        documents=documents,
        top_n=len(documents),
        return_documents=False,
        instruct="Given a web search query, retrieve relevant passages that answer the query."
    )

    return [
        {
            "index":item.index,
            "score":item.relevance_score
        }
        for item in resp.results
    ]

if __name__ == '__main__':
    result = text_rerank(query="我爱谁", documents=["我爱杨幂","我爱赵丽颖"])
    print(result)