# def func():
#     print("aaaa")
#     yield 1
#     print("bbbb")
#     yield 2
#     print("cccc")
#     yield 3
#     print("dddd")
#     yield 4
#     print("eeee")
#     yield 5
#     print("ffff")
#     return 100
#     yield 6
#
# result = func()  #生成器函数调用的时候返回生成器，不看return,此时函数的代码还没走
# # print(result)
#
# print(next(result))
# print(next(result))
# print(next(result))
# print(next(result))
# print(next(result))
# print(next(result))



def numgenderator(n):
    num = 1
    step = 1
    while num <= n:
        value = yield num
        print(value)
        if value:
            step = value
        num += step

num_generator = numgenderator(100)
# next(num_generator) #==> num_generator.send(None)
print(num_generator.send(None))  #第一次没有发送值，目的是为了启动生成器的函数执行
print(num_generator.send(None))
print(num_generator.send(None))
print(num_generator.send(None))
print(num_generator.send(None))


# 我要改变步长
print(num_generator.send(2))

print(num_generator.send(None))
print(num_generator.send(None))
print(num_generator.send(None))

# 我要改步长
print(num_generator.send(1))


# 迭代器类和迭代器对象：
    # 迭代器是实现了迭代协议的类，通过这个类实例化的对象叫迭代器对象
    # 迭代协议要求类当中必须实现 __iter__  __next__    __iter__返回自身 __next__一般写的就是惰性生成逻辑
# 作用：惰性生成 节约内存

# 使用：以后不用


# 生成器函数  生成器对象
#生成器 是一个简易版的迭代器，用它实现惰性生成更加简便快捷
# 要想拿到一个生成器对象，必须先有一个生成器函数，生成器函数和普通函数的区别
# 生成器函数当中有yield关键字，生成器函数调用的时候不会执行代码，会立即返回生成器对象
# 生成器函数的代码，第一次调用next的时候才会执行代码


# 作用：惰性生成 节约内存

# 使用: 和迭代器一样都有两种用法：1、next(生成器对象) 2、循环遍历

# 在哪用过：
#     目前我们还没接触过
#  项目最后和前端对接我们学习sse,里面需要做流式输出到前端，就要用生成器（我们就得自己定义生成器）



















