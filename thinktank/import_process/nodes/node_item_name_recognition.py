# thinktank/import_process/nodes/node_entry.py
from thinktank.import_process.base import NodeBase
from thinktank.import_process.state import ImportGraphState


class NodeItemNameRecognition(NodeBase):
    

    name = "node_item_name_recognition"

    def process(self, state: ImportGraphState):

        return state