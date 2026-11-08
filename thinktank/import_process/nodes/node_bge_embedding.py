# thinktank/import_process/nodes/node_entry.py
from thinktank.import_process.base import NodeBase
from thinktank.import_process.state import ImportGraphState


class NodeBGEEmbedding(NodeBase):
    """
    
    """

    name = "node_bge_embedding"

    def process(self, state: ImportGraphState):

        return state