import pathlib
import shutil
import uuid

import uvicorn
from fastapi import FastAPI, Path, Query, Body, Depends, File, UploadFile
from pydantic import BaseModel, Field
from starlette.requests import Request

from atguigu.tool.minio_client_tool import get_minio_client

app = FastAPI()
#参数：路径参数 查询参数 请求体参数
#todo 1 接收路径参数
#1、前端怎么传
#2、后端怎么接
#3、后端怎么校验
#如果是路径参数，都必须传，不能可传可不传
#路经参数是占路径的一部分
@app.get("/testpath/{id}/{name}")
def testpath(
    # id: int = 100, #路径参数不能这么干，如果干了这个就不再是路径参数而是一个普通的形参
    id: int = Path(..., gt=0),
    name: str = Path(...,description="用户名字",min_length=1,max_length=20),
):
    return {"msg":"ok","id":id, "name":name}


#todo 2 接收查询参数
#1、前端怎么传
#2、后端怎么接
#3、后端怎么校验
#校验的时候...和default是互斥的，不能同时出现
@app.get("/testquery")
def testquery(
    name: str = Query(...,description="用户名字"),
    # age: int = 100 #这里可以做可传可不传，因为不影响路径，虽然我们也是一个普通的形参，就算可以也不会这么写
    age: int = Query(default=18,description="年龄",gt=0,lt=100),
):
    return {"msg":"ok","name":name, "age":age}


#todo 3、接收请求体参数
#1、前端怎么传
#2、后端怎么接
#3、后端怎么校验
# 请求体参数是在请求报文的体里面传过来的，请求体并不是每种请求方式都有
#只要是请求体参数，一般都是post和put请求才有请求体，get和delete请求一般没有请求体
#浏览器默认地址栏输入回车是get请求，那么我们要测试post请求，就得借助工具要不就得写前端代码
#BaseModel是pydantic模块当中给的，python系统包，通常用来做数据校验。

#请求参数校验分为两步
#1、整体校验 Body
#2、内容校验 pydantic

class BodyParams(BaseModel):
    name: str = Field(...,description="用户名字")
    age: int = Field(default=18,description="用户年龄")

@app.post("/testbody")
def testbody(
        body_params: BodyParams = Body(...,description="请求体参数")
):
    print(body_params,type(body_params))
    return {"msg":"ok","name":body_params.name, "age":body_params.age}


#todo 4、接收综合参数
#1、前端怎么传
#2、后端怎么接
#3、后端怎么校验
class User(BaseModel):
    username:str = Field(...,description="账户名")
    password:str = Field(...,description="密码")

# @app.post("/testmix/{id}")
# def testmix(
#     id: int = Path(..., gt=0,description="用户id"),
#     name: str = Query(...,description="用户名字"),
#     age: int = Query(default=18,description="用户年龄"),
#     user: User = Body(...,description="用户账号信息")
# ):
#     return {"msg":'ok',"id":id, "name":name, "age":age, "user":user}

#todo 5、接收综合参数
#把路径参数和查询参数都作为键值对参数，使用一个普通类+fastapi里面的依赖注入去接收
#请求体参数还是之前的
#1、前端怎么传
#2、后端怎么接

class UserInfo:
    def __init__(self, id,name,age):
        self.id = id
        self.name = name
        self.age = age
#fastapi当中的依赖注入Depends，这个类里面需要传递的是可以执行调用的数据类型
#fastapi在解析这个形参默认值的时候，通过Depends自动解析上下文当中的参数，实例化对应的类的对象
#Depends是我们调的，而传递给Depends的类或者函数不是我们调的
#注意：这个依赖注入只能在函数的形参默认值当中出现
@app.post("/testmix/{id}")
def testmix(
    user_info: UserInfo = Depends(UserInfo),
    user: User = Body(...,description="用户账号信息")
):
    return {"msg":'ok',"id":user_info.id, "name":user_info.name, "age":user_info.age, "user":user}


#todo 6、接收头信息
#前端发送过来的头信息就是键值对，fastapi会把请求的头信息放在一个对象当中request
@app.get("/testheader")
def testheader(request: Request):
    print(request.headers.get("token"))
    print(request.headers.get("host"))
    return {"msg":"ok"}


#todo 7、接收文件（前端上传文件）
#1、前端怎么传
#2、后端怎么接
#3、校验
@app.post("/upload")
def upload(
    file:UploadFile = File(...,description="上传的文件"),
):
    # print(file.file) #代表文件内容对象
    # print(file.filename)
    # print(file.content_type)
    # print(file.size)

    #1、暂存 把文件先暂存到后端服务器本地磁盘，也就是我们项目当中
    image_dir = pathlib.Path(__file__).parent / "image"
    if not image_dir.exists():
        image_dir.mkdir(parents=True,exist_ok=True)

    file_name =  str(uuid.uuid4())[:9] + file.filename

    image_path = image_dir / file_name
    with open(image_path, "wb") as f:
        # f.write(file.file.read())
        shutil.copyfileobj(file.file,f,1024*1024*10) #把给定的内容写到指定的文件，每次写的大小自己可以设定


    #2、转储 把暂存的文件存储到对象存储容器minio
    # minio_client = get_minio_client()
    # minio_client.fput_object()

    return {"msg":"ok"}











if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=8000)
