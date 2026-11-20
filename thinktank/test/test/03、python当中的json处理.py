# 是什么 为什么 怎么做 项目里面哪里用到过

# json
#todo 是什么
#json是一种数据格式，专门用来做前后端交互的数据格式，本质上一个字符串 所以很多人也叫json为json串、





#todo 为什么
# 岗位的变迁
# 大前端时代：H5和css3+nodejs出现标志进入大前端时代，前后端才有前后端分离项目，才有前端岗位，才出现前端工程师
# 没进入大前端时代之前，那时候所有的前端页面最后搭建好都要交给后端，后端拿着这些页面做模版，后端人员需要从数据库拿到数据
# 自己再把这些数据整理好，渲染到页面上，（那时候的后端人员一定是全栈）   jsp  spring


# 现在前后端如果要交互都是分离的，前后端代码 部署都是分离的
# 前端要发请求给后端，后端要接收请求，主要是为了拿到前端传递过来的数据
# 后端给前端反响应，目的也是让前端可以拿到后端的数据

# 前端传递数据用的是前端语言的代码，前端的数据类型和后端的代码数据类型不一样
# 前端和python后端进行交互
# 前端传递数据用的是前端的数据类型，python就算能接受的到，也不认识
# 老早前没有json的时候，当时都使用xml文件去传递
# xml：可扩展标记语言，是html的爹，他们用的都是各种标签
# <star>
#     <name>杨幂</name>
#     <age>18</age>
#     <gender>female</gender>
# </star>
# xml作为前后端交互的数据格式，会很麻烦：
#   前后端根本不需要标签的东西，二需要的是标签中间的数据，此时就要解析
#   前后端交互使用网络，xml文件一般比较大，占带宽，效率不高

# xml因为上面的原因导致后期必然被淘汰，现在的xml主要就是用来做配置文件

# json应运而生
#json是一个字符串，各大语言当中字符串都是一样的

#json其实最终扮演的就是中间人
# 前端给后端传递复杂数据，先把前端的数据类型转化为json串（序列化）
# 递给后端，后端拿到json串是可以认识的，后端有专用工具会把json转化为后端数据类型去操作（反序列化）

#后端给前端返回数据，先把后端语言的数据类型转化为json串（序列化）
#再把数据返回给前端，前端拿到json字符串，也有自己的工具把json串反序列化为前端自己的数据类型去操作
#json是字符串，很轻量，不占带宽效率贼高


#todo 怎么玩
import json
# json.dumps()  #序列化 把python数据转化为json串
# json.loads()  #反序列化 把json串转化python的数据类型
#
# json.dump()   #序列化  把python数据转化为json串并且写入到文件（.json）
# json.load()   #反序列化  把.json文件当中的json数据读取出来并转化为python数据类型

#作为后端我想把这个字典返回给前端
#和数据打交道的一对
dict1 = {
    "name":"yangmi",
    "age":18,
    "gender":"female"
}
#先把python的字段格式转化为json串
dict1_json = json.dumps(dict1)
print(dict1,type(dict1))
print(dict1_json,type(dict1_json))

#然后就可以把这个json串作为响应的数据返回给前端
# 前端就可以使用js的工具对这个json串进行反序列化，成为前端的对象去处理
# JSON.stringify() #序列化工具
# JSON.parse() #反序列化工具




#前端假设给我们传了一个json 就是上面咱们打印的dict1_json

#需要修改前端传递的数据，我们就得先反序列化转化为python的数据再去操作
json_dict1 = json.loads(dict1_json)
print(json_dict1,type(json_dict1))

json_dict1["age"] = 40
print(json_dict1,type(json_dict1))





#和文件打交道的一对
#把数据序列化并写入json文件
dict2 = {
    "name":"赵丽颖",
    "age":18,
}
with open("test.json","w",encoding="utf-8") as f:
    json.dump(dict2,f)

# 从json文件读取json并反序列化
with open("test.json","r",encoding="utf-8") as f:
    res = json.load(f)

print(res,type(res))











# dict1 = {
#     "a":100,
#     "b":200
# }
# dict2 = {
#     **dict1,
#     "a":50
# }
# print(dict2)













































