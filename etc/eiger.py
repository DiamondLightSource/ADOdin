import os

from iocbuilder import Device
from iocbuilder.arginfo import makeArgInfo, Simple, Ident, Choice

from odin import _OdinData, _OdinDataServer, _OdinControlServer, \
    find_module_path, expand_template_file
from excalibur import EXCALIBUR_PATH


EIGER, EIGER_PATH = find_module_path("eiger-detector")
print("Eiger: {} = {}".format(EIGER, EIGER_PATH))


class _EigerOdinData(_OdinData):

    CONFIG_TEMPLATES = {
        "FrameProcessor": "fp_eiger.json",
        "FrameReceiver": "fr_eiger.json"
    }

    def __init__(self, IP, READY, RELEASE, META, SOURCE_IP):
        super(_EigerOdinData, self).__init__(IP, READY, RELEASE, META)
        self.source = SOURCE_IP

    def create_config_files(self, index):
        macros = dict(PP_ROOT=EIGER_PATH,
                      IP=self.source)

        super(_EigerOdinData, self).create_config_file(
            "fp", self.CONFIG_TEMPLATES["FrameProcessor"], index, extra_macros=macros)
        super(_EigerOdinData, self).create_config_file(
            "fr", self.CONFIG_TEMPLATES["FrameReceiver"], index, extra_macros=macros)


class EigerOdinDataServer(_OdinDataServer):

    """Store configuration for an EigerOdinDataServer"""
    ODIN_DATA_CLASS = _EigerOdinData

    def __init__(self, IP, PROCESSES, SOURCE_IP, SHARED_MEM_SIZE=16000000000):
        self.source = SOURCE_IP
        self.__super.__init__(IP, PROCESSES, SHARED_MEM_SIZE)

    ArgInfo = makeArgInfo(__init__,
        IP=Simple("IP address of server hosting OdinData processes", str),
        PROCESSES=Simple("Number of OdinData processes on this server", int),
        SOURCE_IP=Simple("IP address of data stream from Eiger detector", str),
        SHARED_MEM_SIZE=Simple("Size of shared memory buffers in bytes", int)
    )

    def create_odin_data_process(self, ip, ready, release, meta, *args):
        return super(EigerOdinDataServer, self).create_odin_data_process(
            ip, ready, release, meta, self.source, *args)


class EigerOdinControlServer(_OdinControlServer):

    """Store configuration for an EigerOdinControlServer"""

    ODIN_SERVER = os.path.join(EXCALIBUR_PATH, "prefix/bin/excalibur_odin")

    def __init__(self, IP,
                 NODE_1_CTRL_IP = None, NODE_2_CTRL_IP = None, NODE_3_CTRL_IP = None,
                 NODE_4_CTRL_IP = None, NODE_5_CTRL_IP = None, NODE_6_CTRL_IP = None,
                 NODE_7_CTRL_IP = None, NODE_8_CTRL_IP = None):
        self.__dict__.update(locals())

        super(EigerOdinControlServer, self).__init__(
            IP,
            NODE_1_CTRL_IP, NODE_2_CTRL_IP, NODE_3_CTRL_IP, NODE_4_CTRL_IP,
            NODE_5_CTRL_IP, NODE_6_CTRL_IP, NODE_7_CTRL_IP, NODE_8_CTRL_IP
        )

    # __init__ arguments
    ArgInfo = makeArgInfo(__init__,
        IP=Simple("IP address of control server", str),
        NODE_1_CTRL_IP=Simple("IP address for control of FR and FP", str),
        NODE_2_CTRL_IP=Simple("IP address for control of FR and FP", str),
        NODE_3_CTRL_IP=Simple("IP address for control of FR and FP", str),
        NODE_4_CTRL_IP=Simple("IP address for control of FR and FP", str),
        NODE_5_CTRL_IP=Simple("IP address for control of FR and FP", str),
        NODE_6_CTRL_IP=Simple("IP address for control of FR and FP", str),
        NODE_7_CTRL_IP=Simple("IP address for control of FR and FP", str),
        NODE_8_CTRL_IP=Simple("IP address for control of FR and FP", str)
    )

    def create_odin_server_config_entries(self):
        return [
            self._create_odin_data_config_entry()
        ]


class EigerFan(Device):

    """Create startup file for an EigerFan process"""

    # Device attributes
    AutoInstantiate = True

    def __init__(self, IP, PROCESSES, SOCKETS, BLOCK_SIZE=1):
        self.__super.__init__()
        # Update attributes with parameters
        self.__dict__.update(locals())

        self.create_startup_file()

    def create_startup_file(self):
        macros = dict(EIGER_DETECTOR_PATH=EIGER_PATH, IP=self.IP,
                      PROCESSES=self.PROCESSES, SOCKETS=self.SOCKETS, BLOCK_SIZE=self.BLOCK_SIZE,
                      LOG_CONFIG=os.path.join(EIGER_PATH, "log4cxx.xml"))

        expand_template_file("eiger_fan_startup", macros, "stEigerFan.sh")

    # __init__ arguments
    ArgInfo = makeArgInfo(__init__,
        IP=Simple("IP address of Eiger detector", str),
        PROCESSES=Simple("Number of processes to fan out to", int),
        SOCKETS=Simple("Number of sockets to open to Eiger detector stream", int),
        BLOCK_SIZE=Simple("Number of blocks per file", int)
    )


class EigerMetaListener(Device):

    """Create startup file for an EigerMetaListener process"""

    # Device attributes
    AutoInstantiate = True

    def __init__(self, BLOCK_SIZE=1,
                 ODIN_DATA_SERVER_1=None, ODIN_DATA_SERVER_2=None, ODIN_DATA_SERVER_3=None,
                 ODIN_DATA_SERVER_4=None, ODIN_DATA_SERVER_5=None, ODIN_DATA_SERVER_6=None,
                 ODIN_DATA_SERVER_7=None, ODIN_DATA_SERVER_8=None):
        self.__super.__init__()
        # Update attributes with parameters
        self.__dict__.update(locals())

        self.ip_list = []
        for idx in range(1, 9):
            server = eval("ODIN_DATA_SERVER_{}".format(idx))
            if server is not None:
                base_port = 5000
                for odin_data in server.processes:
                    port = base_port + 558
                    self.ip_list.append("tcp://{}:{}".format(odin_data.IP, port))
                    base_port += 1000

        self.create_startup_file()

    def create_startup_file(self):
        macros = dict(EIGER_DETECTOR_PATH=EIGER_PATH,
                      IP_LIST=",".join(self.ip_list),
                      BLOCK_SIZE=self.BLOCK_SIZE)

        expand_template_file("eiger_meta_startup", macros, "stEigerMetaListener.sh")

    # __init__ arguments
    ArgInfo = makeArgInfo(__init__,
        BLOCK_SIZE=Simple("Number of blocks per file", int),
        ODIN_DATA_SERVER_1=Ident("OdinDataServer 1 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_2=Ident("OdinDataServer 2 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_3=Ident("OdinDataServer 3 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_4=Ident("OdinDataServer 4 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_5=Ident("OdinDataServer 5 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_6=Ident("OdinDataServer 6 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_7=Ident("OdinDataServer 7 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_8=Ident("OdinDataServer 8 configuration", _OdinDataServer)
    )
