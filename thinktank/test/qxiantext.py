import pymupdf

src = r"C:\Users\Administrator\Desktop\育儿\数据\儿童性格心理学.pdf"
dst = r"C:\Users\Administrator\Desktop\育儿\数据\儿童性格心理学_clean.pdf"

doc = pymupdf.open(src)
doc.save(dst, garbage=4, deflate=True, clean=True)  # garbage=4 最彻底的对象重组
doc.close()
print("重建完成")