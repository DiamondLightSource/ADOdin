import os
from string import Template

from dls_dependency_tree import dependency_tree

from iocbuilder import AutoSubstitution, Device
from iocbuilder.arginfo import makeArgInfo, Simple, Ident, Choice
from iocbuilder.iocinit import IocDataStream
from iocbuilder.modules.asyn import AsynPort
from iocbuilder.modules.ADCore import ADCore, ADBaseTemplate, makeTemplateInstance
from iocbuilder.modules.restClient import restClient
from iocbuilder.modules.calc import Calc


def debug_print(message, level):
    if int(os.getenv("ODIN_BUILDER_DEBUG", 0)) == level:
        print(message)


ADODIN_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.."))
ADODIN_DATA = os.path.join(ADODIN_ROOT, "data")

TREE = None


def find_module_path(module):
    global TREE
    if TREE is None:
        TREE = dependency_tree()
        TREE.process_module(ADODIN_ROOT)
    for macro, path in TREE.macros.items():
        if "/{}".format(module) in path:
            return macro, path


ODIN_DATA_MACRO, ODIN_DATA_ROOT = find_module_path("odin-data")
debug_print("OdinData: {} = {}".format(ODIN_DATA_MACRO, ODIN_DATA_ROOT), 1)


def expand_template_file(template, macros, output_file, executable=False):
    if executable:
        mode = 0755
    else:
        mode = None

    with open(os.path.join(ADODIN_DATA, template)) as template_file:
        template_config = Template(template_file.read())

    output = template_config.substitute(macros)
    debug_print("--- {} ----------------------------------------------".format(output_file), 2)
    debug_print(output, 2)
    debug_print("---", 2)

    stream = IocDataStream(output_file, mode)
    stream.write(output)


class _OdinDataTemplate(AutoSubstitution):
    TemplateFile = "OdinData.template"


class _OdinData(Device):

    """Store configuration for an OdinData process"""
    INDEX = 1  # Unique index for each OdinData instance
    RANK = 0
    FP_ENDPOINT = ""
    FR_ENDPOINT = ""

    # Device attributes
    AutoInstantiate = True

    def __init__(self, server, READY, RELEASE, META):
        self.__super.__init__()
        # Update attributes with parameters
        self.__dict__.update(locals())

        self.IP = server.IP

        # Create unique R MACRO for template file - OD1, OD2 etc.
        self.R = ":OD{}:".format(self.INDEX)
        self.index = _OdinData.INDEX
        _OdinData.INDEX += 1

    def create_config_file(self, prefix, template, index, extra_macros=None):
        macros = dict(
            IP=self.server.IP, OD_ROOT=ODIN_DATA_ROOT,
            RD_PORT=self.READY, RL_PORT=self.RELEASE, META_PORT=self.META
        )
        if extra_macros is not None:
            macros.update(extra_macros)

        expand_template_file(template, macros, "{}{}.json".format(prefix, index))

    def create_config_files(self, index):
        raise NotImplementedError("Method must be implemented by child classes")


class _OdinDataServer(Device):

    """Store configuration for an OdinDataServer"""
    PORT_BASE = 5000
    PROCESS_COUNT = 0

    # Device attributes
    AutoInstantiate = True

    def __init__(self, IP, PROCESSES, SHARED_MEM_SIZE, IO_THREADS=1, TOTAL_NUMA_NODES=0):
        self.__super.__init__()
        # Update attributes with parameters
        self.__dict__.update(locals())

        self.processes = []
        for _ in range(PROCESSES):
            self.processes.append(
                self.create_odin_data_process(
                    self, self.PORT_BASE + 1, self.PORT_BASE + 2, self.PORT_BASE + 8)
            )
            self.PORT_BASE += 10

        self.instantiated = False  # Make sure instances are only used once

    ArgInfo = makeArgInfo(__init__,
        IP=Simple("IP address of server hosting OdinData processes", str),
        PROCESSES=Simple("Number of OdinData processes on this server", int),
        SHARED_MEM_SIZE=Simple("Size of shared memory buffers in bytes", int),
        IO_THREADS=Simple("Number of FR Ipc Channel IO threads to use", int),
        TOTAL_NUMA_NODES=Simple("Total number of numa nodes available to distribute processes over"
                                " - Optional for performance tuning", int)
    )

    def create_odin_data_process(self, server, ready, release, meta):
        raise NotImplementedError("Method must be implemented by child classes")

    def create_od_startup_scripts(self, server_rank, total_servers):
        rank = server_rank
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
            process.RANK = rank
            process.FP_ENDPOINT = "{}:{}".format(self.IP, fp_port_number)
            process.FR_ENDPOINT = "{}:{}".format(self.IP, fr_port_number)

            output_file = "stFrameReceiver{}.sh".format(rank)
            macros = dict(
                OD_ROOT=ODIN_DATA_ROOT,
                BUFFER_IDX=idx + 1, SHARED_MEMORY=self.SHARED_MEM_SIZE,
                CTRL_PORT=fr_port_number, IO_THREADS=self.IO_THREADS,
                READY_PORT=ready_port_number, RELEASE_PORT=release_port_number,
                LOG_CONFIG=os.path.join(ADODIN_DATA, "log4cxx.xml"),
                NUMA=numa_call)
            expand_template_file("fr_startup", macros, output_file, executable=True)

            output_file = "stFrameProcessor{}.sh".format(rank)
            macros = dict(
                OD_ROOT=ODIN_DATA_ROOT,
                CTRL_PORT=fp_port_number,
                READY_PORT=ready_port_number, RELEASE_PORT=release_port_number,
                LOG_CONFIG=os.path.join(ADODIN_DATA, "log4cxx.xml"),
                NUMA=numa_call)
            expand_template_file("fp_startup", macros, output_file, executable=True)

            rank += total_servers


