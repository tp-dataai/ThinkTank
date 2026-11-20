# 这个文件是专门用来封装 mongodb 操作的文件。
# 1、获取mongodb连接对象 单例，通过MongoDB的url就能获得客户端的内容。
# 封装与M MongoDB 相关的数据操作的功能。
import time
from pymongo import MongoClient
from thinktank.config.config import MongoConfig
# from bson.objectid import ObjectId

# 1、创建 MongoDB 客户端
mongdb_client = None
def get_mongdb_client():
    global mongdb_client

    if mongdb_client is None:
        mongdb_client = MongoClient(MongoConfig.mongo_url)

    return mongdb_client

# 2、创建获取 MongoDB 的表对象，因为只有拿到表对象才能操作表。
mongdb_tool = None
def get_mongdb_collection():
    global mongdb_tool
    if mongdb_tool is None:
        mongdb_client = get_mongdb_client()
        db = mongdb_client[MongoConfig.mongo_db_name]

        mongdb_collection = db["chat_history"] # 拿到表对象

        # 索引提升效率
        mongdb_collection.create_index([("session_id",1),("ts",-1)])

    return mongdb_collection

# 3、get_recent_messages 根据 session_id 获取最近的n条消息
def get_recent_message(session_id, limit = 10):
    mongo_collection = get_mongdb_collection()  # 获得 我们需要的 collection

    # 一个 session_id 可能对应多条数据。
    result = mongo_collection.find({"session_id":session_id}).sort({"ts":-1}).limit(limit)

    return list(result)

# 4、clear_history 清空某个 session_id 的所有消息
def clear_history(session_id):
    mongo_collection = get_mongdb_collection()
    # 使用 delete_many来完成数据的删除
    mongo_collection.delete_many({"session_id":session_id})

# 5、save_chat_message 保存历史记录（根据id决定是添加还是修改） 
# 增改一体化（增和改写一个函数）
# 这个项目中是否需要修改的功能这个还需要考虑。
# 注意保存的每一轮的对话内容。
def save_chat_message(session_id,role,text,rewritten_query=None,item_names=None,ts=None,message_id=None):
    mongo_collection = get_mongdb_collection()

    if message_id is None:
        res = mongo_collection.insert_one({
            "session_id": session_id,
            "role": role,
            "text": text,
            "rewritten_query": rewritten_query,
            "item_names": item_names,
            "ts": ts or time.time(),
        })
        return res.inserted_id  # 这个 id 是插入数据的时候返回的id。

    else:
        mongo_collection.update_one({"_id":message_id}, {
            "$set":{
                "session_id": session_id,
                "role": role,
                "text": text,
                "rewritten_query": rewritten_query,
                "item_names": item_names,
                "ts": ts or time.time(),                
            }
        })

# 数据回传历史记录中(回传还是属于更新)
# 需要回传的数据id，这里面的数据不仅仅是一条。
# item_names 这里面的数据表示的 从 MongoDB 中识别出来的内容
# rewritten_query：？
def update_history_item_names(ids,item_names,rewritten_query):
    mongo_collection = get_mongdb_collection()
    mongo_collection.update_many({"_id":{"$in":ids}},{
        "$set":{
            "item_names":item_names,
            "rewritten_query":rewritten_query,
        }
    })


if __name__ == '__main__':
    session_id = "test_001"
    get_recent_message(session_id,10)

    # 用于验证数据是否能正常插入
    save_chat_message(session_id, "user", "咨询儿童教育问题")
    save_chat_message(session_id, "assistant", "叛逆期应该怎么处理？")
    save_chat_message(session_id, "user", "如何和他沟通？")
    save_chat_message(session_id, "assistant", "应该怎么办？")
    print("内容全部插入 MongoDB中")