# 18、同步和异步的概念
# 同步：
# 代码必须先执行完一个任务才能继续往下走，当使用同步的代码碰到阻塞的时候，也必须等待这个任务完成，才能走下一个
#
# 异步：
# 代码碰到同步的代码会一行一行去执行，当碰到阻塞的时候，这个任务我们会交给另外一个东西去帮忙管理（回调函数、事件循环），我们
# 就把这个耗时操作称作叫异步操作，这个任务如果有结果的话，我们会回头可以调用回调函数获取结果，也可以根据事件循环当中任务的就绪状态
# 来执行这个任务
#
# 异步思想对于我们自己的代码来说，我们是没有使用多进程和多线程的。因为多进程和多线程都操作系统调度，协程是程序员调度

# 19、协程（进程线程协程的结构）
# 什么是协程
# 协程（Co - routine），也可称为微线程，或非抢占式的多仕务子例程，一种用户态的上下文切换技术（通过一个线程实现代码块间的相互切换执行）。
# 在一个线程（协程）中，遇到io等待时间，线程可以利用这个等待时间去做其他事情。通过 “协作式调度” 实现并发，同一时刻仅一个协程执行，
# 切换由程序主动控制（无GIL影响）。

# 协程的特点
# 用户态调度：协程切换由Python程序控制（如yield 或await），无需操作系统介入，切换开销极小（仅保存函数上下文）。
# 协作式并发：协程执行到IO操作或主动挂起时（await），才会切换到其他协程，避免 “抢占式调度” 的开销。
# 单线程内并发：所有协程运行在同一线程中，内存共享且无需加锁（避免资源竞争），但需配合异步IO库使用。


# 协程是微线程
# 依赖于线程
# 协程是程序员自己控制调度的
# 在线程当中协程也是并发执行
# 没有受到GIL影响
# 效率极高
# 但是要配合异步库使用

# asyncio
# 模块（async / await 语法）异步IO库
# asyncio是Python
# 标准库中用于异步编程和并发任务管理的核心库。它的基础是事件循环，用来调度协程（coroutines），让它们能够非阻塞地并发执行。
# 这种编程模型在处理大量I / O密集型任务时非常高效，如网络操作、文件读写等。主要是控制协程的执行顺序
#
# 事件循环
# 管理所有协程任务的状态（就绪 / 运行 / 挂起）。
# 当协程挂起（如等待IO响应）时，切换到其他就绪协程。
# 事件完成后，唤醒对应的协程继续执行。
# 类似一个死循环遍历列表里面的任务，哪个可以执行哪个不可以执行，哪个可以执行就去执行
#
# asyncio的常用方法
# async 在函数定义前面代表创建一个协程函数，函数调用后会返回协程对象，而不是直接执行
# await 在协程函数中才能使用，用来等待其他异步操作的完成，也是切换协程任务执行的标志
# run
# 启动事件循环，传入主协程


# create_task()
# 把协程包装成并发任务，可以高并发执行这些任务



# gather # 开启并发的开关
# 并发执行多个协程任务，需要在run内部调用执行，run是启动事件循环，
# gather是把多个任务并发执行并收集结果（在已经启动的事件循环中）



# sleep
# 模拟异步任务中的延迟
#
# asyncio在处理并发I / O密集型任务时非常强大，使用它可以避免传统多线程编程中的锁和上下文切换开销。

# todo 代码
# 协程的使用
# async函数定义协程, 调用后返回的是协程对象
# async def fn():
#     print("我爱你杨幂")
#     return 100
# print(fn())


# 协程的使用run （单协程使用）
# 本质是开启事件循环，传入要开始循环的协程对象
# 协程必须先run开启事件循环
# import asyncio
# async def get_url(url):
#     print("发请求前")
#     await asyncio.sleep(2)
#     print("请求后")
#     return 200
#
#
# if __name__ == '__main__':
#     # result = asyncio.run(get_url("http://www.baidu.com"))
#     # print(result)
#     loop = asyncio.new_event_loop()
#     asyncio.set_event_loop(loop)
#     result = loop.run_until_complete(get_url("http://www.baidu.com"))
#     print(result)



# 4、携程异步实现两个任务（多协程）
import asyncio
import time

from langchain.chat_models import init_chat_model


async def get_url(url):
    print("发请求前")
    await asyncio.sleep(2)
    # time.sleep(2)
    print("请求后")
    return 200

async def main(urls):
    c_list = [get_url(url) for url in urls]  # 协程对象列表
    # 并发执行多个协程任务
    # t_list = [asyncio.create_task(c) for c in c_list]  # 把每个协程任务包装成并发任务

    # 通过gather并发执行并发协程任务 收集并发执行完成后的结果组成列表
    result = await asyncio.gather(*c_list)
    return result

if __name__ == '__main__':
    urls = ["http://www.baidu.com","http://www.qq.com","http://www.jd.com",]
    result = asyncio.run(main(urls))
    print(result)



# 5、await等待异步操作完成（切换协程）必须是在async函数内部才能使用
# await会暂停当前所在的协程任务，写在哪个async函数当中就是暂停谁
# await会让当前协程等待，
# 执行await后面的任务（直接去找事件循环当中的就绪任务），直到执行完成才会

# 总结：
# io密集型任务后期能用协程就协程，不能用就多线程
# cpu密集型只能是多进程

# llm = init_chat_model()
# llm.abatch()
# llm.ainvoke()

