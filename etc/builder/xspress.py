import os

from iocbuilder import AutoSubstitution
from iocbuilder.arginfo import makeArgInfo, Simple, Ident, Choice
from iocbuilder.modules.ADCore import ADBaseTemplate, makeTemplateInstance

from util import (
    OdinPaths,
    expand_template_file,
    debug_print,
    create_config_entry,
    OneLineEntry,
)
from odin import (
    _OdinDetector,
    _OdinData,
    _OdinDataDriver,
    _OdinDataServer,
    _OdinControlServer,
    _MetaWriter,
    _PluginConfig,
    OdinProcServ,
    _FrameProcessorPlugin,
)
from plugins import (
    _LiveViewPlugin,
    _OffsetAdjustmentPlugin,
    _UIDAdjustmentPlugin,
    _SumPlugin,
    _BloscPlugin,
    _FileWriterPlugin,
    _DatasetCreationPlugin,
)


debug_print(
    "Xspress: \n{}\n{}".format(OdinPaths.XSPRESS_TOOL, OdinPaths.XSPRESS_PYTHON),
    1
)


class XspressOdinProcServ(OdinProcServ):

    @property
    def extra_applications(self):
        return ["ControlServer"]

class _XspressProcessPlugin(_DatasetCreationPlugin):

    NAME = "xspress"
    CLASS_NAME = "XspressProcessPlugin"
    LIBRARY_PATH = OdinPaths.XSPRESS_TOOL
    DATASETS = [
        dict(name="compressed_size", datatype="uint32")
    ]

    def __init__(self, size_dataset):
        super(_XspressProcessPlugin, self).__init__(None)

        self.size_dataset = size_dataset

    def create_extra_config_entries(self, rank, total):
        entries = []
        if self.size_dataset:
            entries = super(_XspressProcessPlugin, self).create_extra_config_entries(rank, total)

        return entries

class XspressPlugins(_PluginConfig):
    """Plugin Singleton"""
    _instance = None
    def __init__(self):
        if self._instance:
            return self._instance
        xspress_plugin = _XspressProcessPlugin(size_dataset=False)
        live_plugin = _LiveViewPlugin(source=xspress_plugin)
        blosc_plugin = _BloscPlugin(source=live_plugin)
        fw_plugin = _FileWriterPlugin(source=blosc_plugin)
        
        self._instance = super(XspressPlugins, self).__init__(
            PLUGIN_1=xspress_plugin,
            PLUGIN_2=live_plugin,
            PLUGIN_3=blosc_plugin,
            PLUGIN_4=fw_plugin,
        )
        return self._instance
        



class _XspressOdinData(_OdinData):

    CONFIG_TEMPLATES = {
        "36CHAN": {
            "FrameProcessor": "fp_xspress.json",
            "FrameReceiver": "fr_xspress.json"
        }
    }
    fp_template = "fp_xspress.json"
    fr_template = "fr_xspress.json"
    hdf_postfix = ["_A", "_B", "_C", "_D", "_E", "_F", "_G", "_H", "_I"]
    chans_per_processs_mca = 4
    chans_per_processs_list = 5
    base_rx_port = 15150
    base_lv_port = 15500



    def __init__(self, server, READY, RELEASE, META, SENSOR):
        super(_XspressOdinData, self).__init__(server, READY, RELEASE, META, XspressPlugins())
        self.sensor = SENSOR

    def create_config_files(self, index, total):
        zero_idx = index - 1
        base_mca = zero_idx * self.chans_per_processs_mca
        base_list = zero_idx * self.chans_per_processs_list
        macros = dict(DETECTOR_ROOT=OdinPaths.XSPRESS_TOOL,
                      HDF_POSTFIX = self.hdf_postfix[zero_idx],
                      MCA1 = base_mca,
                      MCA2 = base_mca + 1,
                      MCA3 = base_mca + 2,
                      MCA4 = base_mca + 3,
                      LIST1 = base_list,
                      LIST2 = base_list + 1,
                      LIST3 = base_list + 2,
                      LIST4 = base_list + 3,
                      LIST5 = base_list + 4,
                      RX_PORT = self.base_rx_port + zero_idx,
                      LV_PORT = self.base_lv_port + zero_idx)

        # Generate the frame processor config files
        super(_XspressOdinData, self).create_config_file(
            "fp", self.fp_template, extra_macros=macros
        )

        # Generate the frame receiver config files
        super(_XspressOdinData, self).create_config_file(
            "fr", self.fr_template, extra_macros=macros
        )

