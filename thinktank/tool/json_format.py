import json
from bson import ObjectId

class MongoJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        
        return super().default(obj)
    
def json_format(data):
    result = json.dumps(data, ensure_ascii=False, indent=4)
    return result