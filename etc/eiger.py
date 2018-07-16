import os

from iocbuilder.arginfo import makeArgInfo, Simple, Ident, Choice

from odin import OdinData, OdinDataServer, OdinControlServer, \
    find_module_path
from excalibur import EXCALIBUR_PATH


EIGER, EIGER_PATH = find_module_path("eiger-detector")
print("Eiger: {} = {}".format(EIGER, EIGER_PATH))


class EigerOdinData(OdinData):

    CONFIG_TEMPLATES = {
        "FrameProcessor": "fp_eiger.json",
        "FrameReceiver": "fr_eiger.json"
    }

    def __init__(self, IP, READY, RELEASE, META, SOURCE_IP):
        super(EigerOdinData, self).__init__(IP, READY, RELEASE, META)
        self.source = SOURCE_IP

    def create_config_files(self, index):
        macros = dict(PP_ROOT=EIGER_PATH,
                      IP=self.source)

        super(EigerOdinData, self).create_config_file(
            "fp", self.CONFIG_TEMPLATES["FrameProcessor"], index, extra_macros=macros)
        super(EigerOdinData, self).create_config_file(
            "fr", self.CONFIG_TEMPLATES["FrameReceiver"], index, extra_macros=macros)


class EigerOdinDataServer(OdinDataServer):

    """Store configuration for an EigerOdinDataServer"""
    ODIN_DATA_CLASS = EigerOdinData

    def __init__(self, IP, PROCESSES, SOURCE_IP, SHARED_MEM_SIZE=16000000000):
        self.source = SOURCE_IP
        self.__super.__init__(IP, PROCESSES, SHARED_MEM_SIZE)

    ArgInfo = makeArgInfo(__init__,
        IP=Simple("IP address of server hosting processes", str),
        PROCESSES=Simple("Number of OdinData processes on this server", int),
        SOURCE_IP=Simple("IP address of data stream from Eiger detector", str),
        SHARED_MEM_SIZE=Simple("Size of shared memory buffers in bytes", int)
    )

    def create_odin_data_process(self, ip, ready, release, meta, *args):
        return super(EigerOdinDataServer, self).create_odin_data_process(
            ip, ready, release, meta, self.source, *args)


class EigerOdinControlServer(OdinControlServer):

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
        IP=Simple("IP address of server hosting processes", str),
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
