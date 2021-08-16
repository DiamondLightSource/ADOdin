import os

from iocbuilder import Device, AutoSubstitution
from iocbuilder.arginfo import makeArgInfo, Simple, Ident, Choice
from iocbuilder.modules.ADCore import ADBaseTemplate, makeTemplateInstance

from util import OdinPaths, expand_template_file, create_batch_entry, debug_print
from odin import (
    _OdinDetector,
    _OdinData,
    _OdinDataDriver,
    _OdinDataServer,
    _OdinControlServer,
    _MetaWriter,
    _PluginConfig,
    OdinBatchFile,
    OdinStartAllScript
)
from plugins import (
    _OffsetAdjustmentPlugin,
    _UIDAdjustmentPlugin,
    _FileWriterPlugin,
    _KafkaPlugin,
    _DatasetCreationPlugin
)


debug_print("Eiger: = {}".format(OdinPaths.EIGER_DETECTOR), 1)


class _EigerProcessPlugin(_DatasetCreationPlugin):

    NAME = "eiger"
    CLASS_NAME = "EigerProcessPlugin"
    LIBRARY_PATH = OdinPaths.EIGER_DETECTOR
    DATASETS = [
        dict(name="compressed_size", datatype="uint32")
    ]

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


class EigerMetaWriter(_MetaWriter):
    DETECTOR = "Eiger"
    SENSOR_SHAPE = None
    WRITER_CLASS = "metalistener.EigerMetaWriter"

    def _add_python_modules(self):
        self.PYTHON_MODULES.update(dict(eiger_data=OdinPaths.EIGER_DETECTOR))


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


class _EigerV16DetectorTemplate(AutoSubstitution):
    TemplateFile = "Eiger1.template"

class _EigerV18DetectorTemplate(AutoSubstitution):
    TemplateFile = "Eiger2.template"

class EigerDetector(_OdinDetector):

    """Create an Eiger detector"""

    DETECTOR = "eiger"
    DETECTOR_OPTIONS = {  # (AutoSubstitution Template, API)
        "V1": (_EigerV16DetectorTemplate, "1.6.0"),
        "V2": (_EigerV18DetectorTemplate, "1.8.0")
    }

    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = "PORT"

    # We don't really need the OdinDataDriver, but we need to know it is instantiated as it
    # defines the RANK on all the OdinData instances and we need to sort by RANK for the UDP config
    def __init__(self, PORT, ODIN_CONTROL_SERVER, ODIN_DATA_DRIVER, DETECTOR_VERSION,
                 BUFFERS=0, MEMORY=0, **args):
        # Init the superclass (OdinDetector)
        self.__super.__init__(PORT, ODIN_CONTROL_SERVER, self.DETECTOR,
                              BUFFERS, MEMORY, **args)
        # Update the attributes of self from the commandline args
        self.__dict__.update(locals())

        self.control_server = ODIN_CONTROL_SERVER

        debug_print("{}".format(args), 1)
        # Instantiate template corresponding to SENSOR, passing through some of own args
        detector_template = self.DETECTOR_OPTIONS[DETECTOR_VERSION][0]
        detector_args = {
            "P": args["P"],
            "R": args["R"],
            "ADDR": args["ADDR"],
            "PORT": PORT,
            "TIMEOUT": args["TIMEOUT"],
            "API": self.DETECTOR_OPTIONS[DETECTOR_VERSION][1]
        }
        detector_template(**detector_args)

    # __init__ arguments
    ArgInfo = ADBaseTemplate.ArgInfo + makeArgInfo(__init__,
        PORT=Simple("Port name for the detector", str),
        ODIN_CONTROL_SERVER=Ident("Odin control server instance", _OdinControlServer),
        ODIN_DATA_DRIVER=Ident("OdinDataDriver instance", _OdinDataDriver),
        DETECTOR_VERSION=Choice("Eiger detector version (1 or 2)", DETECTOR_OPTIONS.keys()),
        BUFFERS=Simple("Maximum number of NDArray buffers to be created for plugin callbacks", int),
        MEMORY=Simple("Max memory to allocate, should be maxw*maxh*nbuffer for driver and all "
                      "attached plugins", int)
    )


