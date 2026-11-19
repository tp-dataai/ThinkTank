import uvicorn
import uuid
import os
import shutil
import time
import queue
import asyncio

from fastapi import FastAPI, BackgroundTasks,Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from fastapi.responses import StreamingResponse

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

class BodyParam(BaseModel):
    session_id: str = Field(..., description="会话id")
    query: str = Field(..., description="用户问题")

queue_dic = {}

async def generate_answer(session_id, query):
    if session_id not in queue_dic:
        queue_dic[session_id] = asyncio.Queue()
    while not queue_dic[session_id]:
        await asyncio.sleep(3)

    await queue_dic[session_id].put("我")
    await queue_dic[session_id].put("爱")
    await queue_dic[session_id].put("杨")
    await queue_dic[session_id].put("幂")
    await queue_dic[session_id].put("!")
    await queue_dic[session_id].put(None)

@app.post("/send_message")
async def send_message(body_param: BodyParam,background_tasks: BackgroundTasks):
    print(body_param.session_id)
    print(body_param.query)

    background_tasks.add_task(generate_answer, body_param.session_id,body_param.query)

    return {"message": "收到,准备开始回答"}

@app.get("/sseanswer/{session_id}")
async def sseanswer(session_id: str):

    async def gen_answer():
        if session_id not in queue_dic:
            await asyncio.sleep(3)
        while True:
            answer = await queue_dic[session_id].get()
            yield f"data: {answer}\n\n"
            await asyncio.sleep(2)
            if answer is None:
                break
    return StreamingResponse(gen_answer(), media_type="text/event-stream")

if __name__ == "__main__":
    uvicorn.run(
        app=app,
        host="0.0.0.0",
        port=8001,
    )