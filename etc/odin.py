import os
from string import Template

from dls_dependency_tree import dependency_tree

from iocbuilder import AutoSubstitution, Device
from iocbuilder.arginfo import makeArgInfo, Simple, Ident, Choice
from iocbuilder.iocinit import IocDataStream
from iocbuilder.modules.asyn import AsynPort
from iocbuilder.modules.ADCore import ADCore, ADBaseTemplate, makeTemplateInstance
from iocbuilder.modules.calc import Calc
from iocbuilder.modules.restClient import restClient


ADODIN_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
print("ADOdin: {} = {}".format("<self>", ADODIN_ROOT))
ADODIN_DATA = os.path.join(ADODIN_ROOT, "data")


def find_module_path(module):
    tree = dependency_tree()
    tree.process_module(ADODIN_ROOT)
    for macro, path in tree.macros.items():
        if "/{}/".format(module) in path:
            return macro, path


ODIN_DATA_MACRO, ODIN_DATA_ROOT = find_module_path("odin-data")
print("OdinData: {} = {}".format(ODIN_DATA_MACRO, ODIN_DATA_ROOT))


def expand_template_file(template, macros, output_file, executable=False):
    if executable:
        mode = 0755
    else:
        mode = None

    with open(os.path.join(ADODIN_DATA, template)) as template_file:
        template_config = Template(template_file.read())

    output = template_config.substitute(macros)
    print("--- {} ----------------------------------------------".format(output_file))
    print(output)
    print("---")

    stream = IocDataStream(output_file, mode)
    stream.write(output)


class OdinData(Device):

    """Store configuration for an OdinData process"""
    INDEX = 1  # Unique index for each OdinData instance

    # Device attributes
    AutoInstantiate = True

    def __init__(self, IP, READY, RELEASE, META):
        self.__super.__init__()
        # Update attributes with parameters
        self.__dict__.update(locals())

        # Create unique R MACRO for template file - OD1, OD2 etc.
        self.R = ":OD{}:".format(self.INDEX)
        self.index = OdinData.INDEX
        OdinData.INDEX += 1

    def create_config_file(self, prefix, template, index, extra_macros=None):
        macros = dict(IP=self.IP, RD_PORT=self.READY, RL_PORT=self.RELEASE,
                      FW_ROOT=ODIN_DATA_ROOT)
        if extra_macros is not None:
            macros.update(extra_macros)

        expand_template_file(template, macros, "{}{}.json".format(prefix, index))


class OdinDataServer(Device):

    """Store configuration for an OdinDataServer"""
    ODIN_DATA_CLASS = OdinData
    PORT_BASE = 5000

    # Device attributes
    AutoInstantiate = True

    def __init__(self, IP, PROCESSES, SHARED_MEM_SIZE):
        self.__super.__init__()
        # Update attributes with parameters
        self.__dict__.update(locals())

        self.processes = []
        for _ in range(PROCESSES):
            self.processes.append(
                self.create_odin_data_process(
                    IP, self.PORT_BASE + 1, self.PORT_BASE + 2, self.PORT_BASE + 3)
            )
            self.PORT_BASE += 10

        self.create_od_startup_scripts()

        self.instantiated = False  # Make sure instances are only used once

    ArgInfo = makeArgInfo(__init__,
        IP=Simple("IP address of server hosting processes", str),
        PROCESSES=Simple("Number of OdinData processes on this server", int),
        SHARED_MEM_SIZE=Simple("Size of shared memory buffers in bytes", int),
    )

    def create_odin_data_process(self, ip, ready, release, meta, *args):
        return self.ODIN_DATA_CLASS(ip, ready, release, meta, *args)

    def create_od_startup_scripts(self):
        for idx, _ in enumerate(self.processes):
            fp_port_number = 5004 + (10 * idx)
            fr_port_number = 5000 + (10 * idx)
            ready_port_number = 5001 + (10 * idx)
            release_port_number = 5002 + (10 * idx)
            process_number = idx + 1

            output_file = "stFrameReceiver{}.sh".format(process_number)
            macros = dict(
                OD_ROOT=ODIN_DATA_ROOT,
                BUFFER_IDX=process_number, SHARED_MEMORY=self.SHARED_MEM_SIZE,
                CTRL_PORT=fr_port_number,
                READY_PORT=ready_port_number, RELEASE_PORT=release_port_number,
                LOG_CONFIG=os.path.join(ADODIN_DATA, "fr_log4cxx.xml"))
            expand_template_file("fr_startup", macros, output_file, executable=True)

            output_file = "stFrameProcessor{}.sh".format(process_number)
            macros = dict(
                OD_ROOT=ODIN_DATA_ROOT,
                CTRL_PORT=fp_port_number,
                READY_PORT=ready_port_number, RELEASE_PORT=release_port_number,
                LOG_CONFIG=os.path.join(ADODIN_DATA, "fp_log4cxx.xml"))
            expand_template_file("fp_startup", macros, output_file, executable=True)


class OdinDetectorTemplate(AutoSubstitution):
    TemplateFile = "odinDetector.template"


