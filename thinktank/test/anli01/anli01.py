import uvicorn
import uuid
import os
import shutil
import time
import queue

from fastapi import FastAPI, BackgroundTasks,Query
from pydantic import BaseModel, Field
from fastapi.responses import StreamingResponse


app = FastAPI()


# 后台任务（BackgroundTasks）、线程安全队列（queue.Queue） 
# 和 SSE（Server-Sent Events）流式响应（StreamingResponse）。

# 在多用户同时访问时，防止数据串线。
# key 是 session_id，value 是 queue.Queue() 对象。张三和李四各自有一个窗口，互不干扰。
queue_dict = {}  # 这是一个存储所有用户专属队列的“大字典”。一个 session_id 代表一个用户。

def generate_email(session_id):
    queue_obj = queue_dict[session_id]

    # 如果队列中为空，那就先等待 3 秒
    while queue_obj.empty():
        time.sleep(3)

    # 后端服务进行处理的内容。
    queue_obj.put("发送第1封邮件" + session_id)
    queue_obj.put("发送第2封邮件" + session_id)
    queue_obj.put("发送第3封邮件" + session_id)
    queue_obj.put("发送第4封邮件" + session_id)
    queue_obj.put("发送第5封邮件" + session_id)
    queue_obj.put("发送第6封邮件" + session_id)
    queue_obj.put(None)  # 告知前端结束，关闭sse


@app.get("/send_message")
def send_message(
    background_tasks: BackgroundTasks,
    session_id:str = Query(..., description="会话编号")
):
    # 先判断前端发过来的 session_id 是否在 队列中。
    # 如果并不在队列中，说明是一个新的 session_id ，就先插入。
    if session_id not in queue_dict:
        queue_dict[session_id] = queue.Queue()

    """
    使用 background_tasks.add_task 把 generate_email 塞进后台执行。这一步极其重要，它不会阻塞当前接口，
    接口会瞬间返回给前端 {"message": "开始生成..."}。
    注意：如果是同步的 def, FastAPI 会把它扔到线程池里执行，不占用主事件循环。
    """
    background_tasks.add_task(generate_email, session_id)

    return {
        "session_id": session_id,
        "message":"开始生成邮件添加队列"
    }

 
@app.get("/ssestream")
async def ssestream(session_id: str = Query(...,description="会话编号")):
    def send_email(session_id: str):
        queue_obj = queue_dict[session_id]

        while True:
            email = queue_obj.get()
            time.sleep(1)
            yield f"data: {email}\n\n"
            if email is None:
                break
    return StreamingResponse(send_email(session_id),media_type="text/event-stream")

if __name__ == "__main__":
    uvicorn.run(
        app=app,
        host="0.0.0.0",
        port=8001,
    )