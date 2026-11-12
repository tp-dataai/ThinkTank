import json

def json_format(data):
    result = json.dumps(data, ensure_ascii=False, indent=4,default=str)
    return result