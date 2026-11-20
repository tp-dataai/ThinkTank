# 目标：后端先接收查询请求，后台处理，SSE 推送处理结果
#
# 案例2 使用post请求加异步操作
# 	1、前端发请求传递一个query，再传递一个session_id  两个参数到后端进行请求体接收
# 	2、后端写一个接口获取这两个参数，并返回给前端收到的消息，并启动task造消息
# 	3、前端订阅sse请求
# 	4、服务端需要写sse回复接口，从task当中获取自己的队列，从队列当中一个一个yield答案
import asyncio

import uvicorn
from fastapi import FastAPI, Body, BackgroundTasks, Query
from pydantic import BaseModel, Field
from starlette.middleware.cors import CORSMiddleware
from asyncio import Queue

from starlette.responses import StreamingResponse

# from queue import Queue

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# todo 第二大步：书写接口处理第一大步发送的普通post请求
q_dict = {}
async def make_data(session_id,query):
    if session_id not in q_dict:
        q_dict[session_id] = Queue()
    q = q_dict.get(session_id)
    # sse推送 我爱杨幂
    # sse推送 我爱赵丽颖


    await q.put({"event":"progress","data":"我爱杨幂"})
    await q.put({"event":"progress","data":"我爱赵丽颖"})
    await q.put({"event":"progress","data":"我爱迪丽热巴"})
    await q.put({"event":"progress","data":"我爱刘诗诗"})
    await q.put({"event":"progress","data":"我爱柳岩"})
    await q.put({"event":"final","data":"我不爱了"})

class BodyPrams(BaseModel):
    session_id: str = Field(...,description="Session ID")
    query: str = Field(...,description="query")

@app.post("/startwork")
def startwork(
    background_tasks: BackgroundTasks,
    body_prams: BodyPrams = Body(...,description="请求体参数")
):
    session_id = body_prams.session_id
    query = body_prams.query

    background_tasks.add_task(make_data,session_id,query)

    return {"msg":"开始造数据"}




# todo 第四大步 书写sse订阅接口返回流式数据
async def generate_data(session_id):
    while session_id not in q_dict:
        await asyncio.sleep(1)

    q = q_dict.get(session_id)
    while True:
        try:
            data = await q.get()
            # a = 1 / 0
            await asyncio.sleep(1)
            yield f"event: {data.get('event')}\n"
            yield f"data: {data.get('data')}\n\n"
        except Exception as e:
            yield f"event: error\n"
            yield f"data: {e}\n\n"


@app.get("/sse02")
def sse02(
    session_id: str = Query(...,description="Session ID"),
):
    return StreamingResponse(generate_data(session_id),media_type="text/event-stream")





if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=8000)

