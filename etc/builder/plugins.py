from iocbuilder import AutoSubstitution
from iocbuilder.arginfo import makeArgInfo, Simple, Ident

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
        entries = super(DatasetCreationPlugin, self).create_extra_config_entries(rank)
        dataset_entry = {
            FileWriterPlugin.NAME: {
                "dataset": {
                    self.DATASET_NAME: {
                        "chunks": OneLineEntry([1000]),
                        "datatype": "uint64"
                    }
                }
            }
        }
        entries.append(create_config_entry(dataset_entry))

        return entries


class _ParameterAdjustmentPluginTemplate(AutoSubstitution):
    TemplateFile = "ParameterAdjustmentPlugin.template"


class ParameterAdjustmentPlugin(DatasetCreationPlugin):

    NAME = "param"
    CLASS_NAME = "ParameterAdjustmentPlugin"
    DATASET_NAME = None
    PARAMETER_PLUGIN_INSTANTIATED = False

    def __init__(self, source=None):
        super(ParameterAdjustmentPlugin, self).__init__(source)

    def create_template(self, template_args):
        if not self.PARAMETER_PLUGIN_INSTANTIATED:
            # If this is the first parameter plugin, instantiate base template
            base_args = dict((k, v) for k, v in template_args.items()
                             if k in ["P", "R", "PORT", "TOTAL"])
            _ParameterAdjustmentPluginTemplate(**base_args)
            self.PARAMETER_PLUGIN_INSTANTIATED = True
        super(ParameterAdjustmentPlugin, self).create_template(template_args)

    def create_extra_config_entries(self, rank):
        entries = super(ParameterAdjustmentPlugin, self).create_extra_config_entries(rank)
        parameter_entry = {
            self.NAME: {
                "parameter": {
                    self.DATASET_NAME: {
                        "adjustment": 0
                    }
                }
            }
        }
        entries.append(create_config_entry(parameter_entry))

        return entries


class UIDAdjustmentPlugin(ParameterAdjustmentPlugin):

    DATASET_NAME = "uid"
    TEMPLATE = _UIDAdjustmentPluginTemplate

    def __init__(self, source=None):
        super(UIDAdjustmentPlugin, self).__init__(source)


class _SumPluginTemplate(AutoSubstitution):
    TemplateFile = "SumPlugin.template"


class SumPlugin(DatasetCreationPlugin):

    NAME = "sum"
    CLASS_NAME = "SumPlugin"
    DATASET_NAME = "sum"
    TEMPLATE = _SumPluginTemplate

    def __init__(self, source=None):
        super(SumPlugin, self).__init__(source)

    def create_template(self, template_args):
        template_args = dict((k, v) for k, v in template_args.items()
                             if k in ["P", "R", "PORT", "TOTAL"])
        super(SumPlugin, self).create_template(template_args)


class KafkaPlugin(FrameProcessorPlugin):

    NAME = "kafka"
    CLASS_NAME = "KafkaProducerPlugin"

    def __init__(self, servers, source=None):
        super(KafkaPlugin, self).__init__(source)

        self.servers = servers

    def create_extra_config_entries(self, rank):
        entries = []
        source_entry = {
            self.NAME: {
                "dataset": "data",
                "topic": "data",
                "servers": self.servers
            }
        }
        entries.append(create_config_entry(source_entry))

        return entries

    ArgInfo = FrameProcessorPlugin.ArgInfo + makeArgInfo(__init__,
        source=Ident("Plugin to connect to", FrameProcessorPlugin),
        servers=Simple("Servers to connect to (comma separated)", str)
    )


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
