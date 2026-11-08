# 我们主要就是写配置类，以后只要有配置就有对应的配置类
import os

from dotenv import load_dotenv
load_dotenv(override=True)
#不加override=True还是会先从环境变量当中去找，写上这个参数意思就是不要找环境变量，全部从.env当中找

class MineruConfig:
    mineru_token = os.getenv("MINERU_TOKEN")

#配置文件当中拿到的数据默认都是字符串，如果要变为python的其它类型，需要强转
class LLMConfig:
    # API 密钥（兼容 OpenAI 格式）
    openai_api_key = os.getenv("OPENAI_API_KEY")
    openai_api_base = os.getenv("OPENAI_API_BASE")
    llm_default_model = os.getenv("LLM_DEFAULT_MODEL")
    llm_default_temperature = float(os.getenv("LLM_DEFAULT_TEMPERATURE", "0.1"))
    vl_model = os.getenv("VL_MODEL")
    item_model = os.getenv("ITEM_MODEL")

class MinioConfig:
    minio_endpoint = os.getenv("MINIO_ENDPOINT","192.168.77.77:9000")
    minio_access_key = os.getenv("MINIO_ACCESS_KEY")
    minio_secret_key = os.getenv("MINIO_SECRET_KEY")
    minio_bucket_name = os.getenv("MINIO_BUCKET_NAME","thinktank")
    minio_img_dir = os.getenv("MINIO_IMG_DIR")

class EmbeddingConfig:
    bge_m3_path=os.getenv("BGE_M3_PATH", "BAAI/bge-m3")
    bge_m3=os.getenv("BGE_M3")
    bge_device=os.getenv("BGE_DEVICE","1")
    # 进行特殊处理
    bge_fp16=os.getenv("BGE_FP16") in ("1","True","true",1)