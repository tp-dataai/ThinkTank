import re
import os
import time
import base64

from pathlib import Path
from langchain.chat_models import init_chat_model
from collections import deque
from datetime import datetime

from thinktank.import_process.base import NodeBase
from thinktank.tool.logger import logger
from thinktank.config.config import LLMConfig,MinioConfig
from thinktank.tool.get_minio_client import get_minio_client
from minio.deleteobjects import DeleteObject

class NodeMDImg(NodeBase):
    name = "node_md_img"
    
    def process(self, state):
        
        # 1、获取到初始化的内容，拿到 md 的文件内容。并根据 md 路径找到 图片的目录;
        image_dir_path_obj,image_names, md_content,md_path_obj = self.get_md_content(state)

        # 2、根据 md 的文件路径获取 图片的 文件路径。并且，当文件存在的情况下需要将文件的路径存储到一个列表中，
        #    方便后续遍历获取图片内容。不仅仅是文件的名称，还包括路径。
        #     还需要考虑防御性判断，如果 列表为空，说明目录虽然存在，但是目录中没有文件。
        # 通过图片的名称去循环遍历每张图片 在 md文档中去匹配，从而找到 图片在 md 文档中的位置。
        #    找到位置后，还需要将 图片的上下文内容也获取到，方便后续的处理。
        image_with_context_list = self.get_image_with_context_list(image_dir_path_obj, image_names, md_content)

        # 3、既然得到了图片以及图片的上下文信息，就需要将这些内容统一提供给大模型总结每张
        # 图片的摘要内容，并整理字典暂存到列表中。
        image_with_summary_list = self.get_image_with_summary_list(image_with_context_list)

        # 4、通过 minin 生成 url -> (1)、幂等性删除 (2) 上传拼接 url 整理字典暂存到列表
        """
            "image_name":image_with_context.get("image_name"),       # 文档名称   
            "image_path":str(image_with_context.get("image_path")),  # 文档路径
            "summary":result.content                                 # 文档摘要
            "url":url                                                # 文档在MinIO中的地址
        """
        image_with_summary_url_list = self.get_image_with_summary_url_list(image_with_summary_list, md_path_obj)

        # 5、将上传好的摘要和url 替换到内容当中。
        new_md_path_obj, md_content= self.replace_md_content(image_with_summary_url_list,md_content,md_path_obj)

        return {
            "md_path":str(new_md_path_obj),
            "md_content":md_content
        }

    def get_md_content(self, state):
        # 1.1 、先得到 md 文件路径并完成 防御性判断。
        md_path = state.get("md_path")
        if not md_path:
            logger.error("文件目录不能为空")
            raise Exception("文件目录不能为空")

        md_path_obj = Path(md_path)
        if not md_path_obj.exists():
            logger.error("文件不存在")
            raise Exception("文件不存在")

        with open(md_path_obj, "r", encoding="utf-8") as f:
            md_content = f.read()

        # 1.2 、根据得到的 md 的文档路径到拼接出 图片的目录
        image_dir_path_obj = md_path_obj.parent / "images"
        if not image_dir_path_obj.exists():
            logger.info("文件目录不存在")
            return{
                "md_content": md_content
            }          
        
        # 1.3 、文件目录存在的情况下，我们需要将 文件的名称处理成一个列表，并判断文件目录中是否存在文件
        image_names = os.listdir(image_dir_path_obj)
        if not image_names:
            logger.warning("md中不存在图片内容")
            return {
                "md_content":md_content
            }

        return image_dir_path_obj, image_names, md_content, md_path_obj

    def get_image_with_context_list(self, image_dir_path_obj, image_names, md_content):
        # 文件不一定都是图片，我们需要先确定 图片类型的数据，其后缀有哪些？
        IMAGE_EXTENSIONS = [".jpg",".jpeg",".png",".gif",".webp",".bmp",".tiff",".tif",".svg",".heic",".heif",".avif",".ico",".raw",".dng",".cr2",".nef",".psd"]

        # 定义一个列表变量，用来存储图片对应的上下文内容
        image_with_context_list = []

        for image_name in image_names:
            # 先判断文件是否是图片
            image_path_obj = image_dir_path_obj / image_name
            suffix = image_path_obj.suffix.lower()
            if not suffix in IMAGE_EXTENSIONS:
                logger.warning("md文件不能引用这种文件")
                continue

            # 如果是图片的情况下，我们就需要找到其在 md 文档中的位置
            # 先通过正则匹配内容。不代表一定能匹配到，因为这些图片在md中有可能是表格的形式
            pattern = re.compile((r"!\[.*?\]\(.*?" + re.escape(image_name) + r"\)"))
            match = pattern.search(md_content)

            if not match:
                logger.warning("图片在md文档中不存在")
                continue
            start, end = match.span()  # 获取到文件在md中的开始和结束位置。

            # 根据位置来抓取图片的上下文内容；
            pre_text = md_content[max(start - 100, 0) : start]
            post_text = md_content[end : min(end + 100, len(md_content))]


            image_with_context_list.append({
                "image_name":image_name,
                "image_path":str(image_path_obj),
                "pre_text":pre_text,
                "post_text":post_text,
            })

        return image_with_context_list
    
    # 我们想要做的事情是将 图片和上下文的内容，都输入给大模型，然后它输出每张图片的摘要内容 
    def get_image_with_summary_list(self, image_with_context_list):
        # 1、初始化一个大模型
        llm = init_chat_model(
            model=LLMConfig.vl_model,
            model_provider="openai",
            api_key=LLMConfig.openai_api_key,
            base_url=LLMConfig.openai_api_base,
            temperature=LLMConfig.llm_default_temperature
        )

        # 2、请求数量控制
        # 由于大模型在请求次数上面存在限制，因此我们需要做一个输入请求的控制，
        # 不能一下请求超过大模型能承载的最大请求数量。
        # 先创建 队列 还有就是一个 摘要列表 用来存储后续需要返回的内容；

        dq = deque(maxlen=30)
        image_with_summary_list = []

        for image_with_context in image_with_context_list:
            # 2.1、当前时间需要创建（用来进行对比）
            # 2.2 也就是当 dq 的数量小于 30 并且 这个时间与 dq 的第一个时间进行对比。
            #   如果两个时间差小于 60 ，那就需要等待，等待的时间就是 和60之间相差的秒数
            # 如果时间没问题的情况下就将其添加进入队列中。然后进行下一步。
            
            current_time = time.time()

            # 先忙盲清一波
            while dq and current_time - dq[0] > 60:
                dq.popleft()   # 左侧先弹出

            # 先判断dq中的内容是否是大于30。还是满的话就需要继续等待。
            
            if len(dq) > 30:
                # 那就需要判断还需要等多长时间。
                need_wait_time = 60 - (current_time - dq[0])

                if need_wait_time > 0:
                    time.sleep(need_wait_time)

                current_time = time.time()

                while dq and current_time - dq[0] > 60:
                    dq.popleft()   # 左侧先弹出

            dq.append(current_time)

            # 2.3 、调用大模型代码
            # 先对图片进行base64处理
            with open(image_with_context.get("image_path"), "rb") as f:
                base64_data = base64.b64encode(f.read()).decode("utf-8")

            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                # 我们要把图片传递给大模型：1、可以传递网络路径 2、可以传递编码后的图片内容（base64编码）
                                "url": f"data:image/jpeg;base64,{base64_data}"
                            },
                        },
                        {
                            "type": "text",
                            "text": f"""这是一张图片，图片上文部分为"{image_with_context.get("pre_text")}"，
                                     下文部分为"{image_with_context.get("post_text")}"，
                                     请用中文简要总结这张图片的摘要,字数在50字以内。"""
                        }
                    ],
                },
            ]

            # 调用大模型
            result = llm.invoke(input=messages)  # 我们需要的是大模型的返回结果中的 content

            # 得到大模型的返回结果，将大模型返回的摘要内容，一起和之前的内容进行封装
            # 成字典列表并返回

            image_with_summary_list.append({
                "image_name":image_with_context.get("image_name"),
                "image_path":str(image_with_context.get("image_path")),
                "summary":result.content
            })
        return image_with_summary_list

    # 将图片从本地上传到 minio 中存储，并返回 存储的位置等内容
    def get_image_with_summary_url_list(self, image_with_summary_list, md_path_obj):
        # 6.1 创建相关内容
        image_with_summary_url_list = []

        upload_dir = f"{MinioConfig.minio_img_dir} / {datetime.now().strftime('%Y%m%d')}/{md_path_obj.stem}"

        # 6.2 先删除目录
        # 要删除MinIO中的目录，需要先获取一个客户端
        minio_client = get_minio_client()

        old_file_generator = minio_client.list_objects(
            bucket_name=MinioConfig.minio_bucket_name,
            prefix=upload_dir,
            recursive=True
        )

        delete_object_list = [DeleteObject(item.object_name) for item in old_file_generator if item.object_name is not None]  
 
        # 真正的删除
        errors = minio_client.remove_objects(
            bucket_name=MinioConfig.minio_bucket_name,
            delete_object_list=delete_object_list  # 删除的老文件对象列表
        )

        # print(errors)
        for error in errors:
            logger.warning("error occurred when deleting object", error)

        # 6.3 将图片存储到 MinIO 中
        for image_with_summary in image_with_summary_list:
            # 将内容图片存储到 MinIO中。
            minio_client.fput_object(
                bucket_name=MinioConfig.minio_bucket_name,
                object_name= upload_dir + "/" + image_with_summary.get("image_name"),
                file_path=image_with_summary.get("image_path")
            )

            # 获取到每张图片的url的内容
            url = (f"http://"
                   f"{MinioConfig.minio_img_dir}"
                   f"/{MinioConfig.minio_bucket_name}"
                   f"/{upload_dir}"
                   f"/{image_with_summary.get("image_name")}"
            )

            # 6.4 获取到 MinIO中目录内容与之前的数据拼接成 字典列表再输出。
            image_with_summary_url_list.append({
                **image_with_summary,
                "url":url
            })

        return image_with_summary_url_list
    
    def replace_md_content(self, image_with_summary_url_list, md_content, md_path_obj):

        print("图片链接替换的位置存在问题：image_with_summary_url_list = ", image_with_summary_url_list)
        # 5.1 先替换内容
        for image_with_summary_url in image_with_summary_url_list:
            pattern = re.compile(r"!\[.*?\]\(.*?" + re.escape(image_with_summary_url["image_name"]) + r"\)")
            md_content = pattern.sub(
                lambda _: f"![{image_with_summary_url.get("summary")}]({image_with_summary_url.get("url")})",
                md_content
            )

        # 5.2 将内容写入新的文件路径中
        new_md_path_obj = md_path_obj.parent / f"{md_path_obj.stem}_new.md"

        with open(new_md_path_obj,"w",encoding="utf-8") as f:
            f.write(md_content)

        # 5.3 返回 新的文件路径和内容。

        return new_md_path_obj, md_content

if __name__ == "__main__":
    node_md_img = NodeMDImg()
    init_state = {
        # "md_content":md_content,
        "md_path":r"C:\Users\Administrator\Desktop\test1\万用表RS-12的使用\万用表RS-12的使用.md"
    }
    result = node_md_img(init_state)