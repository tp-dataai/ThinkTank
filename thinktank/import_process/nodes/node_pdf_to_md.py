import time
import shutil
import zipfile
from pathlib import Path

from thinktank.import_process.base import NodeBase
from thinktank.import_process.state import ImportGraphState
from thinktank.tool.logger import logger
from thinktank.config.config import MineruConfig


class NodePDFToMD(NodeBase):
    """
    PDF 转 MD 节点
    """

    name = "node_pdf_to_md"

    def process(self, state: ImportGraphState):

        # 1、就是需要从 state 中拿到文件的路径
        local_dir_obj, pdf_path, pdf_path_obj = self.check_pdf_file(state)

        # 2、将文件上传到 Mineru ，就是发送http请求
        batch_id = self.upload_pdf_file(pdf_path, pdf_path_obj)
        
        # 3、轮询获取 mineru 解析的 md 的压缩包 url 地址
        url = self.get_md_zip_url(batch_id)
        
        # 4、根据地址，下载 zip 存到本地 ，
        zip_path_obj = self.load_zip(local_dir_obj, pdf_path_obj, url)

        # 5 、解压zip 到指定目录， 
        unzip_file_path_obj = self.unzip(local_dir_obj,pdf_path_obj,zip_path_obj)

        # 6、修改 full.md 的名字，保存md 的内容；
        md_content,new_file_path_obj  = self.rename(pdf_path_obj, unzip_file_path_obj)
        print("new_file_path_obj =" ,new_file_path_obj)
        # 返回值 
        return {
            "md_path":str(new_file_path_obj),
            "md_content":md_content
        }

    def check_pdf_file(self,state):

        # 获取到文件的地址
        local_dir = state.get("local_dir")
        pdf_path = state.get("pdf_path")

        if not pdf_path:
            logger.error("pdf文件路径不能为空")
            raise Exception("pdf文件路径不能为空")

        pdf_path_obj = Path(pdf_path)
        if not pdf_path_obj.exists():
            logger.error("pdf文件不存在")
            raise Exception("pdf文件不存在")

        if not local_dir:
            logger.error("输出目录路径不能为空")
            raise ValueError("输出目录路径不能为空")

        # 根据目录路径得到一个 本地目录对象。
        local_dir_obj = Path(local_dir)
        if not local_dir_obj.exists():
            # parents=True 代表创建的时候递归创建 exist_ok=True 即使存在也不报错
            local_dir_obj.mkdir(parents=True, exist_ok=True)

        return local_dir_obj, pdf_path, pdf_path_obj

    # 当下这个代码还是存在一些问题。
    # 特别是对于多文件的内容，以及多文件上传的对应问题。

    def upload_pdf_file(self, pdf_path, pdf_path_obj):

        import requests  # 发请求的工具库
        token = MineruConfig.mineru_token
        url = "https://mineru.net/api/v4/file-urls/batch"
        header = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        data = {
            "files": [
                # # data_id 是 MinerU 用来标识每个文件的，后续查询结果时会用到。
                {"name": f"{pdf_path_obj.name}", "data_id": "abcd"}
            ],
            "model_version": "vlm"
        }

        file_path = [pdf_path]   # 多个 pdf 的存储路径

        # 发送http请求，获取响应
        response = requests.post(url, headers=header, json=data)
        if response.status_code != 200:
            logger.error("上传文件请求出错")
            raise Exception("上传文件请求出错")

        # 请求成功获取响应当中的数据
        result = response.json()
        if result["code"] != 0:
            logger.error("上传文件请求的数据出错")
            raise Exception("上传文件请求的数据出错")

        # 其实后面我们还得看考虑一层判断，判断数据拿到的是不是我要的数据，这个数据可能是实时数据（随时在变化的数据）
        # 对每个请求都生成一个 batch_id
        batch_id = result["data"]["batch_id"]  # 数据对了就去获取数据
        # file_urls 不是文件内容，也不是本地路径，而是远程文件的 HTTP(S) 地址。
        # 你拿到它之后，通常要再发一次 HTTP 请求去下载，才能得到真正的文件字节或本地文件。
        # ----------------------------------------------------------------
        """
        url 批量上传解析
            接口说明
            适用于通过 API 批量创建提取任务的场景 注意：
            单次申请链接不能超过 50 个
            文件大小不能超过 200MB,文件页数不超出 200 页
            因网络限制,github、aws 等国外 URL 会请求超时
            header头中需要包含 Authorization 字段，格式为 Bearer + 空格 + Token
        存在的问题：
            (2)、data_id 的赋值问题。对于多文件处理的情况下。应该如何去更改？
            (3)、
        """
        urls = result["data"]["file_urls"]        # 文件上传地址
        for i in range(0, len(urls)):             # 文件上传地址的数量
            with open(file_path[i], 'rb') as f:   # 'rb':只能写 bytes
                res_upload = requests.put(urls[i], data=f)
                if res_upload.status_code == 200:
                    logger.info(f"{urls[i]}上传成功")
                else:
                    logger.warning(f"{urls[i]}上传失败")
        # ----------------------------------------------------------------
        return batch_id

    def get_md_zip_url(self, batch_id):
        import requests
        token = MineruConfig.mineru_token
        api_url = f"https://mineru.net/api/v4/extract-results/batch/{batch_id}"
        header = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }


        # 2. 时间控制参数
        timeout_seconds = 600  # 设定最长等待时间为 10 分钟
        start_time = time.time()
        # 3. 开始轮询
        while True:
            # 判断是否整体超时
            if time.time() - start_time > timeout_seconds:
                raise TimeoutError(f"MinerU 解析超时（超过 {timeout_seconds} 秒）")

            try:
                res = requests.get(api_url, headers=header, timeout=10)
                if res.status_code != 200:
                    logger.warning(f"请求失败，状态码: {res.status_code}，2秒后重试...")
                    time.sleep(2)
                    continue

                result = res.json()
                if result.get("code") != 0:
                    logger.warning(f"接口返回错误: {result.get('msg')}，2秒后重试...")
                    time.sleep(2)
                    continue

                # 提取当前状态
                data = result.get("data", {})
                extract_results = data.get("extract_result", [])
                if not extract_results:
                    logger.info("未获取到解析结果列表，等待中...")
                    time.sleep(3)
                    continue

                task_info = extract_results[0]
                state = task_info.get("state")

                # 4. 核心状态机判断
                if state == "done":
                    logger.info("MinerU 解析完成！准备获取下载链接。")
                    download_url = task_info.get("full_zip_url")
                    if not download_url:
                        raise ValueError("解析状态为 done，但未获取到 full_zip_url！")
                    return download_url

                elif state == "failed":
                    err_msg = task_info.get("err_msg", "未知错误")
                    logger.error(f"MinerU 解析失败: {err_msg}")
                    # 遇到 failed 直接抛出异常，绝不能死循环！
                    raise RuntimeError(f"MinerU 解析失败: {err_msg}")

                elif state in ["waiting-file", "pending", "running", "converting"]:
                    # 正常流转中，打印日志并继续等待
                    logger.info(f"当前状态: {state}，等待中...")
                    time.sleep(3)
                    # 注意：这里绝对不要写 break！
                    continue

                else:
                    logger.warning(f"出现未知状态: {state}，等待中...")
                    time.sleep(3)
                    continue

            except requests.RequestException as e:
                # 只有网络异常才重试
                logger.warning(f"网络请求异常: {e}，5秒后重试...")
                time.sleep(5)
                continue
            # 注意：不再使用裸 except，让你自己写错的代码或者 failed 的报错能正常抛出来
            

    # 发送请求去下载zip文件
    def load_zip(self,local_dir_obj, pdf_path_obj, url):
        import requests
        response = requests.get(url)

        if response.status_code != 200:
            logger.error("下载md的zip压缩包的请求失败")
            raise Exception("下载md的zip压缩包的请求失败")

        # 将下载下来的内容存储在内存中。
        zip_content = response.content
        # zip 想要存储的目录
        zip_path_obj = local_dir_obj / f"{pdf_path_obj.name}.zip"
        with open(zip_path_obj, "wb") as f:
            f.write(zip_content)
        return zip_path_obj
    
    # 将文件解压到对应文件目录中
    def unzip(self,local_dir_obj,pdf_path_obj, zip_path_obj):
        # 先得到解压后的路径

        unzip_file_path_obj = local_dir_obj / f"{pdf_path_obj.stem}"

        if unzip_file_path_obj.exists():
            shutil.rmtree(unzip_file_path_obj)
        unzip_file_path_obj.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_path_obj) as zf:
            zf.extractall(unzip_file_path_obj)

        # 将解压后的目录对象返回，用于后续更改文件名称
        return unzip_file_path_obj
        
    # 重新修改 md 文件的名称。
    def rename(self, pdf_path_obj, unzip_file_path_obj):
        # todo 从这个位置找到 full.md 改名改成我们要的文件名。
        # ==========================================================================================
        old_file_path_obj = unzip_file_path_obj / "full.md"  # 找到源文件的Path对象
        new_file_path_obj = old_file_path_obj.with_name(f"{pdf_path_obj.stem}.md")  # 改名没落盘
        old_file_path_obj.rename(new_file_path_obj)  # 真正的落盘

        print("old_file_path_obj=",old_file_path_obj)
        print("new_file_path_obj=",new_file_path_obj)
        print("old_file_path_obj=",old_file_path_obj)

        # 这里其实拿这个内容没必要，只是state当中需要这个中间数据，我们只是存一份罢了
        with open(new_file_path_obj, "r", encoding="utf-8") as f:
            md_content = f.read()
        print(new_file_path_obj)
        return md_content, new_file_path_obj

        


if __name__ == '__main__':
    node = NodePDFToMD()

    init_state = {
        "pdf_path":r"C:\Users\Administrator\Desktop\test1\hak180产品安全手册.pdf" #上传给mineru解析的文件路径
    }

    result = node(init_state)
    # logger.info(result)