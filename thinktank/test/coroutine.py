import asyncio
import time

# 这是一个协程函数
async def get_url(url):
    print("发请求前")
    await asyncio.sleep(2)
    print("请求后")
    return 200

# 协程函数的调用需要放到另一个协程函数中
async def main(urls):
    # 通过 列表推导式来创建协程对象,这个时候只是初始化，并没有执行协程函数。
    c_list = [ get_url(url) for url in urls]

    # 并发执行多个协程任务方式1
    # 将每个协程对象，包装成并发任务
    t_list = [ asyncio.create_task(c) for c in c_list ]

    # 并发执行多个协程任务方式2：
    # 通过 gather 并发执行协程任务，收集并发执行完成后的结果组成列表
    result = await asyncio.gather(*t_list)
    return result

if __name__ == "__main__":
    urls = ["http://www.baidu.com","http://www.qq.com","http://www.jd.com"]
    result = asyncio.run(main(urls))
    print(result)