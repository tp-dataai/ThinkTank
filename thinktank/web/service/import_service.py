# 1. 创建应用
import time
from datetime import datetime
import shutil
import uuid
from pathlib import Path

import fastapi
import uvicorn
from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from starlette.middleware.cors import CORSMiddleware

from thinktank.config.config import MinioConfig
from thinktank.import_process.main_graph import MainGraphRunner
from thinktank.tool.json_format import json_format
from thinktank.tool.logger import logger
from thinktank.tool.get_minio_client import get_minio_client
from thinktank.tool.task_utils import update_task_status, TASK_STATUS_PROCESSING, TASK_STATUS_COMPLETED, \
    TASK_STATUS_FAILED, get_task_info, add_running_task, add_done_task, add_node_duration

app = FastAPI(
    title="掌柜智库-导入API",
    description="此文档是掌柜智库导入流程的API接口说明"
)

# 2. 跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许的源
    allow_credentials=True,  # 允许携带cookie
    allow_methods=["*"],  # 允许的请求方法
    allow_headers=["*"],  # 允许的请求头
)

#todo 上传文件的接口
#后台任务函数
def run_main_graph(task_id,local_dir,local_file_path):
    init_state = {
        "task_id": task_id,
        "local_dir": local_dir,
        "local_file_path": local_file_path,
    }
    try:
        #修改全局状态为处理中
        update_task_status(task_id,TASK_STATUS_PROCESSING)
        result = MainGraphRunner.create_and_run(init_state)
        logger.info(json_format(result))
        #修改全局状态为处理完成
        update_task_status(task_id, TASK_STATUS_COMPLETED)
    except:
        #处理失败
        update_task_status(task_id,TASK_STATUS_FAILED)
        raise

@app.post("/upload")
def upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...,description="上传的文件")
):
    # 这个是任务id 是后端在前端第一次发请求的时候造的，返回给前端，作用是后面做节点状态追踪
    task_id = str(uuid.uuid4()) 

    # 开始上传文件
    add_running_task(task_id, "upload_file")
    start_time = time.time()
    
    #暂存
    file_dir_obj = Path(rf"C:\Users\Administrator\Desktop\育儿\{datetime.now().strftime('%Y%m%d')}")
    if not file_dir_obj.exists():
        file_dir_obj.mkdir(parents=True,exist_ok=True)

    assert file.filename is not None, "文件名不能为空"
    file_path_obj = file_dir_obj / file.filename   
    with open(file_path_obj, "wb") as f:
        shutil.copyfileobj(file.file, f, 1024*1024*10)

    #转储
    minio_client = get_minio_client()
    minio_client.fput_object(
        bucket_name=MinioConfig.minio_bucket_name,
        object_name=f"upload_file/{datetime.now().strftime('%Y%m%d')}/{file.filename}",
        file_path=str(file_path_obj),
    )
    logger.info("上传文件结束")


    #结束上传文件
    add_done_task(task_id,"upload_file")
    end_time = time.time()
    add_node_duration(task_id,"upload_file",end_time-start_time)


    #看前端需要不需要网络url

    #启动后台任务开始执行import模块的main_graph
    background_tasks.add_task(run_main_graph,task_id,str(file_dir_obj),str(file_path_obj))
    return {"task_id": task_id}


#书写轮询接口返回实时状态数据
@app.get("/status/{task_id}")
def get_status(task_id: str = fastapi.Path(...,description="用户对应的任务id")):
    return get_task_info(task_id)

# 7. 启动项目
if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=8001)