class OdinDetector(AsynPort):

    """Create an odin detector"""

    Dependencies = (ADCore, restClient)

    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = "PORT"

    def __init__(self, PORT, SERVER, ODIN_SERVER_PORT, DETECTOR, BUFFERS = 0, MEMORY = 0, **args):
        # Init the superclass (AsynPort)
        self.__super.__init__(PORT)
        # Update the attributes of self from the commandline args
        self.__dict__.update(locals())

    # __init__ arguments
    ArgInfo = ADBaseTemplate.ArgInfo + makeArgInfo(__init__,
        PORT=Simple("Port name for the detector", str),
        SERVER=Simple("Server host name", str),
        ODIN_SERVER_PORT=Simple("Odin server port", int),
        DETECTOR=Simple("Name of detector", str),
        BUFFERS=Simple("Maximum number of NDArray buffers to be created for plugin callbacks", int),
        MEMORY=Simple("Max memory to allocate, should be maxw*maxh*nbuffer for driver and all "
                      "attached plugins", int))

    # Device attributes
    LibFileList = ['odinDetector']
    DbdFileList = ['odinDetectorSupport']

    def Initialise(self):
        print "# odinDetectorConfig(const char * portName, const char * serverPort, " \
              "int odinServerPort, const char * detectorName, " \
              "int maxBuffers, size_t maxMemory, int priority, int stackSize)"
        print "odinDetectorConfig(\"%(PORT)s\", \"%(SERVER)s\", " \
              "%(ODIN_SERVER_PORT)d, \"%(DETECTOR)s\", " \
              "%(BUFFERS)d, %(MEMORY)d)" % self.__dict__


class ProcessPlugin(Device):

    """Virtual class for ProcessPlugins to inherit."""

    # Device attributes
    AutoInstantiate = True

    def create_config_file(self, **kwargs):
        raise NotImplementedError("Method must be implemented by child class")


class OdinControlServer(Device):

    """Store configuration for an OdinControlServer"""

    ODIN_SERVER = None
    ADAPTERS = ["fp", "fr"]

    # Device attributes
    AutoInstantiate = True

    def __init__(self, IP,
                 NODE_1_CTRL_IP, NODE_2_CTRL_IP, NODE_3_CTRL_IP, NODE_4_CTRL_IP,
                 NODE_5_CTRL_IP, NODE_6_CTRL_IP, NODE_7_CTRL_IP, NODE_8_CTRL_IP):
        self.__super.__init__()
        # Update attributes with parameters
        self.__dict__.update(locals())

        self.ips = [
            self.NODE_1_CTRL_IP, self.NODE_2_CTRL_IP, self.NODE_3_CTRL_IP, self.NODE_4_CTRL_IP,
            self.NODE_5_CTRL_IP, self.NODE_6_CTRL_IP, self.NODE_7_CTRL_IP, self.NODE_8_CTRL_IP
        ]

        self.create_odin_server_startup_scripts()
        self.create_odin_server_config_file()

    ArgInfo = makeArgInfo(__init__,
        IP=Simple("IP address of server", str),
        NODE_1_CTRL_IP=Simple("IP address for control of FR and FP", str),
        NODE_2_CTRL_IP=Simple("IP address for control of FR and FP", str),
        NODE_3_CTRL_IP=Simple("IP address for control of FR and FP", str),
        NODE_4_CTRL_IP=Simple("IP address for control of FR and FP", str),
        NODE_5_CTRL_IP=Simple("IP address for control of FR and FP", str),
        NODE_6_CTRL_IP=Simple("IP address for control of FR and FP", str),
        NODE_7_CTRL_IP=Simple("IP address for control of FR and FP", str),
        NODE_8_CTRL_IP=Simple("IP address for control of FR and FP", str)
    )

    def create_odin_server_startup_scripts(self):
        macros = dict(ODIN_SERVER=self.ODIN_SERVER, CONFIG="odin_server.cfg")
        expand_template_file("odin_server_startup", macros, "stOdinServer.sh", executable=True)

    def create_odin_server_config_file(self):
        macros = dict(ADAPTERS=", ".join(self.ADAPTERS),
                      ADAPTER_CONFIG="\n\n".join(self.create_odin_server_config_entries()))
        expand_template_file("odin_server.ini", macros, "odin_server.cfg")

    def create_odin_server_config_entries(self):
        raise NotImplementedError("Method must be implemented by child classes")

    def _create_odin_data_config_entry(self):
        fp_endpoints = []
        fr_endpoints = []
        server_count = {}
        for ip in self.ips:
            if ip is not None:
                if ip not in server_count:
                    server_count[ip] = 0
                fp_port_number = 5004 + (10 * server_count[ip])
                fr_port_number = 5000 + (10 * server_count[ip])
                server_count[ip] += 1
                fr_endpoints.append("{}:{}".format(ip, fr_port_number))
                fp_endpoints.append("{}:{}".format(ip, fp_port_number))

        return "[adapter.fp]\n" \
               "module = odin_data.frame_processor_adapter.FrameProcessorAdapter\n" \
               "endpoints = {}\n" \
               "update_interval = 0.2\n\n" \
               "[adapter.fr]\n" \
               "module = odin_data.odin_data_adapter.OdinDataAdapter\n" \
               "endpoints = {}\n" \
               "update_interval = 0.2".format(", ".join(fp_endpoints), ", ".join(fr_endpoints))
