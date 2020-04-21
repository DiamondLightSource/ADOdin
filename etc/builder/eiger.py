import os

from iocbuilder import Device, AutoSubstitution
from iocbuilder.arginfo import makeArgInfo, Simple, Ident, Choice
from iocbuilder.modules.ADCore import makeTemplateInstance

from util import OdinPaths, expand_template_file, create_batch_entry, debug_print
from odin import _OdinData, _OdinDataDriver, _OdinDataServer, _OdinControlServer, OdinBatchFile, \
    _PluginConfig, OdinStartAllScript
from plugins import _OffsetAdjustmentPlugin, _UIDAdjustmentPlugin, _FileWriterPlugin, _KafkaPlugin, \
    _DatasetCreationPlugin


debug_print("Eiger: = {}".format(OdinPaths.EIGER_DETECTOR), 1)


class _EigerProcessPlugin(_DatasetCreationPlugin):

    NAME = "eiger"
    CLASS_NAME = "EigerProcessPlugin"
    LIBRARY_PATH = OdinPaths.EIGER_DETECTOR
    DATASET_NAME = "compressed_size"
    DATASET_TYPE = "uint32"

    def __init__(self, size_dataset):
        super(_EigerProcessPlugin, self).__init__(None)

        self.size_dataset = size_dataset

    def create_extra_config_entries(self, rank, total):
        entries = []
        if self.size_dataset:
            entries = super(_EigerProcessPlugin, self).create_extra_config_entries(rank, total)

        return entries


class EigerFan(Device):

    """Create startup file for an EigerFan process"""

    # Device attributes
    AutoInstantiate = True

    def __init__(self, IP, DETECTOR_IP, PROCESSES, SOCKETS, SENSOR, THREADS=2, BLOCK_SIZE=1000,
                 NUMA_NODE=-1):
        self.__super.__init__()
        # Update attributes with parameters
        self.__dict__.update(locals())

        self.create_startup_file()

    def create_startup_file(self):
        if self.NUMA_NODE >= 0:
            numa_call = "numactl --membind={node} --cpunodebind={node} ".format(node=self.NUMA_NODE)
        else:
            numa_call = ""
        macros = dict(EIGER_DETECTOR=OdinPaths.EIGER_DETECTOR, IP=self.DETECTOR_IP,
                      PROCESSES=self.PROCESSES, SOCKETS=self.SOCKETS, BLOCK_SIZE=self.BLOCK_SIZE,
                      THREADS=self.THREADS, NUMA=numa_call)

        expand_template_file("eiger_fan_startup", macros, "stEigerFan.sh",
                             executable=True)

    def add_batch_entry(self, entries, beamline, number):
        entries.append(create_batch_entry(beamline, number, "EigerFan"))
        return number + 1

    # __init__ arguments
    ArgInfo = makeArgInfo(__init__,
        IP=Simple("IP address of server hosting process", str),
        DETECTOR_IP=Simple("IP address of Eiger detector", str),
        PROCESSES=Simple("Number of processes to fan out to", int),
        SOCKETS=Simple("Number of sockets to open to Eiger detector stream", int),
        SENSOR=Choice("Sensor type", ["4M", "9M", "16M"]),
        THREADS=Simple("Number of ZMQ threads to use", int),
        BLOCK_SIZE=Simple("Number of blocks per file", int),
        NUMA_NODE=Simple("Numa node to run process on - Optional for performance tuning", int)
    )


