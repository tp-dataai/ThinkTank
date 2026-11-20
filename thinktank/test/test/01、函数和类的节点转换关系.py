from langgraph.graph import StateGraph


def a(state):
    pass

builder = StateGraph()
builder.add_node("a",a)

# 1、todo 函数节点是不是我们自己调的？
# 如果是自己调，那么你就得自己加括号,我们没写过但是最终函数执行了，所以别人帮我调了
# 别人是graph对象，函数谁调用谁负责传参 graph会把a加括号调用


# 2、todo 如果我们在函数节点添加的时候给的是一个对象
# 那么graph后期也会把对象加括号当函数用 graph会在实例对象后面加括号 当函数用
# __call__

class A:
    def __call__(self, *args, **kwargs):
        pass

class B:
    def __call__(self, *args, **kwargs):
        pass

builder.add_node("a",A())
builder.add_node("b",B())

#3、todo 每个节点后期都写一个类，那么每个节点都要在类当中写一个call,那么call太多了
# 所以我们把所有的节点类当中call抽离出来，弄一个父类（基类）写到基类当中
class Base:
    def __call__(self, *args, **kwargs):
        pass

class A(Base):
    pass

class B(Base):
    pass
builder.add_node("a",A())
builder.add_node("b",B())


#4、todo 发现每个子类对象当函数用的时候都会调到父类的call,而每个子类功能是不一样的
# 此时同一个call又执行的同一个功能（出问题）,所以开始把父类转换成抽象类
# 抽象类必须要有一个抽象方法，抽象类不能实例化对象，抽象类相当于是定义了一套规范
# 类似java的接口，而且抽象方法一般父类不实现，是让子类去继承重写实现的
from abc import ABC,abstractmethod
class Base(ABC):
    def __call__(self, *args, **kwargs):
        # 统一
        self.process()

    @abstractmethod
    def process(self):
        pass


class A(Base):
    def process(self):
        pass

class B(Base):
    def process(self):
        pass

builder.add_node("a",A())
builder.add_node("b",B())
















