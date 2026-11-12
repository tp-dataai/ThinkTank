# 1. 原始列表
chunks = [{"id": 1}, {"id": 2}, {"id": 3}]
print("chunks=", chunks)

# 2. 切片赋值
batch = chunks[0:2] # 包含 id 1 和 id 2
print("batch=", batch)

# 3. 修改 batch 里的字典
print("batch[0]=",batch[0])
batch[0]["vector"] = [0.1, 0.2]   # type:ignore
print("batch=", batch)

# 4. 看看原列表
print(chunks) 
# 输出：[{'id': 1, 'vector': [0.1, 0.2]}, {'id': 2}, {'id': 3}]
# 看！原来的 chunks 也被修改了！