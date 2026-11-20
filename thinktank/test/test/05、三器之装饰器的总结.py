# 装饰器 迭代器 生成器

# 高阶函数：函数的参数或者返回值是另外一个函数的函数

# 闭包是是什么
# 1、闭包是内部函数引用外部函数局部变量的引用关系，通过调用外部函数拿到内部函数的返回值
#打印 f.__closure__可以看到
# 闭包的产生条件
# 1、内外函数嵌套 2、内部函数引用外部函数局部变量 3、外部函数返回内部函数 外部函数要调用


# 闭包的作用（为什么）
# 1、延长外部函数局部变量的生命周期
# 2、封装私有数据（可以让外部间接操作函数内部变量）
# 3、装饰器的基础

# 闭包怎么玩
# fn()每调用一次都是一个全新的执行上下文，由这个执行上下文所产生的fn2函数也都是全新的
# 每一次fn()执行的执行上下文和由这一次执行所产生的fn2函数数据形成独立的闭包机制
# 以后调用不同的闭包机制当中的fn2函数数据，更改的是当前闭包机制的fn执行上下文当中的变量
# 不同的闭包机制互不干扰

def fn():
    a = 100
    def fn2():
        nonlocal a
        a += 1
        print(a)
    return fn2


#闭包的缺点
#闭包机制无法自动销毁，会产生内存泄漏（销毁不了），如果滥用则内存溢出（满了）

#如何解决
# 手动销毁 闭包使用完成让全局变量不再指向内部函数即可
f = None
f1 = None

#以后最佳实践： 不要自己随便定义闭包，能不用就别用，效率低

#在哪用过（项目当中）
# todo 装饰器
# @classmethod
# @abstructmethod

# 是什么
# 装饰器的本质要么就是闭包函数要么就是一个类

#为什么
#装饰器是可以让一个函数功能更加强大，而且不改变原函数的代码

#怎么玩
# 三种定义方式 普通装饰器  带参装饰器 类装饰器
# 一种使用方式 @xxxx   xxx可能是装饰器函数（闭包）也可能是装饰器类（不能说闭包）


# todo  多层装饰器的使用及装饰器是什么时候执行的，顺序是怎么样的？
# import time
# def loggerdecorator(func):
#     print("我爱你杨幂")
#     def wrapper(*args, **kwargs):
#         print(f"函数的入参信息是{args}")
#         result = func(*args, **kwargs)
#         print(f"函数的返回值是{result}")
#         return result
#     return wrapper
#
#
# def timerdecorator(func):
#     print("我爱你赵丽颖")
#     def wrapper(*args, **kwargs):
#         start_time = time.time()
#         result = func(*args, **kwargs)
#         end_time = time.time()
#         print(f"函数执行的耗时是{end_time - start_time}")
#         return result
#     return wrapper
#
#
# # 装饰器是什么时候执行的？
# # 原函数在定义的时候，装饰器就执行了
#
# # 装饰器执行的顺序是什么
# # 从下往上，离函数越近越先走
#
# @loggerdecorator
# @timerdecorator
# def add(a,b):
#     return a+b
#
#
# print(add(10, 20))


# todo 修改原函数的元数据
# from functools import wraps
# def loggerdecorator(func):
#     print("我爱你杨幂")
#     @wraps(func)  #帮你把元数据恢复
#     def wrapper(*args, **kwargs):
#         print(f"函数的入参信息是{args}")
#         result = func(*args, **kwargs)
#         print(f"函数的返回值是{result}")
#         return result
#     return wrapper
#
# @loggerdecorator
# def add(a,b):
#     return a+b
#
#
# print(add(1, 2))
# # 元数据 我们可以这样打印
# # 不用装饰器 原函数名字是add
# # 用了装饰器，原函数再去打印的时候名字是wrapper 其实本身就应该是wrapper，但是对于客户来说元数据和调用的函数数据不匹配
# # 所以我们可以强制把元数据再给改回来，但是功能不变
# print(add.__name__)

#装饰器的4个案例
#日志  计时  校验  缓存
# 代码后面最好敲敲


# 通过网盘分享的文件：深圳0331python基础
# 链接: https://pan.baidu.com/s/1KK8yOx6QEiF_KhXoXntPQA?pwd=fnb6 提取码: fnb6


#装饰器
#是什么 为什么 怎么做 在哪用过