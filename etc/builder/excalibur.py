import os

from iocbuilder import AutoSubstitution
from iocbuilder.arginfo import makeArgInfo, Simple, Ident, Choice
from iocbuilder.modules.ADCore import ADBaseTemplate, makeTemplateInstance

from odin import _OdinDetector, _OdinData, _OdinDataDriver, _OdinDataServer, _OdinControlServer, \
                 find_module_path, expand_template_file, debug_print


EXCALIBUR, EXCALIBUR_PATH = find_module_path("excalibur-detector")
debug_print("Excalibur: {} = {}".format(EXCALIBUR, EXCALIBUR_PATH), 1)

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

    def __init__(self, server, READY, RELEASE, META, SENSOR, BASE_UDP_PORT):
        super(_ExcaliburOdinData, self).__init__(server, READY, RELEASE, META)
        self.sensor = SENSOR
        self.base_udp_port = BASE_UDP_PORT

    def create_config_files(self, index):
        macros = dict(DETECTOR_ROOT=EXCALIBUR_PATH,
                      RX_PORT_1=self.base_udp_port,
                      RX_PORT_2=self.base_udp_port + 1,
                      RX_PORT_3=self.base_udp_port + 2,  # 3 - 6 will be ignored in the 1M template
                      RX_PORT_4=self.base_udp_port + 3,
                      RX_PORT_5=self.base_udp_port + 4,
                      RX_PORT_6=self.base_udp_port + 5)

        super(_ExcaliburOdinData, self).create_config_file(
            "fp", self.CONFIG_TEMPLATES[self.sensor]["FrameProcessor"], index, extra_macros=macros)
        super(_ExcaliburOdinData, self).create_config_file(
            "fr", self.CONFIG_TEMPLATES[self.sensor]["FrameReceiver"], index, extra_macros=macros)


class ExcaliburOdinDataServer(_OdinDataServer):

    """Store configuration for an ExcaliburOdinDataServer"""

    BASE_UDP_PORT = 61649

    def __init__(self, IP, PROCESSES, SENSOR, FEM_DEST_MAC, FEM_DEST_IP="10.0.2.2",
                 SHARED_MEM_SIZE=1048576000):
        self.sensor = SENSOR
        self.__super.__init__(IP, PROCESSES, SHARED_MEM_SIZE)
        # Update attributes with parameters
        self.__dict__.update(locals())

    ArgInfo = makeArgInfo(__init__,
        IP=Simple("IP address of server hosting OdinData processes", str),
        PROCESSES=Simple("Number of OdinData processes on this server", int),
        SENSOR=Choice("Sensor type", ["1M", "3M"]),
        FEM_DEST_MAC=Simple("MAC address of node data link (destination for FEM to send to)", str),
        FEM_DEST_IP=Simple("IP address of node data link (destination for FEM to send to)", str),
        SHARED_MEM_SIZE=Simple("Size of shared memory buffers in bytes", int)
    )

    def create_odin_data_process(self, server, ready, release, meta):
        process = _ExcaliburOdinData(server, ready, release, meta, self.sensor, self.BASE_UDP_PORT)
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
                 ODIN_DATA_SERVER_1=None, ODIN_DATA_SERVER_2=None,
                 ODIN_DATA_SERVER_3=None, ODIN_DATA_SERVER_4=None):
        self.__dict__.update(locals())
        self.ADAPTERS.append("excalibur")

        super(ExcaliburOdinControlServer, self).__init__(
            IP, ODIN_DATA_SERVER_1, ODIN_DATA_SERVER_2, ODIN_DATA_SERVER_3, ODIN_DATA_SERVER_4
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
        ODIN_DATA_SERVER_4=Ident("OdinDataServer 4 configuration", _OdinDataServer)
    )

    def create_odin_server_config_entries(self):
        return [
            self._create_excalibur_config_entry(),
            self._create_odin_data_config_entry()
        ]

    def _create_excalibur_config_entry(self):
        return "[adapter.excalibur]\n" \
               "module = excalibur.adapter.ExcaliburAdapter\n" \
               "detector_fems = {}\n" \
               "powercard_fem_idx = {}\n" \
               "chip_enable_mask = {}\n" \
               "update_interval = 0.5".format(
                    self.fem_address_list, self.POWER_CARD_IDX, self.chip_mask
                )

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
    TemplateFile = "ExcaliburDetector.template"


class _ExcaliburFPTemplate(AutoSubstitution):
    TemplateFile = "ExcaliburOD.template"


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
    TemplateFile = "Excalibur2NodeOD.template"


