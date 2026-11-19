# thinktank/test/fastapi/mount_static.py

from fastapi.staticfiles import StaticFiles
from pathlib import Path
from fastapi import FastAPI, Request

app = FastAPI()

# 当前文件目录
BASE_DIR = Path(r"E:\rag_project")
# print("当前文件目录：", BASE_DIR)
static_dir = BASE_DIR / "images"

# 挂载静态文件
# 第一个参数：所有以 /static 开头的请求都交给这个模块处理
# 第二个参数：指定静态文件的存放目录
# 第三个参数：给挂载点起个名字（路由的名字）
app.mount("/images", StaticFiles(directory=str(static_dir)), name="images")
# 用户访问：http://localhost:8001
#      ↓
# FastAPI 看到 "/static" 开头
#      ↓
# 交给 StaticFiles 处理
#      ↓
# StaticFiles 去 {static_dir} 找文件
#      ↓
# 返回给用户

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8001)