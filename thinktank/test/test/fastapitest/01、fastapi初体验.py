import uvicorn
from fastapi import  FastAPI


app = FastAPI(
    title="这个是测试的接口",
    version="0.0.1",
    description="这些接口就是来测试fastapi简单入门"
) #创建的fastapi应用对象，这些参数都是为了在接口文档上可以看到

@app.get("/")
def hello_world():
    return "hello world"



if __name__ == '__main__':
    uvicorn.run(
        app=app,
        host="0.0.0.0",
        port=8000,
    )