class EigerMetaListener(Device):

    """Create startup file for an EigerMetaListener process"""

    # Device attributes
    AutoInstantiate = True

    def __init__(self, IP,
                 ODIN_DATA_SERVER_1=None, ODIN_DATA_SERVER_2=None,
                 ODIN_DATA_SERVER_3=None, ODIN_DATA_SERVER_4=None,
                 NUMA_NODE=-1):
        self.__super.__init__()
        # Update attributes with parameters
        self.__dict__.update(locals())

        self.ip_list = []
        self.sensor = None
        for server in [ODIN_DATA_SERVER_1, ODIN_DATA_SERVER_2, ODIN_DATA_SERVER_3, ODIN_DATA_SERVER_4]:
            if server is not None:
                base_port = 5000
                for odin_data in server.processes:
                    port = base_port + 8
                    self.ip_list.append("tcp://{}:{}".format(odin_data.IP, port))
                    base_port += 10
                    self.set_sensor(odin_data.sensor)

        self.create_startup_file()

    def set_sensor(self, sensor):
        if self.sensor is None:
            self.sensor = sensor
        else:
            if self.sensor != sensor:
                raise ValueError("Inconsistent sensor sizes given on OdinData processes")

    def create_startup_file(self):
        if self.NUMA_NODE >= 0:
            numa_call = "numactl --membind={node} --cpunodebind={node} ".format(node=self.NUMA_NODE)
        else:
            numa_call = ""
        macros = dict(EIGER_DETECTOR=OdinPaths.EIGER_DETECTOR,
                      IP_LIST=",".join(self.ip_list),
                      ODIN_DATA=OdinPaths.ODIN_DATA,
                      SENSOR=self.sensor,
                      NUMA=numa_call)

        expand_template_file("eiger_meta_startup", macros, "stEigerMetaListener.sh",
                             executable=True)

    def add_batch_entry(self, entries, beamline, number):
        entries.append(create_batch_entry(beamline, number, "EigerMetaListener"))
        return number + 1

    # __init__ arguments
    ArgInfo = makeArgInfo(__init__,
        IP=Simple("IP address of server hosting process", str),
        ODIN_DATA_SERVER_1=Ident("OdinDataServer 1 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_2=Ident("OdinDataServer 2 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_3=Ident("OdinDataServer 3 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_4=Ident("OdinDataServer 4 configuration", _OdinDataServer),
        NUMA_NODE=Simple("Numa node to run process on - Optional for performance tuning", int)
    )


class _EigerOdinData(_OdinData):

    CONFIG_TEMPLATES = {
        "FrameProcessor": "fp_eiger.json",
        "FrameReceiver": "fr_eiger.json"
    }

    def __init__(self, server, READY, RELEASE, META, PLUGIN_CONFIG, SOURCE_IP, SENSOR):
        super(_EigerOdinData, self).__init__(server, READY, RELEASE, META, PLUGIN_CONFIG)
        self.source = SOURCE_IP
        self.sensor = SENSOR

    def create_config_files(self, index, total):
        macros = dict(DETECTOR=OdinPaths.EIGER_DETECTOR,
                      IP=self.source,
                      RX_PORT_SUFFIX=self.RANK,
                      SENSOR=self.sensor)

        if self.plugins is None:
            super(_EigerOdinData, self).create_config_file(
                "fp", self.CONFIG_TEMPLATES["FrameProcessor"], extra_macros=macros)
        else:
            super(_EigerOdinData, self).create_config_file(
                "fp", "fp_custom.json", extra_macros=macros)

        super(_EigerOdinData, self).create_config_file(
            "fr", self.CONFIG_TEMPLATES["FrameReceiver"], extra_macros=macros)


class EigerPluginConfig(_PluginConfig):
    # Device attributes
    AutoInstantiate = True

    def __init__(self, MODE="Simple", KAFKA_SERVERS=None):
        if MODE == "Simple":
            eiger = _EigerProcessPlugin(size_dataset=False)
            hdf = _FileWriterPlugin(source=eiger, indexes=True)
            plugins = [eiger, hdf]
        elif MODE == "Malcolm":
            eiger = _EigerProcessPlugin(size_dataset=True)
            offset = _OffsetAdjustmentPlugin(source=eiger)
            uid = _UIDAdjustmentPlugin(source=offset)
            hdf = _FileWriterPlugin(source=uid, indexes=True)
            plugins = [eiger, offset, uid, hdf]
        elif MODE == "Kafka":
            if KAFKA_SERVERS is None:
                raise ValueError("Must provide Kafka servers with Kafka mode")
            eiger = _EigerProcessPlugin(size_dataset=False)
            kafka = _KafkaPlugin(KAFKA_SERVERS, source=eiger)
            hdf = _FileWriterPlugin(source=eiger, indexes=True)
            plugins = [eiger, kafka, hdf]
        else:
            raise ValueError("Invalid mode for EigerPluginConfig")

        super(EigerPluginConfig, self).__init__(*plugins)

    # __init__ arguments
    ArgInfo = makeArgInfo(__init__,
        MODE=Choice("Which plugin configuration mode to use", ["Simple", "Malcolm", "Kafka"]),
        KAFKA_SERVERS=Simple("Kafka servers, if using Kafka (comma separated).", str),
    )


class EigerOdinDataServer(_OdinDataServer):

    """Store configuration for an EigerOdinDataServer"""

    PLUGIN_CONFIG = None

    def __init__(self, IP, PROCESSES, SOURCE, SHARED_MEM_SIZE=16000000000, PLUGIN_CONFIG=None,
                 IO_THREADS=1, TOTAL_NUMA_NODES=0):
        self.source = SOURCE.IP
        self.sensor = SOURCE.SENSOR
        if PLUGIN_CONFIG is None:
            if EigerOdinDataServer.PLUGIN_CONFIG is None:
                # Create the standard Eiger plugin config
                EigerOdinDataServer.PLUGIN_CONFIG = EigerPluginConfig()
        else:
            EigerOdinDataServer.PLUGIN_CONFIG = PLUGIN_CONFIG

        self.__super.__init__(IP, PROCESSES, SHARED_MEM_SIZE, EigerOdinDataServer.PLUGIN_CONFIG,
                              IO_THREADS, TOTAL_NUMA_NODES)

    ArgInfo = makeArgInfo(__init__,
        IP=Simple("IP address of server hosting OdinData processes", str),
        PROCESSES=Simple("Number of OdinData processes on this server", int),
        SOURCE=Ident("EigerFan instance", EigerFan),
        SHARED_MEM_SIZE=Simple("Size of shared memory buffers in bytes", int),
        PLUGIN_CONFIG=Ident("Define a custom set of plugins", _PluginConfig),
        IO_THREADS=Simple("Number of FR Ipc Channel IO threads to use", int),
        TOTAL_NUMA_NODES=Simple("Total number of numa nodes available to distribute processes over"
                                " - Optional for performance tuning", int)
    )

    def create_odin_data_process(self, server, ready, release, meta, plugin_config):
        return _EigerOdinData(server, ready, release, meta, plugin_config, self.source, self.sensor)


class EigerOdinControlServer(_OdinControlServer):

    """Store configuration for an EigerOdinControlServer"""

    ODIN_SERVER = os.path.join(OdinPaths.EIGER_DETECTOR, "prefix/bin/eiger_odin")

    def __init__(self, IP, EIGER_FAN, META_LISTENER, PORT=8888,
                 ODIN_DATA_SERVER_1=None, ODIN_DATA_SERVER_2=None,
                 ODIN_DATA_SERVER_3=None, ODIN_DATA_SERVER_4=None):
        self.__dict__.update(locals())
        self.ADAPTERS.extend(["eiger_fan", "meta_listener"])

        self.eiger_fan = EIGER_FAN
        self.meta_listener = META_LISTENER

        super(EigerOdinControlServer, self).__init__(
            IP, PORT, ODIN_DATA_SERVER_1, ODIN_DATA_SERVER_2, ODIN_DATA_SERVER_3, ODIN_DATA_SERVER_4
        )

    # __init__ arguments
    ArgInfo = makeArgInfo(__init__,
        IP=Simple("IP address of control server", str),
        PORT=Simple("Port of control server", int),
        EIGER_FAN=Ident("EigerFan configuration", EigerFan),
        META_LISTENER=Ident("MetaListener configuration", EigerMetaListener),
        ODIN_DATA_SERVER_1=Ident("OdinDataServer 1 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_2=Ident("OdinDataServer 2 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_3=Ident("OdinDataServer 3 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_4=Ident("OdinDataServer 4 configuration", _OdinDataServer)
    )

    def create_odin_server_config_entries(self):
        return [
            self._create_odin_data_config_entry(),
            self._create_eiger_fan_config_entry(),
            self._create_meta_listener_config_entry()
        ]

    def create_odin_server_static_path(self):
        return OdinPaths.EIGER_DETECTOR + "/prefix/html/static"

    def _create_eiger_fan_config_entry(self):
        return "[adapter.eiger_fan]\n" \
               "module = eiger.eiger_fan_adapter.EigerFanAdapter\n" \
               "endpoints = {}:5559\n" \
               "update_interval = 0.5".format(self.eiger_fan.IP)

    def _create_meta_listener_config_entry(self):
        return "[adapter.meta_listener]\n" \
               "module = odin_data.meta_listener_adapter.MetaListenerAdapter\n" \
               "endpoints = {}:5659\n" \
               "update_interval = 0.5".format(self.meta_listener.IP)


class _EigerDetectorTemplate(AutoSubstitution):
    TemplateFile = "EigerDetector.template"


class EigerOdinDataDriver(_OdinDataDriver):

    """Create an Eiger OdinData driver"""

    OD_SCREENS = [1, 2, 4, 8]

    def __init__(self, **args):
        self.__super.__init__(DETECTOR="eiger", **args)
        # Update the attributes of self from the commandline args
        self.__dict__.update(locals())

        if self.odin_data_processes not in self.OD_SCREENS:
            raise ValueError("Total number of OdinData processes must be {}".format(
                self.OD_TEMPLATES))

        template_args = dict((key, args[key]) for key in ["P", "R", "PORT"])
        template_args["OD_COUNT"] = self.odin_data_processes
        template_args.update(self.create_gui_macros(args["PORT"]))
        makeTemplateInstance(_EigerDetectorTemplate, locals(), template_args)

    # __init__ arguments
    ArgInfo = _OdinDataDriver.ArgInfo.filtered(without=["DETECTOR"])


class EigerOdinBatchFile(OdinBatchFile):

    def add_extra_entries(self, entries, process_number):
        process_number = \
            self.odin_control_server.eiger_fan.add_batch_entry(entries, self.beamline,
                                                               process_number)
        process_number = \
            self.odin_control_server.meta_listener.add_batch_entry(entries, self.beamline,
                                                                   process_number)

        return process_number


class EigerOdinStartAllScript(OdinStartAllScript):

    def create_scripts(self, odin_data_processes):
        scripts = [self.create_script_entry("EigerFan", "stEigerFan.sh")]
        scripts += super(EigerOdinStartAllScript, self).create_scripts(odin_data_processes)
        scripts.append(self.create_script_entry(
            "MetaListener", "stEigerMetaListener.sh", "${PYTHON_EXPORTS}"
        ))
        return scripts
