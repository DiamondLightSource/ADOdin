import os

from iocbuilder import AutoSubstitution
from iocbuilder.arginfo import makeArgInfo, Simple, Ident, Choice
from iocbuilder.modules.ADCore import ADBaseTemplate, makeTemplateInstance

from util import find_module_path, expand_template_file, debug_print, create_config_entry
from odin import _OdinDetector, _OdinData, _OdinDataDriver, _OdinDataServer, _OdinControlServer, \
                 PluginConfig, FrameProcessorPlugin


TRISTAN, TRISTAN_PATH = find_module_path("tristan-detector")
debug_print("Tristan: {} = {}".format(TRISTAN, TRISTAN_PATH), 1)


TRISTAN_DIMENSIONS = {
    # Sensor: (Width, Height)
    "1M": (2048, 512),
    "10M": (4096, 2560)
}


class TristanOdinControlServer(_OdinControlServer):

    """Store configuration for an TristanOdinControlServer"""

    ODIN_SERVER = os.path.join(TRISTAN_PATH, "prefix/bin/tristan_odin")
    CONFIG_TEMPLATES = {
        "1M": {
            "chip_mask": "0xFF, 0xFF",
            "fem_addresses": ["192.168.0.101:6969", "192.168.0.102:6969"]
        },
        "10M": {
            "chip_mask": "0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF",
            "fem_addresses": ["192.168.0.101:6969", "192.168.0.102:6969", "192.168.0.103:6969",
                              "192.168.0.104:6969", "192.168.0.105:6969", "192.168.0.106:6969"]
        }
    }

    def __init__(self, IP, SENSOR, PORT=8888,
                 ODIN_DATA_SERVER_1=None, ODIN_DATA_SERVER_2=None,
                 ODIN_DATA_SERVER_3=None, ODIN_DATA_SERVER_4=None):
        self.__dict__.update(locals())
        self.ADAPTERS.append("tristan")

        super(TristanOdinControlServer, self).__init__(
            IP, PORT, ODIN_DATA_SERVER_1, ODIN_DATA_SERVER_2, ODIN_DATA_SERVER_3, ODIN_DATA_SERVER_4
        )

    # __init__ arguments
    ArgInfo = makeArgInfo(__init__,
        IP=Simple("IP address of control server", str),
        PORT=Simple("Port of control server", int),
        SENSOR=Choice("Sensor type", ["1M", "3M"]),
        ODIN_DATA_SERVER_1=Ident("OdinDataServer 1 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_2=Ident("OdinDataServer 2 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_3=Ident("OdinDataServer 3 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_4=Ident("OdinDataServer 4 configuration", _OdinDataServer)
    )

    def create_odin_server_config_entries(self):
        return [
            self._create_tristan_config_entry(),
            self._create_odin_data_config_entry()
        ]

    def create_odin_server_static_path(self):
        return TRISTAN_PATH + "/prefix/html/static"

    def _create_tristan_config_entry(self):
        return "[adapter.tristan]\n" \
               "module = latrd.detector.tristan_control_adapter.TristanControlAdapter\n" \
               "endpoint = tcp://127.0.0.1:5100\n" \
               "firmware = 0.0.1"


class _TristanDetectorTemplate(AutoSubstitution):
    TemplateFile = "TristanDetector.template"


class _TristanStatusTemplate(AutoSubstitution):
    WarnMacros = False
    TemplateFile = "TristanStatus.template"


def add_tristan_status(cls):
    """Convenience function to add tristanStatusTemplate attributes to a class that
    includes it via an msi include statement rather than verbatim"""
    cls.Arguments = _TristanStatusTemplate.Arguments + \
        [x for x in cls.Arguments if x not in _TristanStatusTemplate.Arguments]
    cls.ArgInfo = _TristanStatusTemplate.ArgInfo + cls.ArgInfo.filtered(
        without=_TristanStatusTemplate.ArgInfo.Names())
    cls.Defaults.update(_TristanStatusTemplate.Defaults)
    return cls


class _TristanFemStatusTemplate(AutoSubstitution):
    WarnMacros = False
    TemplateFile = "TristanFemStatus.template"


def add_tristan_fem_status(cls):
    """Convenience function to add tristanStatusTemplate attributes to a class that
    includes it via an msi include statement rather than verbatim"""
    cls.Arguments = _TristanFemStatusTemplate.Arguments + \
                    [x for x in cls.Arguments if x not in _TristanFemStatusTemplate.Arguments]
    cls.ArgInfo = _TristanFemStatusTemplate.ArgInfo + cls.ArgInfo.filtered(
        without=_TristanFemStatusTemplate.ArgInfo.Names())
    cls.Defaults.update(_TristanFemStatusTemplate.Defaults)
    return cls


@add_tristan_status
@add_tristan_fem_status
class _Tristan1MStatusTemplate(AutoSubstitution):
    TemplateFile = "Tristan1MStatus.template"


@add_tristan_status
@add_tristan_fem_status
class _Tristan10MStatusTemplate(AutoSubstitution):
    TemplateFile = "Tristan10MStatus.template"


class TristanDetector(_OdinDetector):

    """Create a Tristan detector"""

    DETECTOR = "tristan"
    SENSOR_OPTIONS = {  # (AutoSubstitution Template, Number of modules)
        "1M": (_Tristan1MStatusTemplate, 1),
        "10M": (_Tristan10MStatusTemplate, 10)
    }

    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = "PORT"

    _SpecificTemplate = _TristanDetectorTemplate

    # We don't really need the OdinDataDriver, but we need to know it is instantiated as it
    # defines the RANK on all the OdinData instances and we need to sort by RANK for the UDP config
    def __init__(self, PORT, ODIN_CONTROL_SERVER, ODIN_DATA_DRIVER, SENSOR,
                 BUFFERS=0, MEMORY=0, **args):
        # Init the superclass (OdinDetector)
        self.__super.__init__(PORT, ODIN_CONTROL_SERVER, self.DETECTOR,
                              BUFFERS, MEMORY, **args)
        # Update the attributes of self from the commandline args
        self.__dict__.update(locals())
        # Make an instance of our template
        makeTemplateInstance(self._SpecificTemplate, locals(), args)

        self.control_server = ODIN_CONTROL_SERVER

        # Add the housekeeping template
#        hk_template = _TristanHousekeepingTemplate
#        hk_args = {
#            "P": args["P"],
#            "R": args["R"],
#            "PORT": PORT,
#            "TIMEOUT": args["TIMEOUT"]
#        }
#        hk_template(**fem_hk_args)

        # Instantiate template corresponding to SENSOR, passing through some of own args
        status_template = self.SENSOR_OPTIONS[SENSOR][0]
        gui_name = PORT[:PORT.find(".")] + ".Detector"
        status_args = {
            "P": args["P"],
            "R": args["R"],
            "ADDRESS": "0",
            "PORT": PORT,
            "NAME": gui_name,
            "TIMEOUT": args["TIMEOUT"],
            "TOTAL": self.SENSOR_OPTIONS[SENSOR][1]
        }
        status_template(**status_args)

#        self.create_udp_file()
#
#    def create_udp_file(self):
#        fem_config = []
#        for offset in range(self.SENSOR_OPTIONS[self.SENSOR][1]):  # 2 for 1M or 6 for 3M
#            fem_config.append(
#                #    "fems": [
#                "        {{\n"
#                "            \"name\": \"fem{number}\",\n"
#                "            \"mac\": \"62:00:00:00:00:0{number}\",\n"
#                "            \"ipaddr\": \"10.0.2.10{number}\",\n"
#                "            \"port\": 6000{number},\n"
#                "            \"dest_port_offset\": {offset}\n"
#                "        }}".format(number=offset + 1, offset=offset)
#                #    ...
#                #    ]
#            )
#
#        node_config = []
#        for idx, process in enumerate(sorted(self.control_server.odin_data_processes,
#                                             key=lambda x: x.RANK)):
#            config = dict(
#                name="dest{}".format(idx + 1), mac=process.server.FEM_DEST_MAC,
#                ip=process.server.FEM_DEST_IP, port=process.base_udp_port
#            )
#            node_config.append(
#                #    "nodes": [
#                "        {{\n"
#                "            \"name\": \"{name}\",\n"
#                "            \"mac\": \"{mac}\",\n"
#                "            \"ipaddr\": \"{ip}\",\n"
#                "            \"port\": {port}\n"
#                "        }}".format(**config)
#                #    ...
#                #    ]
#            )
#
#        macros = dict(
#            FEM_CONFIG=",\n".join(fem_config),
#            NODE_CONFIG=",\n".join(node_config),
#            NUM_DESTS=len(self.control_server.odin_data_processes)
#        )
#        expand_template_file("udp_excalibur.json", macros, "udp_excalibur.json")

    # __init__ arguments
    ArgInfo = ADBaseTemplate.ArgInfo + _SpecificTemplate.ArgInfo + makeArgInfo(__init__,
        PORT=Simple("Port name for the detector", str),
        ODIN_CONTROL_SERVER=Ident("Odin control server instance", _OdinControlServer),
        ODIN_DATA_DRIVER=Ident("OdinDataDriver instance", _OdinDataDriver),
        SENSOR=Choice("Sensor type", SENSOR_OPTIONS.keys()),
        BUFFERS=Simple("Maximum number of NDArray buffers to be created for plugin callbacks", int),
        MEMORY=Simple("Max memory to allocate, should be maxw*maxh*nbuffer for driver and all "
                      "attached plugins", int)
    )


class _TristanOdinData(_OdinData):

    CONFIG_TEMPLATES = {
        "1M": {
            "FrameProcessor": "fp_tristan.json",
            "FrameReceiver": "fr_tristan_1m.json"
        },
        "10M": {
            "FrameProcessor": "fp_tristan.json",
            "FrameReceiver": "fr_tristan_10m.json"
        }
    }

    def __init__(self, server, READY, RELEASE, META, PLUGINS, SENSOR, BASE_UDP_PORT):
        super(_TristanOdinData, self).__init__(server, READY, RELEASE, META, PLUGINS)
        self.plugins = PLUGINS
        self.sensor = SENSOR
        self.base_udp_port = BASE_UDP_PORT

    def create_config_files(self, index):
        macros = dict(DETECTOR_ROOT=TRISTAN_PATH,
                      RX_PORT_1=self.base_udp_port,
                      RX_PORT_2=self.base_udp_port + 1,
                      RX_PORT_3=self.base_udp_port + 2,
                      RX_PORT_4=self.base_udp_port + 3,
                      WIDTH=TRISTAN_DIMENSIONS[self.sensor][0],
                      HEIGHT=TRISTAN_DIMENSIONS[self.sensor][1])

        if self.plugins is None:
            super(_TristanOdinData, self).create_config_file(
                "fp", self.CONFIG_TEMPLATES[self.sensor]["FrameProcessor"], extra_macros=macros)
        else:
            super(_TristanOdinData, self).create_config_file(
                "fp", "fp_custom.json", extra_macros=macros)

        super(_TristanOdinData, self).create_config_file(
            "fr", self.CONFIG_TEMPLATES[self.sensor]["FrameReceiver"], extra_macros=macros)


class TristanOdinDataServer(_OdinDataServer):

    """Store configuration for a TristanOdinDataServer"""

    BASE_UDP_PORT = 61649

    def __init__(self, IP, PROCESSES, SENSOR, FEM_DEST_MAC, FEM_DEST_IP="127.0.0.1",
                 SHARED_MEM_SIZE=1048576000, PLUGIN_CONFIG=None):
        self.sensor = SENSOR
        self.__super.__init__(IP, PROCESSES, SHARED_MEM_SIZE, PLUGIN_CONFIG)
        # Update attributes with parameters
        self.__dict__.update(locals())

    ArgInfo = makeArgInfo(__init__,
        IP=Simple("IP address of server hosting OdinData processes", str),
        PROCESSES=Simple("Number of OdinData processes on this server", int),
        SENSOR=Choice("Sensor type", ["1M", "10M"]),
        FEM_DEST_MAC=Simple("MAC address of node data link (destination for FEM to send to)", str),
        FEM_DEST_IP=Simple("IP address of node data link (destination for FEM to send to)", str),
        SHARED_MEM_SIZE=Simple("Size of shared memory buffers in bytes", int),
        PLUGIN_CONFIG=Ident("Define a custom set of plugins", PluginConfig)
    )

    def create_odin_data_process(self, server, ready, release, meta, plugin_config):
        process = _TristanOdinData(server, ready, release, meta, plugin_config, self.sensor, self.BASE_UDP_PORT)
        self.BASE_UDP_PORT += 1
        return process


class _TristanFPTemplate(AutoSubstitution):
    TemplateFile = "TristanOD.template"


def add_tristan_fp_template(cls):
    """Convenience function to add tristanFPTemplate attributes to a class that
    includes it via an msi include statement rather than verbatim"""
    template_substitutions = ["TOTAL", "ADDRESS"]

    cls.Arguments = _TristanFPTemplate.Arguments + \
                    [x for x in cls.Arguments if x not in _TristanFPTemplate.Arguments]
    cls.Arguments = [entry for entry in cls.Arguments if entry not in template_substitutions]

    cls.ArgInfo = _TristanFPTemplate.ArgInfo + cls.ArgInfo.filtered(
        without=_TristanFPTemplate.ArgInfo.Names())
    cls.ArgInfo = cls.ArgInfo.filtered(without=template_substitutions)

    cls.Defaults.update(_TristanFPTemplate.Defaults)

    return cls


@add_tristan_fp_template
class _Tristan4NodeFPTemplate(AutoSubstitution):
    TemplateFile = "Tristan4NodeOD.template"


@add_tristan_fp_template
class _Tristan8NodeFPTemplate(AutoSubstitution):
    TemplateFile = "Tristan8NodeOD.template"


class TristanOdinDataDriver(_OdinDataDriver):

    """Create a Tristan OdinData driver"""

    FP_TEMPLATES = {
        # Number of OdinData nodes: Template
        4: _Tristan4NodeFPTemplate,
        8: _Tristan8NodeFPTemplate
    }

    def __init__(self, **args):
        detector_arg = args["R"]
        args["R"] = ":OD:"
        self.__super.__init__(DETECTOR="tristan", **args)
        # Update the attributes of self from the commandline args
        self.__dict__.update(locals())

        if self.total_processes not in self.FP_TEMPLATES.keys():
            raise ValueError("Total number of OdinData processes must be {}".format(
                self.FP_TEMPLATES.keys()))
        else:
            sensor = self.ODIN_DATA_PROCESSES[0].sensor 
            gui_name = args["PORT"][:args["PORT"].find(".")] + ".OdinHDF"
            template_args = {
                "P": args["P"],
                "R": ":OD:",
                "DET": detector_arg,
                "PORT": args["PORT"],
                "name": gui_name,
                "TIMEOUT": args["TIMEOUT"],
                "HEIGHT": TRISTAN_DIMENSIONS[sensor][1],
                "WIDTH": TRISTAN_DIMENSIONS[sensor][0]
            }
            _TristanXNodeFPTemplate = self.FP_TEMPLATES[len(self.ODIN_DATA_PROCESSES)]
            _TristanXNodeFPTemplate(**template_args)

    # __init__ arguments
    ArgInfo = _OdinDataDriver.ArgInfo.filtered(without=["DETECTOR"])




