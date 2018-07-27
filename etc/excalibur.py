import os

from iocbuilder import AutoSubstitution
from iocbuilder.arginfo import makeArgInfo, Simple, Ident, Choice
from iocbuilder.modules.ADCore import ADBaseTemplate, makeTemplateInstance

from odin import _OdinDetector, _OdinData, _OdinDataDriver, _OdinDataServer, _OdinControlServer, \
                 find_module_path, expand_template_file


EXCALIBUR, EXCALIBUR_PATH = find_module_path("excalibur-detector")
print("Excalibur: {} = {}".format(EXCALIBUR, EXCALIBUR_PATH))

EXCALIBUR_DIMENSIONS = {
    # Sensor: (Width, Height)
    "1M": (2048, 512),
    "3M": (2048, 1536)
}


class _ExcaliburOdinData(_OdinData):

    CONFIG_TEMPLATES = {
        "1M": {
            "FrameProcessor": "fp_excalibur.json",
            "FrameReceiver": "fr_excalibur_1m.json"
        },
        "3M": {
            "FrameProcessor": "fp_excalibur.json",
            "FrameReceiver": "fr_excalibur_3m.json"
        }
    }

    def __init__(self, IP, READY, RELEASE, META, SENSOR, BASE_UDP_PORT):
        super(_ExcaliburOdinData, self).__init__(IP, READY, RELEASE, META)
        self.sensor = SENSOR
        self.base_udp_port = BASE_UDP_PORT

    def create_config_files(self, index):
        macros = dict(PP_ROOT=EXCALIBUR_PATH,
                      RX_PORT_1=self.base_udp_port,
                      RX_PORT_2=self.base_udp_port + 1,
                      RX_PORT_3=self.base_udp_port + 2,
                      RX_PORT_4=self.base_udp_port + 3,
                      RX_PORT_5=self.base_udp_port + 4,
                      RX_PORT_6=self.base_udp_port + 5)

        super(_ExcaliburOdinData, self).create_config_file(
            "fp", self.CONFIG_TEMPLATES[self.sensor]["FrameProcessor"], index, extra_macros=macros)
        super(_ExcaliburOdinData, self).create_config_file(
            "fr", self.CONFIG_TEMPLATES[self.sensor]["FrameReceiver"], index, extra_macros=macros)


class ExcaliburOdinDataServer(_OdinDataServer):

    """Store configuration for an ExcaliburOdinDataServer"""
    ODIN_DATA_CLASS = _ExcaliburOdinData

    BASE_UDP_PORT = 61649

    def __init__(self, IP, PROCESSES, SENSOR, SHARED_MEM_SIZE=1048576000):
        self.sensor = SENSOR
        self.__super.__init__(IP, PROCESSES, SHARED_MEM_SIZE)

    ArgInfo = makeArgInfo(__init__,
        IP=Simple("IP address of server hosting OdinData processes", str),
        PROCESSES=Simple("Number of OdinData processes on this server", int),
        SENSOR=Choice("Sensor type", ["1M", "3M"]),
        SHARED_MEM_SIZE=Simple("Size of shared memory buffers in bytes", int)
    )

    def create_odin_data_process(self, ip, ready, release, meta):
        process = _ExcaliburOdinData(ip, ready, release, meta, self.sensor, self.BASE_UDP_PORT)
        self.BASE_UDP_PORT += 6
        return process


