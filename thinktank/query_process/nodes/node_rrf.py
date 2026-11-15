# thinktank/query_process/nodes/node_rrf.py

from thinktank.query_process.base import NodeBase
from thinktank.query_process.state import QueryGraphState
from thinktank.tool.logger import logger
from thinktank.tool.json_format import json_format

class NodeRrf(NodeBase):
    """
    节点功能：Reciprocal Rank Fusion
    将多路召回的结果（向量、HyDE、Web）进行加权融合排序。
    """

    # 覆盖基类的 name 属性，标识节点名称
    name: str = "node_rrf"

    def process(self, state: QueryGraphState):
        embedding_chunks = state.get("embedding_chunks")
        hyde_embedding_chunks = state.get("hyde_embedding_chunks")


        #rrf融合用自己的话说其实就是两件事：去重（两路同时拥有某一个chunk，
        # 最终融合到一路只有一个这个chunk,只是分数是两路的和）
        #除了去重以外，rrf还有一个功能就是把chunks进行筛选，最终只要10个
        #rrf融合条件 一般都是数据来源相同但是量纲不同

        #1、先对两路数据设置权重值
        weight_chunks = [
            (embedding_chunks,1),
            (hyde_embedding_chunks,1)
        ]

        # 2、遍历每一路获取到chunk根据公式计算排名分数，而不关心本身chunk当中的score
        rrf_dict = {}
        for chunks,weight in weight_chunks:
            for idx,chunk in enumerate(chunks,start=1):
                id = chunk.get("id")
                score = weight / (idx + 60)
                if id in rrf_dict:
                    #已经存在了，分数累加即可
                    rrf_dict[id]['score'] += score
                else:
                    # 使用新计算出来的倒数得分覆盖原来的向量检索分数
                    chunk["score"] = score     
                    rrf_dict[id] = chunk


        rrf_chunks = sorted(rrf_dict.values(),key=lambda x:x["score"],reverse=True)[:10]

        return {
            "rrf_chunks":rrf_chunks
        }

