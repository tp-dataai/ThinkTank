import uvicorn
import uuid
import os
import shutil
from fastapi import FastAPI, Path, Query, Body, Depends, Request, UploadFile, File
from pydantic import BaseModel, Field
from fastapi.responses import JSONResponse,FileResponse,HTMLResponse

app = FastAPI()

@app.get("/api/user")
async def get_user():
    # 等价于直接 return {"name":"张三", "age":20}
    return JSONResponse(
        content={"name": "张三", "age":20},
        status_code=200,  # 可选
        headers={"X-Custom-Header":"custom-value"}  # 可选，自定义响应头
    )


@app.get("/download")
async def download():
    return FileResponse(
        path=r"E:\rag_project\images\4f19a5e1squirrel.exe",
        media_type="exe",
        headers={
            "Content-Disposition": "attachment; filename=4f19a5e1squirrel.exe"
        }
    )

@app.get("/hello")
async def hello(name: str = "游客"):
    html_content = f"""
    <html>
        <body>
            <h1>你好，{name}！</h1>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)


from fastapi.responses import PlainTextResponse

@app.get("/text")
async def get_text():
    return PlainTextResponse(content="这是纯文本响应", status_code=200)

from fastapi.responses import RedirectResponse

@app.get("/old-path")
async def redirect_old_path():
    # 重定向到 /new-path，状态码 307 表示临时重定向
    return RedirectResponse(url="/new-path", status_code=307)

@app.get("/new-path")
async def new_path():
    return {"message": "这是新接口"}


from fastapi.responses import Response
@app.get("/custom")
async def custom_response():
    # 返回二进制数据，指定自定义 MIME 类型
    return Response(
        content="<h1>纯文本</h1>",
        # media_type="text/plain",
        media_type="text/html",
        status_code=200)


#=========================================================
from fastapi import FastAPI

import uvicorn
from starlette.middleware.cors import CORSMiddleware


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# @app.get("/test_background")
# async def test_cors():
#     return {"message": "这是后端数据", "status": "success"}


import time
from fastapi import FastAPI, BackgroundTasks

def test_task(n):
    print("执行后台任务")
    while n > 0:
        print("我爱学习大模型")
        n -= 1
        time.sleep(1)

@app.get("/test_background")
def test_background(background_task:BackgroundTasks):
    background_task.add_task(test_task, 10)
    return {"message":"我特别爱学AI"}

if __name__ == "__main__":
    uvicorn.run(
        app=app,
        host="0.0.0.0",
        port=8001,
    )