class ExcaliburOdinControlServer(_OdinControlServer):

    """Store configuration for an ExcaliburOdinControlServer"""

    ODIN_SERVER = os.path.join(EXCALIBUR_PATH, "prefix/bin/excalibur_odin")
    CONFIG_TEMPLATES = {
        "1M": {
            "chip_mask": "0xFF, 0xFF",
            "fem_addresses": ["192.168.0.101:6969", "192.168.0.102:6969"]
        },
        "3M": {
            "chip_mask": "0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF",
            "fem_addresses": ["192.168.0.101:6969", "192.168.0.102:6969", "192.168.0.103:6969",
                              "192.168.0.104:6969", "192.168.0.105:6969", "192.168.0.106:6969"]
        }
    }

    def __init__(self, IP, SENSOR, FEMS_REVERSED=False, POWER_CARD_IDX=1,
                 ODIN_DATA_SERVER_1=None, ODIN_DATA_SERVER_2=None, ODIN_DATA_SERVER_3=None,
                 ODIN_DATA_SERVER_4=None, ODIN_DATA_SERVER_5=None, ODIN_DATA_SERVER_6=None,
                 ODIN_DATA_SERVER_7=None, ODIN_DATA_SERVER_8=None):
        self.__dict__.update(locals())
        self.ADAPTERS.append("excalibur")

        super(ExcaliburOdinControlServer, self).__init__(
            IP,
            ODIN_DATA_SERVER_1, ODIN_DATA_SERVER_2, ODIN_DATA_SERVER_3, ODIN_DATA_SERVER_4,
            ODIN_DATA_SERVER_5, ODIN_DATA_SERVER_6, ODIN_DATA_SERVER_7, ODIN_DATA_SERVER_8
        )

    # __init__ arguments
    ArgInfo = makeArgInfo(__init__,
        IP=Simple("IP address of control server", str),
        SENSOR=Choice("Sensor type", ["1M", "3M"]),
        FEMS_REVERSED=Choice("Are the FEM IP addresses reversed 106..101", [True, False]),
        POWER_CARD_IDX=Simple("Index of the power card", int),
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
            self._create_excalibur_config_entry(fems=self.fem_address_list,
                                                powercard_idx=self.POWER_CARD_IDX,
                                                chip_enable_mask=self.chip_mask),
            self._create_odin_data_config_entry()
        ]

    def _create_excalibur_config_entry(self, fems, powercard_idx, chip_enable_mask):
        return "[adapter.excalibur]\n" \
               "module = excalibur.adapter.ExcaliburAdapter\n" \
               "detector_fems = {}\n" \
               "powercard_fem_idx = {}\n" \
               "chip_enable_mask = {}\n" \
               "update_interval = 0.5".format(fems, powercard_idx, chip_enable_mask)

    @property
    def fem_address_list(self):
        if self.FEMS_REVERSED:
            return ", ".join(reversed(self.CONFIG_TEMPLATES[self.SENSOR]["fem_addresses"]))
        else:
            return ", ".join(self.CONFIG_TEMPLATES[self.SENSOR]["fem_addresses"])

    @property
    def chip_mask(self):
        if self.SENSOR == "1M":
            return "0xFF, 0xFF"
        if self.SENSOR == "3M":
            return "0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF"


class _ExcaliburDetectorTemplate(AutoSubstitution):
    TemplateFile = "excaliburDetector.template"


class _ExcaliburFPTemplate(AutoSubstitution):
    TemplateFile = "excaliburFP.template"


def add_excalibur_fp_template(cls):
    """Convenience function to add excaliburFPTemplate attributes to a class that
    includes it via an msi include statement rather than verbatim"""
    template_substitutions = ["TOTAL", "ADDRESS"]

    cls.Arguments = _ExcaliburFPTemplate.Arguments + \
                    [x for x in cls.Arguments if x not in _ExcaliburFPTemplate.Arguments]
    cls.Arguments = [entry for entry in cls.Arguments if entry not in template_substitutions]

    cls.ArgInfo = _ExcaliburFPTemplate.ArgInfo + cls.ArgInfo.filtered(
        without=_ExcaliburFPTemplate.ArgInfo.Names())
    cls.ArgInfo = cls.ArgInfo.filtered(without=template_substitutions)

    cls.Defaults.update(_ExcaliburFPTemplate.Defaults)

    return cls


@add_excalibur_fp_template
class _Excalibur2NodeFPTemplate(AutoSubstitution):
    TemplateFile = "excalibur2NodeFP.template"


@add_excalibur_fp_template
class _Excalibur4NodeFPTemplate(AutoSubstitution):
    TemplateFile = "excalibur4NodeFP.template"


@add_excalibur_fp_template
class _Excalibur8NodeFPTemplate(AutoSubstitution):
    TemplateFile = "excalibur8NodeFP.template"


class ExcaliburOdinDataDriver(_OdinDataDriver):

    """Create an Excalibur OdinData driver"""

    FP_TEMPLATES = {
        # Number of OdinData nodes: Template
        2: _Excalibur2NodeFPTemplate,
        4: _Excalibur4NodeFPTemplate,
        8: _Excalibur8NodeFPTemplate
    }

    def __init__(self, **args):
        self.__super.__init__(**args)
        # Update the attributes of self from the commandline args
        self.__dict__.update(locals())

        if self.server_count not in self.FP_TEMPLATES.keys():
            raise ValueError("Total number of OdinData processes must be {}".format(
                self.FP_TEMPLATES.keys()))
        else:
            sensor = self.ODIN_DATA_PROCESSES[0].sensor 
            gui_name = args["PORT"][:args["PORT"].find(".")] + ".System"
            template_args = {
                "P": args["P"],
                "R": ":OD:",
                "DET": args["R"],
                "PORT": args["PORT"],
                "name": gui_name,
                "TIMEOUT": args["TIMEOUT"],
                "HEIGHT": EXCALIBUR_DIMENSIONS[sensor][1],
                "WIDTH": EXCALIBUR_DIMENSIONS[sensor][0]
            }
            _ExcaliburXNodeFPTemplate = self.FP_TEMPLATES[len(self.ODIN_DATA_PROCESSES)]
            _ExcaliburXNodeFPTemplate(**template_args)

    # __init__ arguments
    ArgInfo = _OdinDataDriver.ArgInfo + makeArgInfo(__init__)


