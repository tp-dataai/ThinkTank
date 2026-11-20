import time
from pathlib import Path

import uvicorn
from fastapi import FastAPI, BackgroundTasks
from starlette.background import BackgroundTask
from starlette.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

app = FastAPI(
    title="这个是测试的接口",
    version="0.0.1",
    description="这些接口就是来测试fastapi简单入门"
) #创建的fastapi应用对象，这些参数都是为了在接口文档上可以看到

#解决跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 允许所有来源域名访问
    allow_credentials = True,  # 允许携带凭证（Cookie、Authorization 头等）
    allow_methods = ["*"],  # 允许所有 HTTP 方法（GET/POST/PUT/DELETE...）
    allow_headers = ["*"],  # 允许所有请求头
)


BASE_DIR = Path(__file__).parent
static_dir = BASE_DIR / "static"
#以后发请求如果路径是以/static开头，那么就去找static目录当中的资源
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/getdata")
def get_data():
    return {"hello": "world"}

#跨域的条件
#1、前后端分离
#2、发送ajax请求
#才有可能扩域
#跨域说的是协议、ip、端口号有一个和后端服务器不一样就跨域
#跨域是浏览器上存在的一种同源验证策略
#同源：协议、ip、端口号一样
#不同源（异域） 协议、ip、端口号至少有一个不同



#fastapi的接口前面加async和不加差距很大
#底层实现的原理不同：不加async底层用多线程，加了就是使用多协程任务
#如果你的代码里面没有异步操作，也就是说没必要用到异步接口，反而你加了async,那么效率将会很低，因为是串行
#如果你的代码没有加async，至少它是多线程处理，多线程处理是GIL释放决定效率，效率反而比协程要好
#反之，有异步操作当然就是async的效率最高

def print_love(n):
    # MainGraphRunner.create_and_run(init_state)
    while n > 0:
        print("我爱你杨幂")
        time.sleep(2)
        n -= 1

# todo 后台任务，非常重要
@app.get("/testbackgroundtask")
def test_background_task(background_tasks: BackgroundTasks):
    #1、后台任务是异步效果，不会等它走完才返回数据
    #2、发了请求立即返回msg
    #3、后台仍然在执行后台任务
    background_tasks.add_task(print_love,10)
    return {"msg":"ok"}










if __name__ == '__main__':
    uvicorn.run(
        app=app,
        host="0.0.0.0",
        port=8000,
    )