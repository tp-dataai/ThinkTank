import uvicorn
import uuid
import os
import shutil
from fastapi import FastAPI, Path, Query, Body, Depends, Request, UploadFile, File
from pydantic import BaseModel, Field

app = FastAPI(
    title="第一个FastAPI应用",
    version="0.0.1",
    description="这个接口用来测试第一个FastAPI应用。",
)

@app.get("/")
def first_fastapi():
    return "这是第一个FastAPI应用~~"

# 路径参数案例
@app.get("/testpath/{id}/{name}/{gender}")
def testpath(
    id:int,
    name:str = Path(description="姓名"),
    gender:str = Path(description="性别")
):
    return {"id":id, "name":name, "gender":gender}


@app.get("/testquery")
def testquery(
    id:int,             # 必须要传
    height:float = 170,
    name:str = Query(...,description="姓名"),
    gender:str = Query(description="性别", default="female"),
):
    return {"id":id, "height":height, "name":name, "gender":gender}

# class User(BaseModel):
#     username: str = Field(title="用户名", description="用户名")
#     age: int = Field(title="年龄", description="年龄",default=18)

# @app.post("/testbody")
# def testbody(user:User):
#     return user

###############################################3
# # 第一种
# class User(BaseModel):
#     username:str = Field(title="用户名", description="用户名")
#     password:str = Field(..., title="密码", description="密码")

# @app.post("/testmixed/{id}")
# def testmined(
#     id:int = Path(description="用户ID"),
#     user:User = Body(..., description="用户信息"),
#     name:str = Query(...,description="用户名"),
#     age:int = Query(description="年龄", default=18)
# ):
#     return {"id":id, "name":name, "user":user, "age":age}

#===============================================
# 第二种方式：
class User(BaseModel):
    username: str = Field(title="用户名", description="用户名")
    password: str = Field(..., title="密码", description="密码")

# 路径参数和查询参数的处理方式
class Student:
    def __init__(self, id:int, name:str, age:int = 18):
        self.name = name
        self.age = age
        self.id = id

@app.post("/testmixed2/{id}")
def testmixed2(
    user:User = Body(..., description="用户信息"),
    student:Student = Depends(Student)
):
    return {"id":student.id, "name":student.name, "user":user, "age":student.age}

#=================================
# 使用request 来接受整个请求头的内容
@app.get("/testheader")
def testheader(request:Request):
    token = request.headers.get("token")
    return {"token":token}

#================================================
# 文件上传
@app.post("/testupload")
def testupload(file:UploadFile):
    print(file.filename)
    print(file.size)
    print(file.content_type)
    print(file.file)
    print(file.headers)

    file_name = str(uuid.uuid4())[:8] + file.filename  # type:ignore
    dir_path = "./images"
    if not os.path.exists(dir_path):
        os.mkdir(dir_path)
    print("dir_path=",dir_path)
    fs = open(f"./{dir_path}/{file_name}", "wb")  # 通过二进制的方式打开这个文件

    # 流式读取数据 (shutil)
    shutil.copyfileobj(file.file, fs, length=1024*1024)
    return {"filename":file.filename}

if __name__ == "__main__":
    uvicorn.run(
        app=app,
        host="0.0.0.0",
        port=8001,
    )
