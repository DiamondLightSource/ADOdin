from iocbuilder import AutoSubstitution
from iocbuilder.arginfo import makeArgInfo, Simple, Ident

from util import OneLineEntry, create_config_entry
from odin import _FrameProcessorPlugin


class _OffsetAdjustmentPluginTemplate(AutoSubstitution):
    TemplateFile = "OffsetAdjustmentPlugin.template"


class _OffsetAdjustmentPlugin(_FrameProcessorPlugin):

    NAME = "offset"
    CLASS_NAME = "OffsetAdjustmentPlugin"
    TEMPLATE = _OffsetAdjustmentPluginTemplate

    def __init__(self, source=None):
        super(_OffsetAdjustmentPlugin, self).__init__(source)


class _UIDAdjustmentPluginTemplate(AutoSubstitution):
    TemplateFile = "UIDAdjustmentPlugin.template"


class _DatasetCreationPlugin(_FrameProcessorPlugin):

    DATASETS = []
    DATASET_TYPE = "uint64"

    def create_extra_config_entries(self, rank, total):
        entries = super(_DatasetCreationPlugin, self).create_extra_config_entries(rank, total)
        if self.DATASETS is not None:
            for dset in self.DATASETS:
                dset_desc = {}
                if 'type' in dset:
                    dset_desc['datatype'] = dset['type']
                if 'dims' in dset:
                    dset_desc['dims'] = OneLineEntry(dset['dims'])
                if 'type' in dset:
                    dset_desc['chunks'] = OneLineEntry(dset['chunks'])
                else:
                    dset_desc['chunks'] = OneLineEntry([1000])
                dataset_entry = {
                    _FileWriterPlugin.NAME: {
                        "dataset": {
                            dset['name']: dset_desc
                        }
                    }
                }
                entries.append(create_config_entry(dataset_entry))

        return entries


class _ParameterAdjustmentPluginTemplate(AutoSubstitution):
    TemplateFile = "ParameterAdjustmentPlugin.template"


class _ParameterAdjustmentPlugin(_DatasetCreationPlugin):

    NAME = "param"
    CLASS_NAME = "ParameterAdjustmentPlugin"
    DATASET_NAME = None
    PARAMETER_PLUGIN_INSTANTIATED = False

    def __init__(self, source=None):
        super(_ParameterAdjustmentPlugin, self).__init__(source)

    def create_template(self, template_args):
        if not self.PARAMETER_PLUGIN_INSTANTIATED:
            # If this is the first parameter plugin, instantiate base template
            base_args = dict((k, v) for k, v in template_args.items()
                             if k in ["P", "R", "PORT", "TOTAL"])
            _ParameterAdjustmentPluginTemplate(**base_args)
            self.PARAMETER_PLUGIN_INSTANTIATED = True
        super(_ParameterAdjustmentPlugin, self).create_template(template_args)

    def create_extra_config_entries(self, rank, total):
        entries = super(_ParameterAdjustmentPlugin, self).create_extra_config_entries(rank, total)
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


class _UIDAdjustmentPlugin(_ParameterAdjustmentPlugin):

    DATASET_NAME = "uid"
    TEMPLATE = _UIDAdjustmentPluginTemplate

    def __init__(self, source=None):
        super(_UIDAdjustmentPlugin, self).__init__(source)


class _SumPluginTemplate(AutoSubstitution):
    TemplateFile = "SumPlugin.template"


class _SumPlugin(_DatasetCreationPlugin):

    NAME = "sum"
    CLASS_NAME = "SumPlugin"
    DATASET_NAME = "sum"
    TEMPLATE = _SumPluginTemplate

    def __init__(self, source=None):
        super(_SumPlugin, self).__init__(source)

    def create_template(self, template_args):
        template_args = dict((k, v) for k, v in template_args.items()
                             if k in ["P", "R", "PORT", "TOTAL"])
        super(_SumPlugin, self).create_template(template_args)


class _KafkaPlugin(_FrameProcessorPlugin):

    NAME = "kafka"
    CLASS_NAME = "KafkaProducerPlugin"

    def __init__(self, servers, source=None):
        super(_KafkaPlugin, self).__init__(source)

        self.servers = servers

    def create_extra_config_entries(self, rank, total):
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

    ArgInfo = _FrameProcessorPlugin.ArgInfo + makeArgInfo(__init__,
        source=Ident("Plugin to connect to", _FrameProcessorPlugin),
        servers=Simple("Servers to connect to (comma separated)", str)
    )


class _FileWriterPlugin(_FrameProcessorPlugin):

    NAME = "hdf"
    CLASS_NAME = "FileWriterPlugin"
    LIBRARY_NAME = "Hdf5Plugin"
    DATASET_NAME = "data"

    def __init__(self, source=None, indexes=False):
        super(_FileWriterPlugin, self).__init__(source)

        self.indexes = indexes

    def create_extra_config_entries(self, rank, total):
        entries = []
        entries.append(
            create_config_entry(
                {
                    self.NAME: {
                        "process": {
                            "number": total,
                            "rank": rank
                        }
                    }
                }
            )
        )
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


class _LiveViewPlugin(_FrameProcessorPlugin):

    NAME = "view"
    CLASS_NAME = "LiveViewPlugin"
    TEMPLATE = _LiveViewPluginTemplate
    BASE_PORT = 5005

    def __init__(self, source=None):
        super(_LiveViewPlugin, self).__init__(source)

        self.endpoint = None

    def create_extra_config_entries(self, rank, total):
        entries = []
        self.endpoint = "tcp://0.0.0.0:{}".format(self.BASE_PORT + rank * 10)
        source_entry = {
            self.NAME: {
                "dataset_name": _FileWriterPlugin.DATASET_NAME,
                "live_view_socket_addr": self.endpoint
            }
        }
        entries.append(create_config_entry(source_entry))

        return entries


class _BloscPluginTemplate(AutoSubstitution):
    TemplateFile = "BloscPlugin.template"


class _BloscPlugin(_FrameProcessorPlugin):

    NAME = "blosc"
    CLASS_NAME = "BloscPlugin"
    TEMPLATE = _BloscPluginTemplate

    def __init__(self, source=None):
        super(_BloscPlugin, self).__init__(source)
