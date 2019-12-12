from iocbuilder import AutoSubstitution, Device
from iocbuilder.arginfo import makeArgInfo, Simple, Ident, Choice
from iocbuilder.iocinit import IocDataStream
from iocbuilder.modules.asyn import AsynPort
from iocbuilder.modules.ADCore import ADCore, ADBaseTemplate, makeTemplateInstance
from iocbuilder.modules.restClient import restClient
from iocbuilder.modules.calc import Calc

from util import debug_print, OdinPaths, data_file_path, expand_template_file, \
    create_batch_entry, create_config_entry


# ~~~~~~~~ #
# OdinData #
# ~~~~~~~~ #

debug_print("OdinData: {}".format(OdinPaths.ODIN_DATA), 1)


class _OdinDataTemplate(AutoSubstitution):
    TemplateFile = "OdinData.template"


class _OdinData(Device):

    """Store configuration for an OdinData process"""
    INDEX = 1  # Unique index for each OdinData instance
    RANK = None
    FP_ENDPOINT = ""
    FR_ENDPOINT = ""

    # Device attributes
    AutoInstantiate = True

    def __init__(self, server, READY, RELEASE, META, PLUGINS):
        self.__super.__init__()
        # Update attributes with parameters
        self.__dict__.update(locals())

        self.IP = server.IP
        self.plugins = PLUGINS

        # Create unique R MACRO for template file - OD1, OD2 etc.
        self.R = ":OD{}:".format(self.INDEX)
        self.index = _OdinData.INDEX
        _OdinData.INDEX += 1

    def create_config_file(self, prefix, template, extra_macros=None):
        macros = dict(
            IP=self.server.IP, ODIN_DATA=OdinPaths.ODIN_DATA,
            RD_PORT=self.READY, RL_PORT=self.RELEASE, META_PORT=self.META
        )
        if extra_macros is not None:
            macros.update(extra_macros)
        if self.plugins is not None:
            load_entries = []
            connect_entries = []
            config_entries = []
            for plugin in self.plugins:
                load_entries.append(plugin.create_config_load_entry())
                connect_entries.append(create_config_entry(plugin.create_config_connect_entry()))
                config_entries += plugin.create_extra_config_entries(self.RANK)
            for mode in self.plugins.modes:
                valid_entries = False
                mode_config_dict = {'store': {'index': mode, 'value': [{'plugin': {'disconnect': 'all'}}]}}
                for plugin in self.plugins:
                    entry = plugin.create_config_connect_entry(mode)
                    if entry is not None:
                        valid_entries = True
                        mode_config_dict['store']['value'].append(entry)
                if valid_entries:
                    connect_entries.append(create_config_entry(mode_config_dict))
            
            custom_plugin_config_macros = dict(
                LOAD_ENTRIES=",\n  ".join(load_entries),
                CONNECT_ENTRIES=",\n  ".join(connect_entries),
                CONFIG_ENTRIES=",\n  ".join(config_entries)
            )
            macros.update(custom_plugin_config_macros)

        expand_template_file(template, macros, "{}{}.json".format(prefix, self.RANK + 1))

    def create_config_files(self, index):
        raise NotImplementedError("Method must be implemented by child classes")

    def add_batch_entries(self, entries, beamline, number):
        entries.append(
            create_batch_entry(beamline, number, "FrameReceiver{}".format(self.RANK + 1))
        )
        number += 1
        entries.append(
            create_batch_entry(beamline, number, "FrameProcessor{}".format(self.RANK + 1))
        )
        return number + 1