class EigerOdinControlServer(_OdinControlServer):

    """Store configuration for an EigerOdinControlServer"""

    ODIN_SERVER = os.path.join(OdinPaths.EIGER_DETECTOR, "prefix/bin/eiger_odin")

    def __init__(self, ENDPOINT, API, IP, EIGER_FAN, CTRL_PORT=8888, META_WRITER_IP=None,
                 ODIN_DATA_SERVER_1=None, ODIN_DATA_SERVER_2=None,
                 ODIN_DATA_SERVER_3=None, ODIN_DATA_SERVER_4=None):
        self.__dict__.update(locals())
        self.ADAPTERS.extend(["eiger", "eiger_fan"])

        self.eiger_fan = EIGER_FAN

        super(EigerOdinControlServer, self).__init__(
            IP, CTRL_PORT, META_WRITER_IP,
            ODIN_DATA_SERVER_1, ODIN_DATA_SERVER_2, ODIN_DATA_SERVER_3, ODIN_DATA_SERVER_4
        )

    ArgInfo = makeArgInfo(__init__,
        ENDPOINT=Simple("Detector endpoint", str),
        API=Choice("API version", ["1.6.0", "1.8.0"]),
        IP=Simple("IP address of control server", str),
        CTRL_PORT=Simple("Port of control server", int),
        EIGER_FAN=Ident("EigerFan configuration", EigerFan),
        META_WRITER_IP=Simple("IP address of MetaWriter (None -> first OdinDataServer)", str),
        ODIN_DATA_SERVER_1=Ident("OdinDataServer 1 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_2=Ident("OdinDataServer 2 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_3=Ident("OdinDataServer 3 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_4=Ident("OdinDataServer 4 configuration", _OdinDataServer)
    )

    def _add_python_modules(self):
        self.PYTHON_MODULES.update(dict(eiger_control=OdinPaths.EIGER_DETECTOR))

    def create_extra_config_entries(self):
        return [
            self._create_control_config_entry(),
            self._create_eiger_fan_config_entry()
        ]

    def _create_control_config_entry(self):
        return "[adapter.eiger]\n" \
               "module = eiger.eiger_adapter.EigerAdapter\n" \
               "endpoint = {}\n" \
               "api = {}".format(self.ENDPOINT, self.API)

    def _create_eiger_fan_config_entry(self):
        return "[adapter.eiger_fan]\n" \
               "module = eiger.eiger_fan_adapter.EigerFanAdapter\n" \
               "endpoints = {}:5559\n" \
               "update_interval = 0.5".format(self.eiger_fan.IP)

    def create_odin_server_static_path(self):
        return OdinPaths.EIGER_DETECTOR + "/prefix/html/static"


class _EigerDetectorTemplate(AutoSubstitution):
    TemplateFile = "EigerDetector.template"


class EigerOdinDataDriver(_OdinDataDriver):

    """Create an Eiger OdinData driver"""

    OD_SCREENS = [1, 2, 4, 8]
    META_WRITER_CLASS = EigerMetaWriter

    def __init__(self, SENSOR_Y=None, SENSOR_X=None, **args):
        # Insert sensor shape before base class init called
        sensor_shape = (SENSOR_Y, SENSOR_X)
        if None not in sensor_shape:
            EigerMetaWriter.SENSOR_SHAPE = sensor_shape

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
    ArgInfo += makeArgInfo(
        __init__,
        SENSOR_Y=Simple("Sensor Y dimension (height)", int),
        SENSOR_X=Simple("Sensor X dimension (width)", int)
    )


class EigerOdinBatchFile(OdinBatchFile):

    def add_extra_entries(self, entries, process_number):
        process_number = self.odin_data_driver.control_server.eiger_fan.add_batch_entry(
            entries, self.beamline, process_number
        )

        return process_number


class EigerOdinStartAllScript(OdinStartAllScript):

    def create_scripts(self, odin_data_processes):
        scripts = [self.create_script_entry("EigerFan", "stEigerFan.sh")]
        scripts += super(EigerOdinStartAllScript, self).create_scripts(odin_data_processes)
        return scripts
