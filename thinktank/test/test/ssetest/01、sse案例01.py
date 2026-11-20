# 案例1
# 	1、客户前端发ajax请求要发邮件并携带session_id，服务端直接回复收到，制造邮件开始
# 	2、服务端就开始执行backgroundtask当中造邮件的函数，造的邮件全部放在队列当中
import time
from queue import Queue

import uvicorn
# 	3、客户端想直接拿到造的邮件内容，造一个拿一个，那么客户端需要去发送订阅sse请求
# 	4、服务端需要写sse回复接口，流式返回，流式返回就是把一个生成器对象返回
# 		生成器函数当中就是从queue_dict当中获取自己session_id的队列，从队列当中一个一个yield球
#
# 注意：每个session_id对应自己的邮件队列

from fastapi import FastAPI, Path, BackgroundTasks, Query
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




#todo 第二大步 书写接口处理前端发送的普通http请求开始工作造数据
q_dict = {}
def make_email(session_id: str):
    #每个用户session_id不一样，造的邮件也不一样，此时我们需要把造的数据按用户分开
    #咱们使用队列来保存邮件数据，每个队列按照session_id为键，每个用户的队列为值保存到字典
    #判断这个人有没有队列，没有就造一个队列
    if session_id not in q_dict:
        q_dict[session_id] = Queue()

    #造数据放队列
    q = q_dict.get(session_id)
    q.put(f"{session_id}用户的第1封邮件")

    q.put(f"{session_id}用户的第2封邮件")
    q.put(f"{session_id}用户的第3封邮件")
    q.put(f"{session_id}用户的第4封邮件")
    q.put(None)
    print("制造邮件结束")





@app.get("/startwork/{session_id}")
def start_work(
    background_tasks: BackgroundTasks,
    session_id: str = Path(...,description="用户的标识会话id")
):
    background_tasks.add_task(make_email,session_id)

    return {"msg":"收到，开始制造邮件"}


# todo 第五大步：书写生成器函数，完成流式输出数据,获取用户对应的队列，拿一条吐一条
def generate_data(session_id: str):
    while session_id not in q_dict:
        time.sleep(1)

    #保证队列创建完成，存在
    q = q_dict.get(session_id)
    while True:
        data = q.get()
        time.sleep(1)
        yield f"data: {data}\n\n" #两个\n代表sse一次输出结束，规定没有为啥
        if data is None:
            break

# todo 第四大步书写sse的订阅接口
@app.get("/sse01")
def sse01(session_id: str = Query(...,description="用户标识会话id")):
    #StreamingResponse流式响应
    return StreamingResponse(generate_data(session_id),media_type="text/event-stream")



if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=8000)

