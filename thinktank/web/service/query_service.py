# 1. 创建应用
import json
import time
import uuid

import uvicorn
from fastapi import FastAPI, Path, Body, BackgroundTasks
from pydantic import BaseModel, Field
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse

from thinktank.query_process.main_graph import QueryMainGraphRunner
from thinktank.tool.mongo_tool import clear_history, get_recent_message
from thinktank.tool.task_utils import update_task_status, TASK_STATUS_PROCESSING, TASK_STATUS_COMPLETED, \
    TASK_STATUS_FAILED, get_q, put_data, get_task_info, q_dict, get_data

app = FastAPI(
    title="掌柜智库-检索API",
    description="此文档是掌柜智库检索流程的API接口说明"
)

# 2. 跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许的源
    allow_credentials=True,  # 允许携带cookie
    allow_methods=["*"],  # 允许的请求方法
    allow_headers=["*"],  # 允许的请求头
)


# todo 1 书写健康检查接口
@app.get("/health")
def health():
    return {"msg": "ok"}


# todo 2 书写清空历史记录的接口
@app.delete("/history/{session_id}")
def remove_history(session_id: str = Path(...,description="用户会话id")):
    clear_history(session_id=session_id)
    return {"msg": "ok"}



#todo 3 书写获取历史记录的接口
@app.get("/history/{session_id}")
def get_history(session_id: str = Path(...,description="用户会话id")):
    history_list = get_recent_message(session_id=session_id)
    history_list = [
        {
            **item,
            "_id":str(item.get("_id"))
        }
        for item in history_list
    ]
    history_list.sort(key=lambda item: item["ts"])
    return {
        "items": history_list,
    }



#todo 4 书写用户查询的接口（普通请求）

# def run_main_graph(task_id,original_query, session_id):
#     q = get_q(task_id)
#     init_state = {
#         "task_id": task_id,
#         "original_query":original_query,
#         "session_id": session_id,
#     }

#     try:
#         #设置全局状态数据为处理中
#         update_task_status(task_id,TASK_STATUS_PROCESSING) #修改状态
#         put_data(task_id,event="progress",data=get_task_info(task_id))#把修改的状态数据存到队列
#         QueryMainGraphRunner.create_and_run(init_state)
#         update_task_status(task_id, TASK_STATUS_COMPLETED)
#         put_data(task_id, event="progress", data=get_task_info(task_id))  # 把修改的状态数据存到队列
#     except:
#         update_task_status(task_id, TASK_STATUS_FAILED)
#         put_data(task_id, event="error", data=get_task_info(task_id))  # 把修改的状态数据存到队列
#         raise

def run_main_graph(task_id, original_query, session_id):
    # q = get_q(task_id) # 这行没用，可以删掉
    init_state = {
        "task_id": task_id,
        "original_query": original_query,
        "session_id": session_id,
    }

    try:
        update_task_status(task_id, TASK_STATUS_PROCESSING)
        put_data(task_id, event="progress", data=get_task_info(task_id))
        
        # 💡 核心修改 1：接收 LangGraph 执行完的最终状态
        result_state = QueryMainGraphRunner.create_and_run(init_state) 
        
        update_task_status(task_id, TASK_STATUS_COMPLETED)
        put_data(task_id, event="progress", data=get_task_info(task_id))
        
        # 💡 核心修改 2：提取最终的完整答案，发送 final 事件给前端
        final_answer = result_state.get("answer", "") if result_state else ""
        put_data(task_id, event="final", data={"answer": final_answer})
        
    except Exception as e:
        update_task_status(task_id, TASK_STATUS_FAILED)
        # 💡 核心修改 3：错误信息要传给前端，而不是传 progress 状态
        put_data(task_id, event="error", data={"error": str(e)}) 
        # raise # 可以保留 raise 也可以去掉，看你的日志处理策略

class BodyParams(BaseModel):
    query: str = Field(...,description="用户原始问题")
    session_id: str = Field(...,description="用户会话id")

@app.post("/query")
def query(
        background_tasks: BackgroundTasks,
        body_params:BodyParams = Body(...,description="请求体参数")
):
    task_id = str(uuid.uuid4())
    original_query = body_params.query
    session_id = body_params.session_id

    background_tasks.add_task(run_main_graph, task_id, original_query, session_id)

    return {"task_id":task_id}



# todo sse推送接口
def generate_data(task_id):
    while task_id not in q_dict:
        time.sleep(1)

    while True:
        data = get_data(task_id)
        event_type = data.get('event')

        yield f"event: {data.get('event')}\n"
        yield f"data: {json.dumps(data.get('data'))}\n\n" #传数据的时候不能直接把字典往过推，必须把字典变成json字符串
        # 💡 核心修改：遇到 final 或 error 必须跳出循环，结束 SSE 响应！
        if event_type in ["final", "error"]:
            break
@app.get("/stream/{task_id}")
def stream(task_id: str = Path(...,description="任务id")):
    return StreamingResponse(generate_data(task_id), media_type="text/event-stream")

# 7. 启动项目
if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=8001)