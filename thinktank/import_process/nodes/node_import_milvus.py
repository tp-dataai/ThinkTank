# thinktank/import_process/nodes/node_entry.py
from thinktank.import_process.base import NodeBase
from thinktank.import_process.state import ImportGraphState


class NodeImportMilvus(NodeBase):
    """
    
    """

    name = "node_import_milvus"

    def process(self, state: ImportGraphState):

        return state