if __name__ == '__main__':
    init_state = {
        "embedding_chunks": [
            {
                "item_name": "RSPRORS-12数字万用表",
                "file_title": "万用表RS-12的使用",
                "content": "无标题\n\n![图片为RS PRO品牌数字万用表（型号RS-12，编号123-1939）的使用说明书封面，含红色“RS PRO”标志及产品信息。](http://192.168.77.77:9000/knowledge-base/upload-images/20261110/万用表RS-12的使用/a6c9fcfb41cfc997c0f88e35c06f34818e7b53d83d92fa3580257172c1c24ec7.jpg)\n\n使用说明书\n\nRS-12\n\n编号: 123-1939\n\n数字万用表",
                "title": "无标题",
                "id": 470357272956278341,
                "score": 0.7703771591186523,
                "source": "local"
            },
            {
                "item_name": "RSPRORS-12数字万用表",
                "file_title": "万用表RS-12的使用",
                "content": "无标题\n\n使用说明书\n\nRS-12\n\n编号: 123-1939\n\n数字万用表\n\n![图片为RS-12数字万用表使用说明书封面，含型号、编号、CE标志及安全手册标题，中央有“中文”椭圆标识。](http://192.168.77.77:9000/knowledge-base/upload-images/20261110/万用表RS-12的使用/16f1ae918c8905b9e4fc1d0c08fe8a9b55c34d69f4c1191f790bf08571419299.jpg)\n\nCE",
                "title": "无标题",
                "id": 470357272956278342,
                "score": 0.766277015209198,
                "source": "local"
            },
            {
                "item_name": "RSPRORS-12数字万用表",
                "file_title": "万用表RS-12的使用",
                "content": "## 安全标识\n\nCAUTION 表明此处可能出现危险电压，请避开以免导致仪表的损坏。\n\n![图片为电气安全警示标识，含“MAX”符号及接地标志，提示操作需参照说明书，并警告勿接500VAC/VDC电路，以防触电或设备损坏。](http://192.168.77.77:9000/knowledge-base/upload-images/20261110/万用表RS-12的使用/87ccf38edca64aa36a803d7091a6385340dace221ee3105f93037e3b4285d161.jpg)\n\n请勿连接到500VAC或VDC的电路上。",
                "title": "## 安全标识",
                "id": 470357272956278346,
                "score": 0.7491637468338013,
                "source": "local"
            },
            {
                "item_name": "RSPRORS-12数字万用表",
                "file_title": "万用表RS-12的使用",
                "content": "## 安全标识\n\n![图片为三角形感叹号安全警示标识，提示操作需参照说明书，并注意危险电压，以防人身伤害或仪表损坏。](http://192.168.77.77:9000/knowledge-base/upload-images/20261110/万用表RS-12的使用/2ec4f0e7e8b05c73503dc25db1ad0e65b99a06b2dea8d8a9525a1865c75095e0.jpg)\n\n表明此操作须参照说明书进行。\n\nWARNING 表明此处可能出现危险电压，请避开以免导致死亡或严重伤害。\n\nCAUTION 表明此处可能出现危险电压，请避开以免导致仪表的损坏。",
                "title": "## 安全标识",
                "id": 470357272956278345,
                "score": 0.7489747405052185,
                "source": "local"
            },
            {
                "item_name": "RSPRORS-12数字万用表",
                "file_title": "万用表RS-12的使用",
                "content": "## 直流电流测量\n\n![图片展示数字万用表测量电路电压的接线方式：黑表笔接负极，红表笔接正极，串联于含负载的回路中，显示屏读数为1.97V。](http://192.168.77.77:9000/knowledge-base/upload-images/20261110/万用表RS-12的使用/820246ff8d6f448489eb36a1297e028a8ca8ff17100aecb8aa38d685b069fc19.jpg)",
                "title": "## 直流电流测量",
                "id": 470357272956278366,
                "score": 0.7475560903549194,
                "source": "local"
            },
            {
                "item_name": "RSPRORS-12数字万用表",
                "file_title": "万用表RS-12的使用",
                "content": "## 操作指导\n",
                "title": "## 操作指导",
                "id": 470357272956278356,
                "score": 0.5731539130210876,
                "source": "local"
            },
            {
                "item_name": "RSPRORS-12数字万用表",
                "file_title": "万用表RS-12的使用",
                "content": "## 控制与端口\n\n1.LCD液晶显示\n\n2.功能选择转盘\n\n3.10A端口\n\n4.COM端口\n\n5.正极端口\n\n6.数据保持按键\n\n7.背光按键\n\n![该图为一款数字万用表结构图，标注了LCD显示、功能转盘、测试端口（10A、COM、正极）及数据保持、背光按键，并说明具双绝缘保护与蜂鸣指示功能。](http://192.168.77.77:9000/knowledge-base/upload-images/20261110/万用表RS-12的使用/d6946861c4592804bd8d7e75b58029565712d4dc58f855e374bf0fcf370c91dd.jpg)\n",
                "title": "## 控制与端口",
                "id": 470357272956278349,
                "score": 0.5289907455444336,
                "source": "local"
            },
            {
                "item_name": "RSPRORS-12数字万用表",
                "file_title": "万用表RS-12的使用",
                "content": "## 交流电压测量\n\n注意：正打开或关闭电源时不要进行此项测量，瞬间的强大电压将损坏仪表。\n\n![图片展示数字万用表测量电压的接线示意图：红黑表笔分别接V和COM端，接触被测点，显示屏显示读数。](http://192.168.77.77:9000/knowledge-base/upload-images/20261110/万用表RS-12的使用/84c37b209829d15820d5bbe76bbc98e1bf9eddc58bd9c983fc710cb2747d341b.jpg)\n\n1. 将功能转盘置于V AC的位置。\n\n2. 将黑色表笔插入负极COM端口，红色表笔插入正极V端口。",
                "title": "## 交流电压测量",
                "id": 470357272956278362,
                "score": 0.5157920122146606,
                "source": "local"
            },
            {
                "item_name": "RSPRORS-12数字万用表",
                "file_title": "万用表RS-12的使用",
                "content": "## 电池安装\n\n警告: 为防触电, 打开电池后盖前后，请勿操作仪表并把表笔与电源断开。\n\n1. 把表笔与仪表断开。\n\n2. 用螺丝刀拧开电池后盖上的螺母。\n\n3. 正确安装电池，正负极应一致。\n\n4. 盖上电池后盖并拧紧螺丝钉。\n\n警告: 为防触电,在电池后盖安装和固定之前，请勿操作仪表。\n\n注意: 若仪表出现工作不正常，请检测保险丝和电池是否完好以及是否放在正确的位置。\n",
                "title": "## 电池安装",
                "id": 470357272956278355,
                "score": 0.5147212743759155,
                "source": "local"
            },
            {
                "item_name": "RSPRORS-12数字万用表",
                "file_title": "万用表RS-12的使用",
                "content": "## 电阻测量\n\n![图片展示数字万用表测量电阻的接线示意图，表笔连接被测元件，显示屏显示“1.953”，下方标注“Ω”单位，配合文字说明电阻测量与短路蜂鸣测试操作要点。](http://192.168.77.77:9000/knowledge-base/upload-images/20261110/万用表RS-12的使用/3dce15efe5689c2d8c904dfbbb653eef71ce00b270bd08d47e3b474af2fb68a8.jpg)",
                "title": "## 电阻测量",
                "id": 470357272956278368,
                "score": 0.5094112157821655,
                "source": "local"
            }
        ],
        "hyde_embedding_chunks": [
            {
                "id": 470357272956278362,
                "item_name": "RSPRORS-12数字万用表",
                "file_title": "万用表RS-12的使用",
                "content": "## 交流电压测量\n\n注意：正打开或关闭电源时不要进行此项测量，瞬间的强大电压将损坏仪表。\n\n![图片展示数字万用表测量电压的接线示意图：红黑表笔分别接V和COM端，接触被测点，显示屏显示读数。](http://192.168.77.77:9000/knowledge-base/upload-images/20261110/万用表RS-12的使用/84c37b209829d15820d5bbe76bbc98e1bf9eddc58bd9c983fc710cb2747d341b.jpg)\n\n1. 将功能转盘置于V AC的位置。\n\n2. 将黑色表笔插入负极COM端口，红色表笔插入正极V端口。",
                "title": "## 交流电压测量",
                "score": 0.8625977635383606,
                "source": "local"
            },
            {
                "id": 470357272956278366,
                "item_name": "RSPRORS-12数字万用表",
                "file_title": "万用表RS-12的使用",
                "content": "## 直流电流测量\n\n![图片展示数字万用表测量电路电压的接线方式：黑表笔接负极，红表笔接正极，串联于含负载的回路中，显示屏读数为1.97V。](http://192.168.77.77:9000/knowledge-base/upload-images/20261110/万用表RS-12的使用/820246ff8d6f448489eb36a1297e028a8ca8ff17100aecb8aa38d685b069fc19.jpg)",
                "title": "## 直流电流测量",
                "score": 0.8558820486068726,
                "source": "local"
            },
            {
                "id": 470357272956278364,
                "item_name": "RSPRORS-12数字万用表",
                "file_title": "万用表RS-12的使用",
                "content": "## 直流电流测量\n\n注意：在10A情况下测量时间不能超过30秒，否则将可能损坏仪表或表笔。\n\n![图片展示数字万用表测量电压的接线方式（红黑表笔接被测元件两端），并附有电压读数说明及直流电流测量的操作步骤要点。](http://192.168.77.77:9000/knowledge-base/upload-images/20261110/万用表RS-12的使用/eb330b9b1b79716fc9feacd30808b4ed86c395ebaab24c29dec65d68060e10be.jpg)\n\n1. 将黑色表笔插入负极COM端口。",
                "title": "## 直流电流测量",
                "score": 0.8506361842155457,
                "source": "local"
            },
            {
                "id": 470357272956278367,
                "item_name": "RSPRORS-12数字万用表",
                "file_title": "万用表RS-12的使用",
                "content": "## 电阻测量\n\n警告: 为防触电,测量前应断开电源，把所有电容放电，取出电池和拔掉电线。\n\n1. 将功能转盘置于最高电阻Ω位置\n\n2. 将黑色表笔插入负极COM端口，红色表笔插入正极Ω端口\n\n3. 把表笔接触被测电路或元件。测试时最好断开电路的一端，以使剩余的电路不会干扰被测电阻数值。\n\n4. 读取显示屏上读数，然后将功能转盘调至最低电阻Ω档位，通常大于实际电阻或预测电阻.读数由精确的小数点和数值表示。",
                "title": "## 电阻测量",
                "score": 0.8457084894180298,
                "source": "local"
            },
            {
                "id": 470357272956278368,
                "item_name": "RSPRORS-12数字万用表",
                "file_title": "万用表RS-12的使用",
                "content": "## 电阻测量\n\n![图片展示数字万用表测量电阻的接线示意图，表笔连接被测元件，显示屏显示“1.953”，下方标注“Ω”单位，配合文字说明电阻测量与短路蜂鸣测试操作要点。](http://192.168.77.77:9000/knowledge-base/upload-images/20261110/万用表RS-12的使用/3dce15efe5689c2d8c904dfbbb653eef71ce00b270bd08d47e3b474af2fb68a8.jpg)",
                "title": "## 电阻测量",
                "score": 0.8356079459190369,
                "source": "local"
            },
            {
                "id": 470357272956278360,
                "item_name": "RSPRORS-12数字万用表",
                "file_title": "万用表RS-12的使用",
                "content": "## 直流电压测量\n\n注意：正打开或关闭电源时不要进行此项测量，瞬间的强大电压将损坏仪表。\n\n1. 将功能转盘置于V DC的位置。\n\n2. 将黑色表笔插入负极COM端口，红色表笔插入正极V端口。\n\n3. 将表笔尖端接触被测物,确保极性正确(红色连正极,黑色连负极)。\n\n4. 显示屏上读取电压值。显示屏显示了精确的小数点，数值。若极性颠倒，数值前将显示负号。\n",
                "title": "## 直流电压测量",
                "score": 0.6547167301177979,
                "source": "local"
            },
            {
                "id": 470357272956278363,
                "item_name": "RSPRORS-12数字万用表",
                "file_title": "万用表RS-12的使用",
                "content": "## 交流电压测量\n\n2. 将黑色表笔插入负极COM端口，红色表笔插入正极V端口。\n\n3. 将表笔尖端接触被测物。\n\n4. 显示屏上读取电压值。显示屏显示了精确的小数点，数值和(AC,V等)符号。\n\n在显示屏上读取电压数据。不断重调功能转盘至低交流电压档位获得高分辨率读数。读数由精确的小数点和数值表示。",
                "title": "## 交流电压测量",
                "score": 0.6457425951957703,
                "source": "local"
            },
            {
                "id": 470357272956278365,
                "item_name": "RSPRORS-12数字万用表",
                "file_title": "万用表RS-12的使用",
                "content": "## 直流电流测量\n\n1. 将黑色表笔插入负极COM端口。\n\n2. 测量直流200mA 以下的电流,将功能转盘置于最高DC mA档位，并将红色表笔插入mA端口。\n\n3. 测量直流10A时,将功能转盘置于10A档位，并将红色表笔(10A)端口。\n\n4. 断开被测电路的电源。在你想测量电流的位置打开电路绝缘层。\n\n5. 将黑色表笔接触被测电路的负极，红色表笔接触被测电路正极。\n\n6. 接通电源。\n\n7. 在显示屏上读取读数。进行mA DC测量时,不断重调功能转盘至低mA DC档位获得高分辨率读数.读数由精确的小数点和数值表示。",
                "title": "## 直流电流测量",
                "score": 0.6422015428543091,
                "source": "local"
            },
            {
                "id": 470357272956278349,
                "item_name": "RSPRORS-12数字万用表",
                "file_title": "万用表RS-12的使用",
                "content": "## 控制与端口\n\n1.LCD液晶显示\n\n2.功能选择转盘\n\n3.10A端口\n\n4.COM端口\n\n5.正极端口\n\n6.数据保持按键\n\n7.背光按键\n\n![该图为一款数字万用表结构图，标注了LCD显示、功能转盘、测试端口（10A、COM、正极）及数据保持、背光按键，并说明具双绝缘保护与蜂鸣指示功能。](http://192.168.77.77:9000/knowledge-base/upload-images/20261110/万用表RS-12的使用/d6946861c4592804bd8d7e75b58029565712d4dc58f855e374bf0fcf370c91dd.jpg)\n",
                "title": "## 控制与端口",
                "score": 0.6409847140312195,
                "source": "local"
            },
            {
                "id": 470357272956278371,
                "item_name": "RSPRORS-12数字万用表",
                "file_title": "万用表RS-12的使用",
                "content": "## 电池测试\n\n1. 将黑色表笔插入负极COM端口，红色表笔插入正极V 端口。\n\n2. 使用功能选择键，选择1.5V 或 9V 电池档位。\n\n3. 将红色表笔接触电池正极，将黑色表笔接触电池负极。\n\n4. 在显示屏上读取数值。\n\n<table><tr><td></td><td>良好</td><td>较弱</td><td>坏的</td></tr><tr><td>9V 电池:</td><td>&gt;8.2V</td><td>7.2 至 8.2V</td><td>&lt;7.2V</td></tr><tr><td>1.5V 电池:</td><td>&gt;1.35V</td><td>1.22 至 1.35V</td><td>&lt;1.22V</td></tr></table>\n",
                "title": "## 电池测试",
                "score": 0.6373416185379028,
                "source": "local"
            }
        ]
    }

    node_rrf = NodeRrf()
    result = node_rrf(init_state)  # type:ignore
    logger.info(json_format(result))