@add_excalibur_fp_template
class _Excalibur4NodeFPTemplate(AutoSubstitution):
    TemplateFile = "Excalibur4NodeOD.template"


@add_excalibur_fp_template
class _Excalibur8NodeFPTemplate(AutoSubstitution):
    TemplateFile = "Excalibur8NodeOD.template"


class ExcaliburOdinDataDriver(_OdinDataDriver):

    """Create an Excalibur OdinData driver"""

    FP_TEMPLATES = {
        # Number of OdinData nodes: Template
        2: _Excalibur2NodeFPTemplate,
        4: _Excalibur4NodeFPTemplate,
        8: _Excalibur8NodeFPTemplate
    }

    def __init__(self, **args):
        detector_arg = args["R"]
        args["R"] = ":OD:"
        self.__super.__init__(DETECTOR="excalibur", **args)
        # Update the attributes of self from the commandline args
        self.__dict__.update(locals())

        if self.total_processes not in self.FP_TEMPLATES.keys():
            raise ValueError("Total number of OdinData processes must be {}".format(
                self.FP_TEMPLATES.keys()))
        else:
            sensor = self.ODIN_DATA_PROCESSES[0].sensor 
            gui_name = args["PORT"][:args["PORT"].find(".")] + ".System"
            template_args = {
                "P": args["P"],
                "R": ":OD:",
                "DET": detector_arg,
                "PORT": args["PORT"],
                "name": gui_name,
                "TIMEOUT": args["TIMEOUT"],
                "HEIGHT": EXCALIBUR_DIMENSIONS[sensor][1],
                "WIDTH": EXCALIBUR_DIMENSIONS[sensor][0]
            }
            _ExcaliburXNodeFPTemplate = self.FP_TEMPLATES[len(self.ODIN_DATA_PROCESSES)]
            _ExcaliburXNodeFPTemplate(**template_args)

    # __init__ arguments
    ArgInfo = _OdinDataDriver.ArgInfo.filtered(without=["DETECTOR"])


class _ExcaliburFemHousekeepingTemplate(AutoSubstitution):
    TemplateFile = "ExcaliburFemHousekeeping.template"


class _ExcaliburFemStatusTemplate(AutoSubstitution):
    WarnMacros = False
    TemplateFile = "ExcaliburFemStatus.template"


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
    TemplateFile = "Excalibur2FemStatus.template"


@add_excalibur_fem_status
class _Excalibur6FemStatusTemplate(AutoSubstitution):
    TemplateFile = "Excalibur6FemStatus.template"


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

        # Add the FEM housekeeping template
        fem_hk_template = _ExcaliburFemHousekeepingTemplate
        fem_hk_args = {
            "P": args["P"],
            "R": args["R"],
            "PORT": PORT,
            "TIMEOUT": args["TIMEOUT"]
        }
        fem_hk_template(**fem_hk_args)

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
        fem_config = []
        for offset in range(self.SENSOR_OPTIONS[self.SENSOR][1]):  # 2 for 1M or 6 for 3M
            fem_config.append(
                #    "fems": [
                "        {{\n"
                "            \"name\": \"fem{number}\",\n"
                "            \"mac\": \"62:00:00:00:00:0{number}\",\n"
                "            \"ipaddr\": \"10.0.2.10{number}\",\n"
                "            \"port\": 6000{number},\n"
                "            \"dest_port_offset\": {offset}\n"
                "        }}".format(number=offset + 1, offset=offset)
                #    ...
                #    ]
            )

        node_config = []
        for idx, process in enumerate(sorted(self.control_server.odin_data_processes,
                                             key=lambda x: x.RANK)):
            config = dict(
                name="dest{}".format(idx + 1), mac=process.server.FEM_DEST_MAC,
                ip=process.server.FEM_DEST_IP, port=process.base_udp_port
            )
            node_config.append(
                #    "nodes": [
                "        {{\n"
                "            \"name\": \"{name}\",\n"
                "            \"mac\": \"{mac}\",\n"
                "            \"ipaddr\": \"{ip}\",\n"
                "            \"port\": {port}\n"
                "        }}".format(**config)
                #    ...
                #    ]
            )

        macros = dict(
            FEM_CONFIG=",\n".join(fem_config),
            NODE_CONFIG=",\n".join(node_config),
            NUM_DESTS=len(self.control_server.odin_data_processes)
        )
        expand_template_file("udp_excalibur.json", macros, "udp_excalibur.json")

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
