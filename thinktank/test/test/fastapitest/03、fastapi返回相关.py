import uvicorn
from fastapi import FastAPI, Body
from pydantic import BaseModel, Field
from starlette.responses import JSONResponse, FileResponse

app = FastAPI() #创建的fastapi应用对象，这些参数都是为了在接口文档上可以看到

#todo 1、fastapi返回json
@app.get("/returnjson")
def returnjson():
    # return {"msg":"ok"} #这样的写法其实是个简写，完全等价于下面写法
    return JSONResponse(
        content={"msg":"ok"},
        status_code=200,
        media_type="application/json",
    )

class User(BaseModel):
    name: str = Field(...,description="用户名")
    age: int = Field(...,description="用户年龄")

@app.post("/returnjson2")
def returnjson2(user:User = Body(...,description="请求体参数")):
    # return user
    return JSONResponse(
        content=user,
        status_code=200,
        media_type="application/json",
    )

#json返回的时候有简写，那么后期就很少看到写下面的那种方式


# todo 2 返回文件（前端下载文件）
@app.get("/download")
def download():
    #响应头设置的目的是为了返回给浏览器让浏览器看到之后怎么操作
    #响应头是为了指挥浏览器干活
    return FileResponse(
        path="./image/7dca47c6-mylove09.png",
        media_type="image/png",
        status_code=200,
        headers={
            "Content-Disposition": "attachment; filename=mylove09.png"
        }
    )


# todo 3 返回html (了解)
from fastapi.responses import HTMLResponse
@app.get("/hello")
def hello(name: str = "游客"):
    html_content = f"""
    <html>
        <body>
            <h1>你好，{name}！</h1>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)

# todo 4 返回纯文本 (了解)
from fastapi.responses import PlainTextResponse
@app.get("/text")
async def get_text():
    return PlainTextResponse(content="<h1>这是纯文本响应</h1>", status_code=200)


# todo 5 返回重定向（了解）
from fastapi.responses import RedirectResponse
@app.get("/old-path")
async def redirect_old_path():
    # 重定向到 /new-path，状态码 307 表示临时重定向
    return RedirectResponse(url="/new-path", status_code=307)

@app.get("/new-path")
async def new_path():
    return {"message": "这是新接口"}



# todo 6 返回自定义的response(了解)
from fastapi.responses import Response

@app.get("/custom")
async def custom_response():
    # 返回二进制数据，指定自定义 MIME 类型
    return Response(
        content="<h1>纯文本</h1>",
        media_type="text/plain",
        # media_type="text/html",
        status_code=200)









if __name__ == '__main__':
    uvicorn.run(
        app=app,
        host="0.0.0.0",
        port=8000,
    )