class _ExcaliburFemHousekeepingTemplate(AutoSubstitution):
    TemplateFile = "excaliburFemHousekeeping.template"


class _ExcaliburFemStatusTemplate(AutoSubstitution):
    WarnMacros = False
    TemplateFile = "excaliburFemStatus.template"


def add_excalibur_fem_status(cls):
    """Convenience function to add excaliburFemStatusTemplate attributes to a class that
    includes it via an msi include statement rather than verbatim"""
    cls.Arguments = _ExcaliburFemStatusTemplate.Arguments + \
        [x for x in cls.Arguments if x not in _ExcaliburFemStatusTemplate.Arguments]
    cls.ArgInfo = _ExcaliburFemStatusTemplate.ArgInfo + cls.ArgInfo.filtered(
        without=_ExcaliburFemStatusTemplate.ArgInfo.Names())
    cls.Defaults.update(_ExcaliburFemStatusTemplate.Defaults)
    return cls


@add_excalibur_fem_status
class _Excalibur2FemStatusTemplate(AutoSubstitution):
    TemplateFile = "excalibur2FemStatus.template"


@add_excalibur_fem_status
class _Excalibur6FemStatusTemplate(AutoSubstitution):
    TemplateFile = "excalibur6FemStatus.template"


class ExcaliburDetector(_OdinDetector):

    """Create an Excalibur detector"""

    DETECTOR = "excalibur"
    SENSOR_OPTIONS = {  # (AutoSubstitution Template, Number of FEMs)
        "1M": (_Excalibur2FemStatusTemplate, 2),
        "3M": (_Excalibur6FemStatusTemplate, 6)
    }

    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = "PORT"

    _SpecificTemplate = _ExcaliburDetectorTemplate

    def __init__(self, PORT, ODIN_CONTROL_SERVER, SENSOR, BUFFERS=0, MEMORY=0,
                 NODE_1_NAME=None, NODE_1_MAC=None, NODE_1_IPADDR=None, NODE_1_PORT=None,
                 NODE_2_NAME=None, NODE_2_MAC=None, NODE_2_IPADDR=None, NODE_2_PORT=None,
                 NODE_3_NAME=None, NODE_3_MAC=None, NODE_3_IPADDR=None, NODE_3_PORT=None,
                 NODE_4_NAME=None, NODE_4_MAC=None, NODE_4_IPADDR=None, NODE_4_PORT=None,
                 NODE_5_NAME=None, NODE_5_MAC=None, NODE_5_IPADDR=None, NODE_5_PORT=None,
                 NODE_6_NAME=None, NODE_6_MAC=None, NODE_6_IPADDR=None, NODE_6_PORT=None,
                 NODE_7_NAME=None, NODE_7_MAC=None, NODE_7_IPADDR=None, NODE_7_PORT=None,
                 NODE_8_NAME=None, NODE_8_MAC=None, NODE_8_IPADDR=None, NODE_8_PORT=None,
                 **args):
        # Init the superclass (OdinDetector)
        self.__super.__init__(PORT, ODIN_CONTROL_SERVER, self.DETECTOR,
                              BUFFERS, MEMORY, **args)
        # Update the attributes of self from the commandline args
        self.__dict__.update(locals())
        # Make an instance of our template
        makeTemplateInstance(self._SpecificTemplate, locals(), args)

        # Add the FEM housekeeping template
        fem_hk_template = _ExcaliburFemHousekeepingTemplate
        fem_hk_args = {
            "P": args["P"],
            "R": args["R"],
            "PORT": PORT,
            "TIMEOUT": args["TIMEOUT"]
        }
        fem_hk_template(**fem_hk_args)

        assert SENSOR in self.SENSOR_OPTIONS.keys()
        # Instantiate template corresponding to SENSOR, passing through some of own args
        status_template = self.SENSOR_OPTIONS[SENSOR][0]
        gui_name = PORT[:PORT.find(".")] + ".Status"
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

        self.create_udp_file()

    def create_udp_file(self):
        names = [self.NODE_1_NAME, self.NODE_2_NAME, self.NODE_3_NAME, self.NODE_4_NAME,
                 self.NODE_5_NAME, self.NODE_6_NAME, self.NODE_7_NAME, self.NODE_8_NAME]
        macs = [self.NODE_1_MAC, self.NODE_2_MAC, self.NODE_3_MAC, self.NODE_4_MAC,
                self.NODE_5_MAC, self.NODE_6_MAC, self.NODE_7_MAC, self.NODE_8_MAC]
        ips = [self.NODE_1_IPADDR, self.NODE_2_IPADDR, self.NODE_3_IPADDR, self.NODE_4_IPADDR,
               self.NODE_5_IPADDR, self.NODE_6_IPADDR, self.NODE_7_IPADDR, self.NODE_8_IPADDR]
        ports = [self.NODE_1_PORT, self.NODE_2_PORT, self.NODE_3_PORT, self.NODE_4_PORT,
                 self.NODE_5_PORT, self.NODE_6_PORT, self.NODE_7_PORT, self.NODE_8_PORT]

        fem_config = []
        for offset in range(self.SENSOR_OPTIONS[self.SENSOR][1]):  # 2 for 1M or 6 for 3M
            index = offset + 1
            fem_config.append(
                #    "fems": [
                "        {{\n"
                "            \"name\": \"fem{index}\",\n"
                "            \"mac\": \"62:00:00:00:00:0{index}\",\n"
                "            \"ipaddr\": \"10.0.2.10{index}\",\n"
                "            \"port\": 6000{index},\n"
                "            \"dest_port_offset\": {offset}\n"
                "        }}".format(index=index, offset=offset)
                #    ...
                #    ]
            )

        number_of_nodes = 0
        node_config = []
        for name, mac, ip, port in zip(names, macs, ips, ports):
            if name is not None:
                node_config.append(
                    #    "nodes": [
                    "        {{\n"
                    "            \"name\": \"{}\",\n"
                    "            \"mac\": \"{}\",\n"
                    "            \"ipaddr\": \"{}\",\n"
                    "            \"port\": {}\n"
                    "        }}".format(name, mac, ip, port)
                    #    ...
                    #    ]
                )
                number_of_nodes += 1

        macros = dict(
            FEM_CONFIG=",\n".join(fem_config),
            NODE_CONFIG=",\n".join(node_config),
            NUM_DESTS=number_of_nodes
        )
        expand_template_file("udp_excalibur.json", macros, "udp_excalibur.json")

    # __init__ arguments
    ArgInfo = ADBaseTemplate.ArgInfo + _SpecificTemplate.ArgInfo + makeArgInfo(__init__,
        PORT=Simple("Port name for the detector", str),
        ODIN_CONTROL_SERVER=Ident("Odin control server instance", _OdinControlServer),
        SENSOR=Choice("Sensor type", ["1M", "3M"]),
        BUFFERS=Simple("Maximum number of NDArray buffers to be created for plugin callbacks", int),
        MEMORY=Simple("Max memory to allocate, should be maxw*maxh*nbuffer for driver and all "
                      "attached plugins", int),
        NODE_1_NAME=Simple("Name of detector output node 1", str),
        NODE_1_MAC=Simple("Mac address of detector output node 1", str),
        NODE_1_IPADDR=Simple("IP address of detector output node 1", str),
        NODE_1_PORT=Simple("Port of detector output node 1", int),
        NODE_2_NAME=Simple("Name of detector output node 2", str),
        NODE_2_MAC=Simple("Mac address of detector output node 2", str),
        NODE_2_IPADDR=Simple("IP address of detector output node 2", str),
        NODE_2_PORT=Simple("Port of detector output node 2", int),
        NODE_3_NAME=Simple("Name of detector output node 3", str),
        NODE_3_MAC=Simple("Mac address of detector output node 3", str),
        NODE_3_IPADDR=Simple("IP address of detector output node 3", str),
        NODE_3_PORT=Simple("Port of detector output node 3", int),
        NODE_4_NAME=Simple("Name of detector output node 4", str),
        NODE_4_MAC=Simple("Mac address of detector output node 4", str),
        NODE_4_IPADDR=Simple("IP address of detector output node 4", str),
        NODE_4_PORT=Simple("Port of detector output node 4", int),
        NODE_5_NAME=Simple("Name of detector output node 5", str),
        NODE_5_MAC=Simple("Mac address of detector output node 5", str),
        NODE_5_IPADDR=Simple("IP address of detector output node 5", str),
        NODE_5_PORT=Simple("Port of detector output node 5", int),
        NODE_6_NAME=Simple("Name of detector output node 6", str),
        NODE_6_MAC=Simple("Mac address of detector output node 6", str),
        NODE_6_IPADDR=Simple("IP address of detector output node 6", str),
        NODE_6_PORT=Simple("Port of detector output node 6", int),
        NODE_7_NAME=Simple("Name of detector output node 7", str),
        NODE_7_MAC=Simple("Mac address of detector output node 7", str),
        NODE_7_IPADDR=Simple("IP address of detector output node 7", str),
        NODE_7_PORT=Simple("Port of detector output node 7", int),
        NODE_8_NAME=Simple("Name of detector output node 8", str),
        NODE_8_MAC=Simple("Mac address of detector output node 8", str),
        NODE_8_IPADDR=Simple("IP address of detector output node 8", str),
        NODE_8_PORT=Simple("Port of detector output node 8", int)
    )