class XspressOdinDataServer(_OdinDataServer):

    """Store configuration for a XspressOdinDataServer"""

    def __init__(self, IP, PROCESSES, SENSOR, SHARED_MEM_SIZE=1048576000, PLUGIN_CONFIG=None):
        self.sensor = SENSOR
        self.__super.__init__(IP, PROCESSES, SHARED_MEM_SIZE, XspressPlugins())
        # Update attributes with parameters
        self.__dict__.update(locals())

    ArgInfo = makeArgInfo(__init__,
        IP=Simple("IP address of server hosting OdinData processes", str),
        PROCESSES=Simple("Number of OdinData processes on this server", int),
        SENSOR=Choice("Sensor type", ["36CHAN",]),
        SHARED_MEM_SIZE=Simple("Size of shared memory buffers in bytes", int),
        PLUGIN_CONFIG=Ident("Define a custom set of plugins", _PluginConfig)
    )

    def create_odin_data_process(self, server, ready, release, meta, plugin_config):
        process = _XspressOdinData(server, ready, release, meta, self.sensor)
        return process

class XspressOdinControlServer(_OdinControlServer):

    """Store configuration for an ArcOdinControlServer"""

    ODIN_SERVER = os.path.join(OdinPaths.XSPRESS_PYTHON, "bin/xspress_control")
    PYTHON_MODULES = {}
    DAQ_ENDPOINTS = [
        "tcp://127.0.0.1:15150",
        "tcp://127.0.0.1:15151",
        "tcp://127.0.0.1:15152",
        "tcp://127.0.0.1:15153",
        "tcp://127.0.0.1:15154",
        "tcp://127.0.0.1:15155",
        "tcp://127.0.0.1:15156",
        "tcp://127.0.0.1:15157",
        "tcp://127.0.0.1:15158"
    ]

    def __init__(
        self,
        SETTINGS_PATH,
        IP="127.0.0.1",
        PORT=8888,
        BASE_IP="192.168.0.1",
        NUM_CARDS=4,
        MAX_CHANNELS=36,
        MAX_SPECTRA=4096,
        NUM_TF=16384,
        RUN_FLAGS=2,
        HARDWARE_ENDPOINT="127.0.0.1:12000",
        DEBUG=1,
        META_WRITER_IP="127.0.0.1",
        ODIN_DATA_SERVER_1=None,
        ODIN_DATA_SERVER_2=None,
        ODIN_DATA_SERVER_3=None,
        ODIN_DATA_SERVER_4=None,
    ):
        self.__dict__.update(locals())
        self.ADAPTERS.append("xsp")

        super(XspressOdinControlServer, self).__init__(
            IP,
            PORT,
            META_WRITER_IP,
            ODIN_DATA_SERVER_1,
            ODIN_DATA_SERVER_2,
            ODIN_DATA_SERVER_3,
            ODIN_DATA_SERVER_4,
        )
        self.create_wrapper_start_up_script_and_config()

    # __init__ arguments
    ArgInfo = makeArgInfo(
        __init__,
        IP=Simple("IP address of control server", str),
        PORT=Simple("Port of control server", int),
        HARDWARE_ENDPOINT=Simple("Control Application endpoint", str),
        MAX_CHANNELS=Simple("Number of channels in the Xspress", int),
        MAX_SPECTRA=Simple("Number of Energy bins (max/default = 4096)", int),
        NUM_TF=Simple("Buffer size for incomming time frames (should not be changed)", int),
        NUM_CARDS=Simple("Number of Xspress devices in the chain", int),
        RUN_FLAGS=Simple("0: Scalars & Histogram, 1: Scalars, 2: Play Back", int),
        BASE_IP=Simple("Xspress base address", str),
        SETTINGS_PATH=Simple( "Path to the Xspress settings directory to upload to the device", str),
        DEBUG=Simple("Turn on support library debugging", int),
        META_WRITER_IP=Simple(
            "IP address of MetaWriter (None -> first OdinDataServer)", str
        ),
        ODIN_DATA_SERVER_1=Ident("OdinDataServer 1 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_2=Ident("OdinDataServer 2 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_3=Ident("OdinDataServer 3 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_4=Ident("OdinDataServer 4 configuration", _OdinDataServer),
    )


    def _add_python_modules(self):
        # return nothing since the python3 venv for xspress odin server already has the
        # required dependencies
        pass

    def get_extra_startup_macro(self):
        return ""
        return (
            "--staticlogfields beamline=${BEAMLINE},"
            'application_name="xspress_odin",detector="Xspress" '
            '--logserver="graylog2.diamond.ac.uk:12210" --access_logging=ERROR'
        )

    def create_odin_server_config_entries(self):
        '''
        TODO: undo this method override
        '''
        return [self._create_xspress_config_entry(),
                self._create_odin_data_config_entry(),
                self._create_meta_writer_config_entry()]

    def create_odin_server_static_path(self):
        return OdinPaths.XSPRESS_TOOL + "/example-config/static"

    def _create_xspress_config_entry(self):
        config_entry = "\n".join(
            [
                "[adapter.xsp]",
                "module = xspress_detector.control.adapter.XspressAdapter",
                "endpoint = {}".format(self.HARDWARE_ENDPOINT),
                "num_cards = {}".format(self.NUM_CARDS),
                "num_tf = {}".format(self.NUM_TF),
                "base_ip = {}".format(self.BASE_IP),
                "max_channels = {}".format(self.MAX_CHANNELS),
                "max_spectra = {}".format(self.MAX_SPECTRA),
                "settings_path = {}".format(self.SETTINGS_PATH),
                "run_flags = {}".format(self.RUN_FLAGS),
                "debug = {}".format(self.DEBUG),
                "daq_endpoints = {}".format(",".join(self.DAQ_ENDPOINTS)),
            ]
        )
        print "-------------------\n"
        print config_entry
        print "-------------------\n"
        return config_entry

    def _create_odin_data_config_entry(self):
        return """
[adapter.fp]
module = xspress_detector.control.fp_xspress_adapter.FPXspressAdapter
endpoints = 127.0.0.1:10004, 127.0.0.1:10014, 127.0.0.1:10024, 127.0.0.1:10034, 127.0.0.1:10044, 127.0.0.1:10054, 127.0.0.1:10064, 127.0.0.1:10074, 127.0.0.1:10084
update_interval = 0.2

[adapter.fr]
module = odin_data.control.frame_receiver_adapter.FrameReceiverAdapter
endpoints = 127.0.0.1:10000, 127.0.0.1:10010, 127.0.0.1:10020, 127.0.0.1:10030, 127.0.0.1:10040, 127.0.0.1:10050, 127.0.0.1:10060, 127.0.0.1:10070, 127.0.0.1:10080
update_interval = 0.2
"""
    def create_wrapper_start_up_script_and_config(self):
        macros = dict(XSPRESS_DETECTOR=OdinPaths.XSPRESS_TOOL)
        expand_template_file("xspress_control_server_start_up.sh", macros, "stControlServer.sh", executable=True)
        expand_template_file("xspress_control_server_config.json", {}, "xspress.json")



# ~~~~~~~~~~~~ 
class XspressMetaWriter(_MetaWriter):
    DETECTOR = "Xspress"
    WRITER_CLASS = "xspress_detector.data.xspress_meta_writer.XspressMetaWriter"
    APP_PATH = OdinPaths.XSPRESS_PYTHON
    APP_NAME = "xspress_meta_writer"


# ~~~~~~~~~~~~ #
# AreaDetector #
# ~~~~~~~~~~~~ #

class XspressOdinDataDriver(_OdinDataDriver):

    def __init__(self, **args):
        meta_class = XspressMetaWriter
        num_channels = args["ODIN_CONTROL_SERVER"].MAX_CHANNELS
        max_spectra = args["ODIN_CONTROL_SERVER"].MAX_SPECTRA
        meta_class.SENSOR_SHAPE = [num_channels, max_spectra]
        self.META_WRITER_CLASS = meta_class
        args["R"] = ":OD:"
        self.__super.__init__(DETECTOR="xsp", **args)



class _XspressDetectorTemplate(AutoSubstitution):
    TemplateFile = "XspressDetector.template"

class _XspressChannelTemplate(AutoSubstitution):
    TemplateFile = "XspressChannel.template"

class _XspressFemTemplate(AutoSubstitution):
    TemplateFile = "XspressFem.template"

class XspressDetector(_OdinDetector):

    """Create an Xspress EPICS client detector"""

    DETECTOR = "xsp"

    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = "PORT"

    _SpecificTemplate = _XspressDetectorTemplate

    # We don't really need the OdinDataDriver, but we need to know it is instantiated as it
    # defines the RANK on all the OdinData instances and we need to sort by RANK for the UDP config
    def __init__(
        self,
        PORT,
        ODIN_CONTROL_SERVER,
        ODIN_DATA_DRIVER,
        BUFFERS=0,
        MEMORY=0,
        **args
    ):
        args["R"] = ":CAM:"
        # Init the superclass (OdinDetector)
        self.__super.__init__(
            PORT, ODIN_CONTROL_SERVER, self.DETECTOR, BUFFERS, MEMORY, **args
        )
        # Update the attributes of self from the commandline args
        self.__dict__.update(locals())
        # Make an instance of our template
        makeTemplateInstance(self._SpecificTemplate, locals(), args)
        self.control_server = ODIN_CONTROL_SERVER

        for i in range(self.control_server.MAX_CHANNELS):
            specific = dict(TOTAL=self.control_server.MAX_CHANNELS,
                            ADDR=i,
                            CHAN=i+1,
                            P = args["P"],
                            R = args["R"],
                            TIMEOUT = args["TIMEOUT"],
                            PORT = PORT)
            _XspressChannelTemplate(**specific)

        for i in range(self.control_server.NUM_CARDS):
            specific = dict(TOTAL=self.control_server.NUM_CARDS,
                            ADDR=i,
                            P = args["P"],
                            R = args["R"],
                            TIMEOUT = args["TIMEOUT"],
                            PORT = PORT)
            _XspressFemTemplate(**specific)

        self.create_live_startup_script()



    # __init__ arguments
    ArgInfo = (
        ADBaseTemplate.ArgInfo
        + _SpecificTemplate.ArgInfo
        + makeArgInfo(
            __init__,
            PORT=Simple("Port name for the detector", str),
            ODIN_CONTROL_SERVER=Ident(
                "Odin control server instance", _OdinControlServer
            ),
            ODIN_DATA_DRIVER=Ident("OdinDataDriver instance", _OdinDataDriver),
            BUFFERS=Simple(
                "Maximum number of NDArray buffers to be created for plugin callbacks",
                int,
            ),
            MEMORY=Simple(
                "Max memory to allocate, should be maxw*maxh*nbuffer for driver and all "
                "attached plugins",
                int,
            ),
        )
    )
    ArgInfo = ArgInfo.filtered(without=["R"])

    def create_live_startup_script(self):

        macros = dict(
            XSPRESS_APP=os.path.join(OdinPaths.XSPRESS_PYTHON, "bin/xspress_live_merge")
        )
        expand_template_file("xspress_live_startup", macros, "stLiveViewMerge.sh", executable=True)
