from pymongo import MongoClient
from bson.objectid import ObjectId
from thinktank.config.config import MongoConfig
from thinktank.tool.mongo_tool import get_mongdb_client

# 1. 先获取 MongoClient 客户端实例（假设你之前封装了获取客户端的方法）
# 如果你代码里直接创建，就是 client = MongoClient("mongodb://...")
client = get_mongdb_client() 

# 2. 通过客户端获取【数据库对象】，而不是直接赋值字符串
# ✅ 正确做法：client[MongoConfig.mongo_db_name]
db = client[MongoConfig.mongo_db_name] 

# 3. 通过数据库对象获取【集合对象】
collection = db["chat_history"]

# 4. 查询数据
target_id = ObjectId('6af4417adc5a908b7130dc18')
result = collection.find_one({"_id": target_id})
print(result)