class _OdinDetectorTemplate(AutoSubstitution):
    TemplateFile = "OdinDetector.template"


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

    def create_startup_script(self):
        macros = dict(ODIN_SERVER=self.ODIN_SERVER, CONFIG="odin_server.cfg")
        expand_template_file("odin_server_startup", macros, "stOdinServer.sh", executable=True)

    def create_config_file(self):
        macros = dict(PORT=self.PORT,
                      ADAPTERS=", ".join(self.ADAPTERS),
                      ADAPTER_CONFIG="\n\n".join(self.create_odin_server_config_entries()))
        expand_template_file("odin_server.ini", macros, "odin_server.cfg")

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

    _SpecificTemplate = _OdinDataDriverTemplate

    def __init__(self, PORT, ODIN_CONTROL_SERVER, DETECTOR=None, DATASET="data",
                 BUFFERS=0, MEMORY=0, **args):
        # Init the superclass (AsynPort)
        self.__super.__init__(PORT)
        # Update the attributes of self from the commandline args
        self.__dict__.update(locals())
        # Make an instance of our template
        makeTemplateInstance(self._SpecificTemplate, locals(), args)

        self.control_server = ODIN_CONTROL_SERVER
        self.server_count = len(self.control_server.odin_data_servers)

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

        for server_idx, server in enumerate(self.control_server.odin_data_servers):
            process_idx = server_idx
            for odin_data in server.processes:
                self.ODIN_DATA_PROCESSES.append(odin_data)
                # Use some OdinDataDriver macros to instantiate an OdinData.template
                args["PORT"] = PORT
                args["ADDR"] = odin_data.index - 1
                args["R"] = odin_data.R
                args["OD"] = args["R"]
                args["TOTAL"] = self.total_processes
                _OdinDataTemplate(**args)

                odin_data.create_config_files(process_idx + 1)
                process_idx += self.server_count

            server.create_od_startup_scripts(server_idx + 1, self.server_count)

        # Now OdinData instances are configured, OdinControlServer can generate its config from them
        self.control_server.create_config_file()

    # __init__ arguments
    ArgInfo = ADBaseTemplate.ArgInfo + _SpecificTemplate.ArgInfo + makeArgInfo(__init__,
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
        # Configure up to 8 OdinData processes
        print "# odinDataProcessConfig(const char * ipAddress, int readyPort, " \
              "int releasePort, int metaPort)"
        for process in self.ODIN_DATA_PROCESSES:
            print "odinDataProcessConfig(\"%(IP)s\", %(READY)d, " \
                  "%(RELEASE)d, %(META)d)" % process.__dict__

        print "# odinDataDriverConfig(const char * portName, const char * serverPort, " \
              "int odinServerPort, " \
              "const char * datasetName, const char * detectorName, " \
              "int maxBuffers, size_t maxMemory)"
        print "odinDataDriverConfig(\"%(PORT)s\", \"%(CONTROL_SERVER_IP)s\", " \
              "%(CONTROL_SERVER_PORT)d, " \
              "\"%(DATASET)s\", \"%(DETECTOR_PLUGIN)s\", " \
              "%(BUFFERS)d, %(MEMORY)d)" % self.__dict__

    def gui_macro(self, port, name):
        top = port[:port.find(".")]
        return "{}.{}".format(top, name)

    def create_gui_macros(self, port):
        return dict(
            OD_HDF_STATUS_GUI=self.gui_macro(port, "HDFStatus"),
            OD_HDF_CONFIG_GUI=self.gui_macro(port, "HDFConfig")
        )


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
