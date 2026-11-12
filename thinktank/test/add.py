import time

# 这是一个用来计时的装饰器
def timer_decorator(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs) # 真正执行你的原函数
        end_time = time.time()
        print(f"函数执行耗时：{end_time - start_time} 秒")
        return result
    return wrapper

@timer_decorator   # add = timer_decorator(add)  --> add = wrapper
def add(a, b):
    time.sleep(1) # 假装干活了一秒
    return a + b

vale = add(10, 20) 
# 运行结果会自动打印出：“函数执行耗时：1.0005 秒”

print(vale)