class FrameProcessorPlugin(Device):

    NAME = None
    CLASS_NAME = None
    LIBRARY_NAME = None
    LIBRARY_PATH = OdinPaths.ODIN_DATA

    TEMPLATE = None
    TEMPLATE_INSTANTIATED = False

    def __init__(self, source=None):
        self.connections = {}

        if source is not None:
            self.source = source.NAME
        else:
            self.source = "frame_receiver"

    def add_mode(self, mode, source=None):
        if source is not None:
            self.connections[mode] = source.NAME
        else:
            self.connections[mode] = "frame_receiver"

    def create_config_load_entry(self):
        library_name = self.LIBRARY_NAME if self.LIBRARY_NAME is not None else self.CLASS_NAME
        entry = {
            "plugin": {
                "load": {
                    "index": self.NAME,
                    "name": self.CLASS_NAME,
                    "library": "{}/prefix/lib/lib{}.so".format(self.LIBRARY_PATH, library_name)
                }
            }
        }
        return create_config_entry(entry)

    def create_config_connect_entry(self, mode=None):
        cnxn = None
        if mode is None:
            cnxn = self.source
        elif mode in self.connections:
            cnxn = self.connections[mode]

        entry = None
        if cnxn is not None:
            entry = {
                "plugin": {
                    "connect": {
                        "index": self.NAME,
                        "connection": cnxn,
                    }
                }
            }
        return entry

    def create_extra_config_entries(self, rank):
        return []

    def create_template(self, template_args):
        if self.TEMPLATE is not None and not self.TEMPLATE_INSTANTIATED:
            makeTemplateInstance(self.TEMPLATE, locals(), template_args)
        self.TEMPLATE_INSTANTIATED = True


FrameProcessorPlugin.ArgInfo = makeArgInfo(FrameProcessorPlugin.__init__,
    source=Ident("Plugin to connect to", FrameProcessorPlugin)
)


class PluginConfig(Device):

    def __init__(self, PLUGIN_1=None, PLUGIN_2=None, PLUGIN_3=None, PLUGIN_4=None, PLUGIN_5=None,
                 PLUGIN_6=None, PLUGIN_7=None, PLUGIN_8=None):
        self.plugins = [plugin for plugin in
                        [PLUGIN_1, PLUGIN_2, PLUGIN_3, PLUGIN_4,
                         PLUGIN_5, PLUGIN_6, PLUGIN_7, PLUGIN_8]
                        if plugin is not None]
        self.modes = []

    ArgInfo = makeArgInfo(__init__,
        PLUGIN_1=Ident("Plugin 1", FrameProcessorPlugin),
        PLUGIN_2=Ident("Plugin 2", FrameProcessorPlugin),
        PLUGIN_3=Ident("Plugin 3", FrameProcessorPlugin),
        PLUGIN_4=Ident("Plugin 4", FrameProcessorPlugin),
        PLUGIN_5=Ident("Plugin 5", FrameProcessorPlugin),
        PLUGIN_6=Ident("Plugin 6", FrameProcessorPlugin),
        PLUGIN_7=Ident("Plugin 7", FrameProcessorPlugin),
        PLUGIN_8=Ident("Plugin 8", FrameProcessorPlugin)
    )

    def detector_setup(self, od_args):
        # No op, should be overridden by specific detector
        pass

    def __iter__(self):
        for plugin in self.plugins:
            yield plugin


