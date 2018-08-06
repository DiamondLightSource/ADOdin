import os

from iocbuilder import Device, AutoSubstitution
from iocbuilder.arginfo import makeArgInfo, Simple, Ident, Choice
from iocbuilder.modules.ADCore import makeTemplateInstance

from odin import _OdinData, _OdinDataDriver, _OdinDataServer, _OdinControlServer, \
    find_module_path, expand_template_file
from excalibur import EXCALIBUR_PATH


EIGER, EIGER_PATH = find_module_path("eiger-detector")
print("Eiger: {} = {}".format(EIGER, EIGER_PATH))


class EigerFan(Device):

    """Create startup file for an EigerFan process"""

    # Device attributes
    AutoInstantiate = True

    def __init__(self, IP, DETECTOR_IP, PROCESSES, SOCKETS, BLOCK_SIZE=1):
        self.__super.__init__()
        # Update attributes with parameters
        self.__dict__.update(locals())

        self.create_startup_file()

    def create_startup_file(self):
        macros = dict(EIGER_DETECTOR_PATH=EIGER_PATH, IP=self.DETECTOR_IP,
                      PROCESSES=self.PROCESSES, SOCKETS=self.SOCKETS, BLOCK_SIZE=self.BLOCK_SIZE,
                      LOG_CONFIG=os.path.join(EIGER_PATH, "log4cxx.xml"))

        expand_template_file("eiger_fan_startup", macros, "stEigerFan.sh",
                             executable=True)

    # __init__ arguments
    ArgInfo = makeArgInfo(__init__,
        IP=Simple("IP address server hosting process", str),
        DETECTOR_IP=Simple("IP address of Eiger detector", str),
        PROCESSES=Simple("Number of processes to fan out to", int),
        SOCKETS=Simple("Number of sockets to open to Eiger detector stream", int),
        BLOCK_SIZE=Simple("Number of blocks per file", int)
    )


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
                      IP=self.source,
                      PORT_SUFFIX=index - 1)

        super(_EigerOdinData, self).create_config_file(
            "fp", self.CONFIG_TEMPLATES["FrameProcessor"], index, extra_macros=macros)
        super(_EigerOdinData, self).create_config_file(
            "fr", self.CONFIG_TEMPLATES["FrameReceiver"], index, extra_macros=macros)


class EigerOdinDataServer(_OdinDataServer):

    """Store configuration for an EigerOdinDataServer"""

    def __init__(self, IP, PROCESSES, SOURCE, SHARED_MEM_SIZE=16000000000):
        self.source = SOURCE.IP
        self.__super.__init__(IP, PROCESSES, SHARED_MEM_SIZE)

    ArgInfo = makeArgInfo(__init__,
        IP=Simple("IP address of server hosting OdinData processes", str),
        PROCESSES=Simple("Number of OdinData processes on this server", int),
        SOURCE=Ident("EigerFan instance", EigerFan),
        SHARED_MEM_SIZE=Simple("Size of shared memory buffers in bytes", int)
    )

    def create_odin_data_process(self, ip, ready, release, meta):
        return _EigerOdinData(ip, ready, release, meta, self.source)


class EigerOdinControlServer(_OdinControlServer):

    """Store configuration for an EigerOdinControlServer"""

    ODIN_SERVER = os.path.join(EXCALIBUR_PATH, "prefix/bin/excalibur_odin")

    def __init__(self, IP,
                 ODIN_DATA_SERVER_1=None, ODIN_DATA_SERVER_2=None, ODIN_DATA_SERVER_3=None,
                 ODIN_DATA_SERVER_4=None, ODIN_DATA_SERVER_5=None, ODIN_DATA_SERVER_6=None,
                 ODIN_DATA_SERVER_7=None, ODIN_DATA_SERVER_8=None):
        self.__dict__.update(locals())

        super(EigerOdinControlServer, self).__init__(
            IP,
            ODIN_DATA_SERVER_1, ODIN_DATA_SERVER_2, ODIN_DATA_SERVER_3, ODIN_DATA_SERVER_4,
            ODIN_DATA_SERVER_5, ODIN_DATA_SERVER_6, ODIN_DATA_SERVER_7, ODIN_DATA_SERVER_8
        )

    # __init__ arguments
    ArgInfo = makeArgInfo(__init__,
        IP=Simple("IP address of control server", str),
        ODIN_DATA_SERVER_1=Ident("OdinDataServer 1 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_2=Ident("OdinDataServer 2 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_3=Ident("OdinDataServer 3 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_4=Ident("OdinDataServer 4 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_5=Ident("OdinDataServer 5 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_6=Ident("OdinDataServer 6 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_7=Ident("OdinDataServer 7 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_8=Ident("OdinDataServer 8 configuration", _OdinDataServer)
    )

    def create_odin_server_config_entries(self):
        return [
            self._create_odin_data_config_entry()
        ]


class _EigerDetectorTemplate(AutoSubstitution):
    """A template file that simply exposes an EDM screen with P and R macros"""
    TemplateFile = "eigerDetector.template"


class EigerOdinDataDriver(_OdinDataDriver):

    """Create an Eiger OdinData driver"""

    def __init__(self, **args):
        self.__super.__init__(DETECTOR="eiger", **args)
        # Update the attributes of self from the commandline args
        self.__dict__.update(locals())

        template_args = dict((key, args[key]) for key in ["P", "R", "PORT"])
        makeTemplateInstance(_EigerDetectorTemplate, locals(), template_args)

    # __init__ arguments
    ArgInfo = _OdinDataDriver.ArgInfo.filtered(without=["DETECTOR"])


class EigerMetaListener(Device):

    """Create startup file for an EigerMetaListener process"""

    # Device attributes
    AutoInstantiate = True

    def __init__(self, SENSOR, BLOCK_SIZE=1,
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
                      SENSOR=self.SENSOR,
                      BLOCK_SIZE=self.BLOCK_SIZE)

        expand_template_file("eiger_meta_startup", macros, "stEigerMetaListener.sh",
                             executable=True)

    # __init__ arguments
    ArgInfo = makeArgInfo(__init__,
        SENSOR=Choice("Sensor type", ["4M"]),
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
