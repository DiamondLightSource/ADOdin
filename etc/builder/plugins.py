from iocbuilder import AutoSubstitution

from util import OneLineEntry, create_config_entry
from odin import FrameProcessorPlugin


class _OffsetAdjustmentPluginTemplate(AutoSubstitution):
    TemplateFile = "OffsetAdjustmentPlugin.template"


class OffsetAdjustmentPlugin(FrameProcessorPlugin):

    NAME = "offset"
    CLASS_NAME = "OffsetAdjustmentPlugin"
    TEMPLATE = _OffsetAdjustmentPluginTemplate

    def __init__(self, source=None):
        super(OffsetAdjustmentPlugin, self).__init__(source)


class _UIDAdjustmentPluginTemplate(AutoSubstitution):
    TemplateFile = "UIDAdjustmentPlugin.template"


class DatasetCreationPlugin(FrameProcessorPlugin):

    def create_extra_config_entries(self, rank):
        entries = []
        dataset_entry = {
            FileWriterPlugin.NAME: {
                "dataset": {
                    self.NAME: {
                        "chunks": OneLineEntry([1000]),
                        "datatype": 3
                    }
                }
            }
        }
        entries.append(create_config_entry(dataset_entry))

        return entries


class UIDAdjustmentPlugin(DatasetCreationPlugin):

    NAME = "uid"
    CLASS_NAME = "UIDAdjustmentPlugin"
    TEMPLATE = _UIDAdjustmentPluginTemplate

    def __init__(self, source=None):
        super(UIDAdjustmentPlugin, self).__init__(source)


class _SumPluginTemplate(AutoSubstitution):
    TemplateFile = "SumPlugin.template"


class SumPlugin(DatasetCreationPlugin):

    NAME = "sum"
    CLASS_NAME = "SumPlugin"

    def __init__(self, source=None):
        super(SumPlugin, self).__init__(source)


class FileWriterPlugin(FrameProcessorPlugin):

    NAME = "hdf"
    CLASS_NAME = "FileWriterPlugin"
    LIBRARY_NAME = "Hdf5Plugin"
    DATASET_NAME = "data"

    def __init__(self, source=None, indexes=False):
        super(FileWriterPlugin, self).__init__(source)

        self.indexes = indexes

    def create_extra_config_entries(self, rank):
        entries = []
        dataset_entry = {
            self.NAME: {
                "dataset": self.DATASET_NAME,
            }
        }
        entries.append(create_config_entry(dataset_entry))
        if self.indexes:
            indexes_entry = {
                self.NAME: {
                    "dataset": {
                        self.DATASET_NAME: {
                            "indexes": True
                        }
                    }
                }
            }
            entries.append(create_config_entry(indexes_entry))

        return entries


class _LiveViewPluginTemplate(AutoSubstitution):
    TemplateFile = "LiveViewPlugin.template"


class LiveViewPlugin(FrameProcessorPlugin):

    NAME = "view"
    CLASS_NAME = "LiveViewPlugin"
    TEMPLATE = _LiveViewPluginTemplate
    BASE_PORT = 5005

    def __init__(self, source=None):
        super(LiveViewPlugin, self).__init__(source)

        self.endpoint = None

    def create_extra_config_entries(self, rank):
        entries = []
        self.endpoint = "tcp://0.0.0.0:{}".format(self.BASE_PORT + rank * 10)
        source_entry = {
            self.NAME: {
                "dataset_name": FileWriterPlugin.DATASET_NAME,
                "live_view_socket_addr": self.endpoint
            }
        }
        entries.append(create_config_entry(source_entry))

        return entries
        

class _BloscPluginTemplate(AutoSubstitution):
    TemplateFile = "BloscPlugin.template"


class BloscPlugin(FrameProcessorPlugin):

    NAME = "blosc"
    CLASS_NAME = "BloscPlugin"
    TEMPLATE = _BloscPluginTemplate

    def __init__(self, source=None):
        super(BloscPlugin, self).__init__(source)