class _OdinDataServer(Device):

    """Store configuration for an OdinDataServer"""
    PORT_BASE = 5000
    PROCESS_COUNT = 0

    # Device attributes
    AutoInstantiate = True

    def __init__(self, IP, PROCESSES, SHARED_MEM_SIZE, PLUGIN_CONFIG=None,
                 IO_THREADS=1, TOTAL_NUMA_NODES=0):
        self.__super.__init__()
        # Update attributes with parameters
        self.__dict__.update(locals())

        self.plugins = PLUGIN_CONFIG

        self.processes = []
        for _ in range(PROCESSES):
            self.processes.append(
                self.create_odin_data_process(
                    self, self.PORT_BASE + 1, self.PORT_BASE + 2, self.PORT_BASE + 8, PLUGIN_CONFIG)
            )
            self.PORT_BASE += 10

        self.instantiated = False  # Make sure instances are only used once

    ArgInfo = makeArgInfo(__init__,
        IP=Simple("IP address of server hosting OdinData processes", str),
        PROCESSES=Simple("Number of OdinData processes on this server", int),
        SHARED_MEM_SIZE=Simple("Size of shared memory buffers in bytes", int),
        PLUGIN_CONFIG=Ident("Define a custom set of plugins", PluginConfig),
        IO_THREADS=Simple("Number of FR Ipc Channel IO threads to use", int),
        TOTAL_NUMA_NODES=Simple("Total number of numa nodes available to distribute processes over"
                                " - Optional for performance tuning", int)
    )

    def create_odin_data_process(self, server, ready, release, meta, plugin_config):
        raise NotImplementedError("Method must be implemented by child classes")

    def configure_processes(self, server_rank, total_servers):
        rank = server_rank
        for idx, process in enumerate(self.processes):
            process.RANK = rank
            rank += total_servers

    def create_od_startup_scripts(self):
        for idx, process in enumerate(self.processes):
            fp_port_number = 5004 + (10 * idx)
            fr_port_number = 5000 + (10 * idx)
            ready_port_number = 5001 + (10 * idx)
            release_port_number = 5002 + (10 * idx)

            # If TOTAL_NUMA_NODES was set, we enable the NUMA call macro instantitation
            if self.TOTAL_NUMA_NODES > 0:
                numa_node = idx % int(self.TOTAL_NUMA_NODES)
                numa_call = "numactl --membind={node} --cpunodebind={node} ".format(node=numa_node)
            else:
                numa_call = ""

            # Store server designation on OdinData object
            process.FP_ENDPOINT = "{}:{}".format(self.IP, fp_port_number)
            process.FR_ENDPOINT = "{}:{}".format(self.IP, fr_port_number)

            output_file = "stFrameReceiver{}.sh".format(process.RANK + 1)
            macros = dict(
                NUMBER=process.RANK + 1,
                ODIN_DATA=OdinPaths.ODIN_DATA,
                BUFFER_IDX=idx + 1, SHARED_MEMORY=self.SHARED_MEM_SIZE,
                CTRL_PORT=fr_port_number, IO_THREADS=self.IO_THREADS,
                READY_PORT=ready_port_number, RELEASE_PORT=release_port_number,
                LOG_CONFIG=data_file_path("log4cxx.xml"),
                NUMA=numa_call)
            expand_template_file("fr_startup", macros, output_file, executable=True)

            output_file = "stFrameProcessor{}.sh".format(process.RANK + 1)
            macros = dict(
                NUMBER=process.RANK + 1,
                ODIN_DATA=OdinPaths.ODIN_DATA,
                HDF5_FILTERS=OdinPaths.HDF5_FILTERS,
                CTRL_PORT=fp_port_number,
                READY_PORT=ready_port_number, RELEASE_PORT=release_port_number,
                LOG_CONFIG=data_file_path("log4cxx.xml"),
                NUMA=numa_call)
            expand_template_file("fp_startup", macros, output_file, executable=True)


class OdinLogConfig(Device):

    """Create logging configuration file"""

    # Device attributes
    AutoInstantiate = True

    def __init__(self, BEAMLINE, DETECTOR):
        self.__super.__init__()
        # Update attributes with parameters
        self.__dict__.update(locals())

        self.create_config_file(BEAMLINE, DETECTOR)

    def create_config_file(self, BEAMLINE, DETECTOR):
        macros = dict(BEAMLINE=BEAMLINE, DETECTOR=DETECTOR)

        expand_template_file("log4cxx_template.xml", macros, "log4cxx.xml")

    # __init__ arguments
    ArgInfo = makeArgInfo(__init__,
        BEAMLINE=Simple("Beamline name, e.g. b21, i02-2", str),
        DETECTOR=Choice("Detector type", ["Excalibur1M", "Excalibur3M", "Eiger4M", "Eiger16M"])
    )


# ~~~~~~~~~~~ #
# OdinControl #
# ~~~~~~~~~~~ #

class _OdinControlServer(Device):

    """Store configuration for an OdinControlServer"""

    ODIN_SERVER = None
    ADAPTERS = ["fp", "fr"]

    # Device attributes
    AutoInstantiate = True

    def __init__(self, IP, PORT=8888,
                 ODIN_DATA_SERVER_1=None, ODIN_DATA_SERVER_2=None,
                 ODIN_DATA_SERVER_3=None, ODIN_DATA_SERVER_4=None):
        self.__super.__init__()
        # Update attributes with parameters
        self.__dict__.update(locals())

        self.odin_data_servers = [
            server for server in [
                ODIN_DATA_SERVER_1, ODIN_DATA_SERVER_2, ODIN_DATA_SERVER_3, ODIN_DATA_SERVER_4
            ] if server is not None
        ]

        if not self.odin_data_servers:
            raise ValueError("Received no control endpoints for Odin Server")

        self.odin_data_processes = []
        for server in self.odin_data_servers:
            if server is not None:
                self.odin_data_processes += server.processes

        self.create_startup_script()

    ArgInfo = makeArgInfo(__init__,
        IP=Simple("IP address of control server", str),
        PORT=Simple("Port of control server", int),
        ODIN_DATA_SERVER_1=Ident("OdinDataServer 1 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_2=Ident("OdinDataServer 2 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_3=Ident("OdinDataServer 3 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_4=Ident("OdinDataServer 4 configuration", _OdinDataServer)
    )

    def get_extra_startup_macro(self):
        return ""

    def create_startup_script(self):
        macros = dict(ODIN_SERVER=self.ODIN_SERVER, CONFIG="odin_server.cfg", EXTRA_PARAMS=self.get_extra_startup_macro())
        expand_template_file("odin_server_startup", macros, "stOdinServer.sh", executable=True)

    def create_config_file(self):
        macros = dict(PORT=self.PORT,
                      ADAPTERS=", ".join(self.ADAPTERS),
                      ADAPTER_CONFIG="\n\n".join(self.create_odin_server_config_entries()),
                      STATIC_PATH=self.create_odin_server_static_path())
        expand_template_file("odin_server.ini", macros, "odin_server.cfg")

    def create_odin_server_static_path(self):
        return "./static"

    def create_odin_server_config_entries(self):
        raise NotImplementedError("Method must be implemented by child classes")

    def _create_odin_data_config_entry(self):
        fp_endpoints = []
        fr_endpoints = []
        for process in sorted(self.odin_data_processes, key=lambda x: x.RANK):
            fp_endpoints.append(process.FP_ENDPOINT)
            fr_endpoints.append(process.FR_ENDPOINT)

        return "[adapter.fp]\n" \
               "module = odin_data.frame_processor_adapter.FrameProcessorAdapter\n" \
               "endpoints = {}\n" \
               "update_interval = 0.2\n\n" \
               "[adapter.fr]\n" \
               "module = odin_data.frame_receiver_adapter.FrameReceiverAdapter\n" \
               "endpoints = {}\n" \
               "update_interval = 0.2".format(", ".join(fp_endpoints), ", ".join(fr_endpoints))

    def add_batch_entry(self, entries, beamline, number):
        entries.append(create_batch_entry(beamline, number, "OdinServer"))
        return number + 1


# ~~~~~~~~~~~~ #
# AreaDetector #
# ~~~~~~~~~~~~ #

class _OdinDetectorTemplate(AutoSubstitution):
    TemplateFile = "OdinDetector.template"


class _OdinDetector(AsynPort):

    """Create an odin detector"""

    Dependencies = (ADCore, restClient)

    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = "PORT"

    def __init__(self, PORT, ODIN_CONTROL_SERVER, DETECTOR, BUFFERS = 0, MEMORY = 0, **args):
        # Init the superclass (AsynPort)
        self.__super.__init__(PORT)
        # Update the attributes of self from the commandline args
        self.__dict__.update(locals())

        # Define Macros for Initialise substitutions
        self.CONTROL_SERVER_IP = ODIN_CONTROL_SERVER.IP
        self.CONTROL_SERVER_PORT = ODIN_CONTROL_SERVER.PORT

    # __init__ arguments
    ArgInfo = ADBaseTemplate.ArgInfo + makeArgInfo(__init__,
        PORT=Simple("Port name for the detector", str),
        ODIN_CONTROL_SERVER=Ident("Odin control server", _OdinControlServer),
        DETECTOR=Simple("Name of detector", str),
        BUFFERS=Simple("Maximum number of NDArray buffers to be created for plugin callbacks", int),
        MEMORY=Simple("Max memory to allocate, should be maxw*maxh*nbuffer for driver and all "
                      "attached plugins", int)
    )

    # Device attributes
    LibFileList = ["OdinDetector"]
    DbdFileList = ["OdinDetectorSupport"]

    def Initialise(self):
        print "# odinDetectorConfig(const char * portName, const char * serverPort, " \
              "int odinServerPort, const char * detectorName, " \
              "int maxBuffers, size_t maxMemory, int priority, int stackSize)"
        print "odinDetectorConfig(\"%(PORT)s\", \"%(CONTROL_SERVER_IP)s\", " \
              "%(CONTROL_SERVER_PORT)d, \"%(DETECTOR)s\", " \
              "%(BUFFERS)d, %(MEMORY)d)" % self.__dict__


class _OdinDataDriverTemplate(AutoSubstitution):
    TemplateFile = "OdinDataDriver.template"


class _OdinDataDriver(AsynPort):

    """Create an OdinData driver"""

    Dependencies = (ADCore, Calc, restClient)

    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = "PORT"

    def __init__(self, PORT, ODIN_CONTROL_SERVER, DETECTOR=None, DATASET="data",
                 BUFFERS=0, MEMORY=0, **args):
        # Init the superclass (AsynPort)
        self.__super.__init__(PORT)
        # Update the attributes of self from the commandline args
        self.__dict__.update(locals())

        self.control_server = ODIN_CONTROL_SERVER
        self.server_count = len(self.control_server.odin_data_servers)

        # Make an instance of our template
        args["TOTAL"] = self.server_count
        makeTemplateInstance(_OdinDataDriverTemplate, locals(), args)

        # Define Macros for Initialise substitutions
        self.CONTROL_SERVER_IP = ODIN_CONTROL_SERVER.IP
        self.CONTROL_SERVER_PORT = ODIN_CONTROL_SERVER.PORT
        self.DETECTOR_PLUGIN = DETECTOR.lower()
        self.ODIN_DATA_PROCESSES = []

        self.total_processes = 0
        # Calculate the total number of FR/FP pairs
        for server_idx, server in enumerate(self.control_server.odin_data_servers):
            if server.instantiated:
                raise ValueError("Same OdinDataServer object given twice")
            else:
                server.instantiated = True
            for odin_data in server.processes:
                self.total_processes += 1

        plugin_config = None
        for server_idx, server in enumerate(self.control_server.odin_data_servers):
            server.configure_processes(server_idx, self.server_count)

            process_idx = server_idx
            for odin_data in server.processes:
                self.ODIN_DATA_PROCESSES.append(odin_data)
                # Use some OdinDataDriver macros to instantiate an OdinData.template
                od_args = dict((key, args[key]) for key in ["P", "TIMEOUT"])
                od_args["PORT"] = PORT
                od_args["ADDR"] = odin_data.index - 1
                od_args["R"] = odin_data.R
                od_args["TOTAL"] = self.total_processes
                _OdinDataTemplate(**od_args)

                odin_data.create_config_files(process_idx + 1)
                process_idx += self.server_count

            if server.plugins is not None:
                plugin_config = server.plugins
                for plugin in server.plugins:
                    if not plugin.TEMPLATE_INSTANTIATED:
                        plugin_args = dict((key, args[key]) for key in ["P", "R"])
                        plugin_args["PORT"] = PORT
                        plugin_args["TOTAL"] = self.total_processes
                        plugin_args["GUI"] = \
                            self.gui_macro(PORT, "OdinData." + plugin.NAME.capitalize())
                        plugin.create_template(plugin_args)

            server.create_od_startup_scripts()

        if plugin_config is not None:
            od_args = dict((key, args[key]) for key in ["P", "TIMEOUT"])
            od_args["PORT"] = PORT
            od_args["ADDRESS"] = 0
            od_args["R"] = ":OD:"
            plugin_config.detector_setup(od_args)

        # Now OdinData instances are configured, OdinControlServer can generate its config from them
        self.control_server.create_config_file()

    # __init__ arguments
    ArgInfo = ADBaseTemplate.ArgInfo + _OdinDataDriverTemplate.ArgInfo + makeArgInfo(__init__,
        PORT=Simple("Port name for the detector", str),
        BUFFERS=Simple("Maximum number of NDArray buffers to be created for plugin callbacks", int),
        MEMORY=Simple("Max memory to allocate, should be maxw*maxh*nbuffer for driver and all "
                      "attached plugins", int),
        ODIN_CONTROL_SERVER=Ident("Odin control server", _OdinControlServer),
        DATASET=Simple("Name of Dataset", str),
        DETECTOR=Simple("Detector type", str)
    )

    # Device attributes
    LibFileList = ["OdinDetector"]
    DbdFileList = ["OdinDetectorSupport"]

    def Initialise(self):
        print "# odinDataDriverConfig(const char * portName, const char * serverPort, " \
              "int odinServerPort, int odinDataCount, " \
              "const char * datasetName, const char * detectorName, " \
              "int maxBuffers, size_t maxMemory)"
        print "odinDataDriverConfig(\"%(PORT)s\", \"%(CONTROL_SERVER_IP)s\", " \
              "%(CONTROL_SERVER_PORT)d, %(total_processes)d, " \
              "\"%(DATASET)s\", \"%(DETECTOR_PLUGIN)s\", " \
              "%(BUFFERS)d, %(MEMORY)d)" % self.__dict__

    def gui_macro(self, port, name):
        top = port[:port.find(".")]
        return "{}.{}".format(top, name)

    def create_gui_macros(self, port):
        return dict(
            OD_HDF_STATUS_GUI=self.gui_macro(port, "HDFStatus")
        )


class OdinBatchFile(Device):

    """Create configure-ioc batch file for all processes"""

    # Device attributes
    AutoInstantiate = True

    def __init__(self, BEAMLINE, ODIN_CONTROL_SERVER):
        self.__super.__init__()
        self.odin_control_server = ODIN_CONTROL_SERVER
        self.beamline = BEAMLINE

        self.create_batch_file()

    def create_batch_file(self):
        entries = []
        process_number = 1
        process_number = self.add_extra_entries(entries, process_number)
        for odin_data_server in self.odin_control_server.odin_data_servers:
            for odin_data_process in odin_data_server.processes:
                process_number = \
                    odin_data_process.add_batch_entries(entries, self.beamline, process_number)
        self.odin_control_server.add_batch_entry(entries, self.beamline, process_number)

        stream = IocDataStream("configure_odin")
        stream.write("\n".join(entries))

    def add_extra_entries(self, entries, process_number):
        return process_number

    # __init__ arguments
    ArgInfo = makeArgInfo(__init__,
        BEAMLINE=Simple("Beamline domain name, e.g. BL14I, BL21B", str),
        ODIN_CONTROL_SERVER=Ident("Odin control server", _OdinControlServer)
    )
