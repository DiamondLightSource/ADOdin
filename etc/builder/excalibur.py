import os

from iocbuilder import AutoSubstitution
from iocbuilder.arginfo import makeArgInfo, Simple, Ident, Choice
from iocbuilder.modules.ADCore import ADBaseTemplate, makeTemplateInstance

from util import OdinPaths, expand_template_file, debug_print, \
                 create_config_entry, OneLineEntry
from odin import _OdinDetector, _OdinData, _OdinDataDriver, _OdinDataServer, _OdinControlServer, \
                 _PluginConfig, _FrameProcessorPlugin
from plugins import _LiveViewPlugin, _OffsetAdjustmentPlugin, _UIDAdjustmentPlugin, \
                    _SumPlugin, _BloscPlugin, _FileWriterPlugin, _DatasetCreationPlugin


debug_print("Excalibur: {}".format(OdinPaths.EXCALIBUR_DETECTOR), 1)

EXCALIBUR_DIMENSIONS = {
    # Sensor: (Width, Height)
    "1M": (2048, 512),
    "3M": (2048, 1536)
}


class _ExcaliburProcessPlugin(_DatasetCreationPlugin):

    NAME = "excalibur"
    CLASS_NAME = "ExcaliburProcessPlugin"
    LIBRARY_PATH = OdinPaths.EXCALIBUR_DETECTOR

    def __init__(self, sensor):
        ddims = [EXCALIBUR_DIMENSIONS[sensor][1], EXCALIBUR_DIMENSIONS[sensor][0]]
        dchunks = [1, EXCALIBUR_DIMENSIONS[sensor][1], EXCALIBUR_DIMENSIONS[sensor][0]]

        DATASETS = [
            dict(name="data", datatype="uint16", dims=ddims, chunks=dchunks),
            dict(name="data2", datatype="uint16", dims=ddims, chunks=dchunks)
        ]
        super(_ExcaliburProcessPlugin, self).__init__(None)

        self.sensor = sensor

    def create_extra_config_entries(self, rank, total):
        entries = []
        dimensions_entry = {
            self.NAME: {
                "width": EXCALIBUR_DIMENSIONS[self.sensor][0],
                "height": EXCALIBUR_DIMENSIONS[self.sensor][1]
            }
        }
        entries.append(create_config_entry(dimensions_entry))

        return entries

    ArgInfo = _FrameProcessorPlugin.ArgInfo + makeArgInfo(__init__,
        sensor=Choice("Sensor type", ["1M", "3M"])
    )


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

    def __init__(self, server, READY, RELEASE, META, PLUGINS, SENSOR, BASE_UDP_PORT):
        super(_ExcaliburOdinData, self).__init__(server, READY, RELEASE, META, PLUGINS)
        self.plugins = PLUGINS
        self.sensor = SENSOR
        self.base_udp_port = BASE_UDP_PORT

    def create_config_files(self, index, total):
        macros = dict(DETECTOR=OdinPaths.EXCALIBUR_DETECTOR,
                      RX_PORT_1=self.base_udp_port,
                      RX_PORT_2=self.base_udp_port + 1,
                      RX_PORT_3=self.base_udp_port + 2,  # 3 - 6 will be ignored in the 1M template
                      RX_PORT_4=self.base_udp_port + 3,
                      RX_PORT_5=self.base_udp_port + 4,
                      RX_PORT_6=self.base_udp_port + 5,
                      WIDTH=EXCALIBUR_DIMENSIONS[self.sensor][0],
                      HEIGHT=EXCALIBUR_DIMENSIONS[self.sensor][1])

        if self.plugins is None:
            super(_ExcaliburOdinData, self).create_config_file(
                "fp", self.CONFIG_TEMPLATES[self.sensor]["FrameProcessor"], extra_macros=macros)
        else:
            super(_ExcaliburOdinData, self).create_config_file(
                "fp", "fp_custom.json", extra_macros=macros)

        super(_ExcaliburOdinData, self).create_config_file(
            "fr", self.CONFIG_TEMPLATES[self.sensor]["FrameReceiver"], extra_macros=macros)


class _ExcaliburModeTemplate(AutoSubstitution):
    TemplateFile = "ExcaliburODMode.template"


class _ExcaliburPluginConfig(_PluginConfig):
    # Device attributes
    AutoInstantiate = True

    def __init__(self, SENSOR):
        excalibur = _ExcaliburProcessPlugin(sensor=SENSOR)
        offset = _OffsetAdjustmentPlugin(source=excalibur)
        uid = _UIDAdjustmentPlugin(source=offset)
        sum = _SumPlugin(source=uid)
        gap = _ExcaliburGapFillPlugin(source=sum, SENSOR=SENSOR, CHIP_GAP=3, MODULE_GAP=124)
        view = _LiveViewPlugin(source=gap)
        blosc = _BloscPlugin(source=gap)
        hdf = _FileWriterPlugin(source=blosc)
        super(_ExcaliburPluginConfig, self).__init__(PLUGIN_1=excalibur,
                                                     PLUGIN_2=offset,
                                                     PLUGIN_3=uid,
                                                     PLUGIN_4=sum,
                                                     PLUGIN_5=gap,
                                                     PLUGIN_6=view,
                                                     PLUGIN_7=blosc,
                                                     PLUGIN_8=hdf)
        
        # Set the modes
        self.modes = ['compression', 'no_compression']
        
        # Now we need to create the standard mode chain (with compression)
        excalibur.add_mode('compression')
        offset.add_mode('compression', source=excalibur)
        uid.add_mode('compression', source=offset)
        sum.add_mode('compression', source=uid)
        gap.add_mode('compression', source=sum)
        view.add_mode('compression', source=gap)
        blosc.add_mode('compression', source=gap)
        hdf.add_mode('compression', source=blosc)

        # Now we need to create the no compression mode chain (no blosc in the chain)
        excalibur.add_mode('no_compression')
        offset.add_mode('no_compression', source=excalibur)
        uid.add_mode('no_compression', source=offset)
        sum.add_mode('no_compression', source=uid)
        gap.add_mode('no_compression', source=sum)
        view.add_mode('no_compression', source=gap)
        hdf.add_mode('no_compression', source=gap)

    def detector_setup(self, od_args):
        ## Make an instance of our template
        makeTemplateInstance(_ExcaliburModeTemplate, locals(), od_args)


class ExcaliburOdinDataServer(_OdinDataServer):

    """Store configuration for an ExcaliburOdinDataServer"""

    BASE_UDP_PORT = 61649
    PLUGIN_CONFIG = None

    def __init__(self, IP, PROCESSES, SENSOR,
                 FEM_DEST_MAC, FEM_DEST_IP="10.0.2.2",
                 SHARED_MEM_SIZE=1048576000, PLUGIN_CONFIG=None,
                 FEM_DEST_MAC_2=None, FEM_DEST_IP_2=None, DIRECT_FEM_CONNECTION=False):
        self.sensor = SENSOR
        if PLUGIN_CONFIG is None:
            if ExcaliburOdinDataServer.PLUGIN_CONFIG is None:
                # Create the standard Excalibur plugin config
                ExcaliburOdinDataServer.PLUGIN_CONFIG = _ExcaliburPluginConfig(SENSOR)

        self.__super.__init__(IP, PROCESSES, SHARED_MEM_SIZE, ExcaliburOdinDataServer.PLUGIN_CONFIG)
        # Update attributes with parameters
        self.__dict__.update(locals())

    ArgInfo = makeArgInfo(__init__,
        IP=Simple("IP address of server hosting OdinData processes", str),
        PROCESSES=Simple("Number of OdinData processes on this server", int),
        SENSOR=Choice("Sensor type", ["1M", "3M"]),
        FEM_DEST_MAC=Simple("MAC address of node data link (destination for FEM to send to)", str),
        FEM_DEST_IP=Simple("IP address of node data link (destination for FEM to send to)", str),
        SHARED_MEM_SIZE=Simple("Size of shared memory buffers in bytes", int),
        PLUGIN_CONFIG=Ident("Define a custom set of plugins", _PluginConfig),
        FEM_DEST_MAC_2=Simple("MAC address of second node data link", str),
        FEM_DEST_IP_2=Simple("IP address of second node data link", str),
        DIRECT_FEM_CONNECTION=Simple("True if data links go direct from FEM to server. "
                                     "False if data links go through a switch. "
                                     "This determines what is done with the second FEM_DEST", bool)
    )

    def create_odin_data_process(self, server, ready, release, meta, plugin_config):
        process = _ExcaliburOdinData(server, ready, release, meta, plugin_config,
                                     self.sensor, self.BASE_UDP_PORT)
        self.BASE_UDP_PORT += 6
        return process


class ExcaliburOdinControlServer(_OdinControlServer):

    """Store configuration for an ExcaliburOdinControlServer"""

    ODIN_SERVER = os.path.join(OdinPaths.EXCALIBUR_DETECTOR, "prefix/bin/excalibur_odin")
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

    def __init__(self, IP, SENSOR, PORT=8888, FEMS_REVERSED=False, POWER_CARD_IDX=1,
                 ODIN_DATA_SERVER_1=None, ODIN_DATA_SERVER_2=None,
                 ODIN_DATA_SERVER_3=None, ODIN_DATA_SERVER_4=None):
        self.__dict__.update(locals())
        self.ADAPTERS.append("excalibur")

        super(ExcaliburOdinControlServer, self).__init__(
            IP, PORT, ODIN_DATA_SERVER_1, ODIN_DATA_SERVER_2, ODIN_DATA_SERVER_3, ODIN_DATA_SERVER_4
        )

    # __init__ arguments
    ArgInfo = makeArgInfo(__init__,
        IP=Simple("IP address of control server", str),
        PORT=Simple("Port of control server", int),
        SENSOR=Choice("Sensor type", ["1M", "3M"]),
        FEMS_REVERSED=Choice("Are the FEM IP addresses reversed 106..101", [True, False]),
        POWER_CARD_IDX=Simple("Index of the power card", int),
        ODIN_DATA_SERVER_1=Ident("OdinDataServer 1 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_2=Ident("OdinDataServer 2 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_3=Ident("OdinDataServer 3 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_4=Ident("OdinDataServer 4 configuration", _OdinDataServer)
    )

    def get_extra_startup_macro(self):
        return '--staticlogfields beamline=${{BEAMLINE}},\
application_name="excalibur_odin",detector="Excalibur{}" \
--logserver="graylog2.diamond.ac.uk:12210" --access_logging=ERROR'.format(self.SENSOR)

    def create_odin_server_config_entries(self):
        return [
            self._create_excalibur_config_entry(),
            self._create_odin_data_config_entry()
        ]

    def create_odin_server_static_path(self):
        return OdinPaths.EXCALIBUR_DETECTOR + "/prefix/html/static"

    def _create_excalibur_config_entry(self):
        return "[adapter.excalibur]\n" \
               "module = excalibur.adapter.ExcaliburAdapter\n" \
               "detector_fems = {}\n" \
               "powercard_fem_idx = {}\n" \
               "chip_enable_mask = {}\n" \
               "update_interval = 0.5".format(
                    self.fem_address_list, self.POWER_CARD_IDX, self.chip_mask
                )

    def _create_odin_data_config_entry(self):
        fp_endpoints = []
        fr_endpoints = []
        for process in sorted(self.odin_data_processes, key=lambda x: x.RANK):
            fp_endpoints.append(process.FP_ENDPOINT)
            fr_endpoints.append(process.FR_ENDPOINT)

        return "[adapter.fp]\n" \
               "module = odin_data.fp_compression_adapter.FPCompressionAdapter\n" \
               "endpoints = {}\n" \
               "update_interval = 0.2\n" \
               "datasets = data,data2\n\n" \
               "[adapter.fr]\n" \
               "module = odin_data.frame_receiver_adapter.FrameReceiverAdapter\n" \
               "endpoints = {}\n" \
               "update_interval = 0.2".format(", ".join(fp_endpoints), ", ".join(fr_endpoints))


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
class _Excalibur1NodeFPTemplate(AutoSubstitution):
    TemplateFile = "Excalibur1NodeOD.template"


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
        1: _Excalibur1NodeFPTemplate,
        2: _Excalibur2NodeFPTemplate,
        4: _Excalibur4NodeFPTemplate,
        8: _Excalibur8NodeFPTemplate
    }

    def __init__(self, **args):
        detector_arg = ":CAM:"
        args["R"] = ":OD:"
        self.__super.__init__(DETECTOR="excalibur", **args)
        # Update the attributes of self from the commandline args
        self.__dict__.update(locals())

        if self.odin_data_processes not in self.FP_TEMPLATES.keys():
            raise ValueError("Total number of OdinData processes must be {}".format(
                self.FP_TEMPLATES.keys()))
        else:
            sensor = self.ODIN_DATA_PROCESSES[0].sensor
            template_args = dict(
                P=args["P"],
                R=":OD:",
                DET=detector_arg,
                PORT=args["PORT"],
                TIMEOUT=args["TIMEOUT"],
                OD_DET_CONFIG_GUI=self.gui_macro(args["PORT"], "OdinData.Excalibur"),
                ACQ_GUI=self.gui_macro(args["PORT"], "Acquisition"),
                **self.create_gui_macros(args["PORT"])
            )
            _ExcaliburXNodeFPTemplate = self.FP_TEMPLATES[len(self.ODIN_DATA_PROCESSES)]
            _ExcaliburXNodeFPTemplate(**template_args)

    # __init__ arguments
    ArgInfo = _OdinDataDriver.ArgInfo.filtered(without=["DETECTOR", "TOTAL", "R"])


class _Excalibur2FemHousekeepingTemplate(AutoSubstitution):
    TemplateFile = "Excalibur2FemHousekeeping.template"


class _Excalibur6FemHousekeepingTemplate(AutoSubstitution):
    TemplateFile = "Excalibur6FemHousekeeping.template"


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
    SENSOR_OPTIONS = {  # (Status Template, Housekeeping Template, Number of FEMs)
        "1M": (_Excalibur2FemStatusTemplate, _Excalibur2FemHousekeepingTemplate, 2),
        "3M": (_Excalibur6FemStatusTemplate, _Excalibur6FemHousekeepingTemplate, 6)
    }

    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = "PORT"

    _SpecificTemplate = _ExcaliburDetectorTemplate

    # We don't really need the OdinDataDriver, but we need to know it is instantiated as it
    # defines the RANK on all the OdinData instances and we need to sort by RANK for the UDP config
    def __init__(self, PORT, ODIN_CONTROL_SERVER, ODIN_DATA_DRIVER, SENSOR,
                 BUFFERS=0, MEMORY=0, **args):
        args["R"] = ":CAM:"
        # Init the superclass (OdinDetector)
        self.__super.__init__(PORT, ODIN_CONTROL_SERVER, self.DETECTOR,
                              BUFFERS, MEMORY, **args)
        # Update the attributes of self from the commandline args
        self.__dict__.update(locals())
        # Make an instance of our template
        makeTemplateInstance(self._SpecificTemplate, locals(), args)

        self.control_server = ODIN_CONTROL_SERVER

        # Add the FEM housekeeping template
        fem_hk_template = self.SENSOR_OPTIONS[SENSOR][1]
        fem_hk_args = {
            "P": args["P"],
            "R": args["R"],
            "PORT": PORT,
            "TIMEOUT": args["TIMEOUT"]
        }
        fem_hk_template(**fem_hk_args)

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
            "TOTAL": self.SENSOR_OPTIONS[SENSOR][2]
        }
        status_template(**status_args)

        self.create_udp_file()

    def create_udp_file(self):
        fem_dests = []
        for offset in range(self.SENSOR_OPTIONS[self.SENSOR][2]):  # 2 for 1M or 6 for 3M
            fem_dests.append(
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

        if any(server.DIRECT_FEM_CONNECTION for server in self.control_server.odin_data_servers):
            node_config = self.generate_direct_fem_node_config()  # [[<FEM1>], [<FEM2>], ...]
            node_labels = ["fem{}".format(n) for n in range(1, len(fem_dests) + 1)]
        else:
            node_config = self.generate_simple_node_config()  # [[<ALL_FEMS>]]
            node_labels = ["all_fems"]

        node_dests = []
        for node_label, fem_config in zip(node_labels, node_config):
            fem_node_dests = []
            for dest_config in fem_config:
                fem_node_dests.append(
                    #    "nodes": {
                    #        "fem1": [
                    "            {{\n"
                    "                \"name\": \"dest{id}\",\n"
                    "                \"mac\": \"{mac}\",\n"
                    "                \"ipaddr\": \"{ip}\",\n"
                    "                \"port\": {port}\n"
                    "            }}".format(**dest_config)
                    #        ...
                    #        ],
                    #    ...
                    #    }
                )

            node_dests.append(
                #    "nodes": {
                "        \"{}\": [\n"
                "{}\n"
                "        ]".format(node_label, ",\n".join(fem_node_dests))
                #    ...
                #    }
            )

        macros = dict(
            FEM_CONFIG=",\n".join(fem_dests),
            NODE_CONFIG=",\n".join(node_dests),
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
    ArgInfo = ArgInfo.filtered(without=["R"])

    def generate_simple_node_config(self):
        fem_config = []
        for idx, process in enumerate(sorted(self.control_server.odin_data_processes,
                                             key=lambda x: x.RANK)):
            config = dict(
                id=idx + 1, mac=process.server.FEM_DEST_MAC,
                ip=process.server.FEM_DEST_IP, port=process.base_udp_port
            )
            fem_config.append(config)

        # A nested list to specify the same config is valid for all FEMS
        node_config = [fem_config]
        return node_config

    def generate_direct_fem_node_config(self):
        if len(self.control_server.odin_data_servers) != 1:
            raise ValueError("Can only use DIRECT_FEM_CONNECTION with a single OdinDataServer")
        server = self.control_server.odin_data_servers[0]
        if server.FEM_DEST_MAC_2 is None or server.FEM_DEST_IP_2 is None:
            raise ValueError("DIRECT_FEM_CONNECTION requires FEM_DEST_MAC_2 and FEM_DEST_IP_2")

        # FEMs are connected directly to a NIC on the server
        # Each will have its own list of entries, one for every receiver, with different ports
        node_config = []
        id = 1
        for mac, ip in [(server.FEM_DEST_MAC, server.FEM_DEST_IP),
                        (server.FEM_DEST_MAC_2, server.FEM_DEST_IP_2)]:
            fem_config = []
            for process in sorted(self.control_server.odin_data_processes, key=lambda x: x.RANK):
                config = dict(
                    id=id, mac=mac, ip=ip, port=process.base_udp_port
                )
                fem_config.append(config)
                id += 1

            node_config.append(fem_config)

        return node_config


class _ExcaliburGapFillPlugin(_FrameProcessorPlugin):

    NAME = "gap"
    CLASS_NAME = "GapFillPlugin"

    def __init__(self, source=None, SENSOR="3M", CHIP_GAP=3, MODULE_GAP=124):
        super(_ExcaliburGapFillPlugin, self).__init__(source)
        self.sensor = SENSOR
        self.chip_gap = CHIP_GAP
        self.module_gap = MODULE_GAP

    def create_extra_config_entries(self, rank, total):
        entries = []

        chip_size = [256, 256]
        x_gaps = [0] + [self.chip_gap] * 7 + [0]
        if self.sensor == "1M":
            grid_size = [2, 8]
            y_gaps = [0, self.chip_gap, 0]
        else:
            grid_size = [6, 8]
            y_gaps = [
                0, self.chip_gap, self.module_gap, self.chip_gap, self.module_gap, self.chip_gap, 0
            ]

        layout_config = {
            self.NAME: {
                "grid_size": grid_size,
                "chip_size": chip_size,
                "x_gaps": x_gaps,
                "y_gaps": y_gaps
            }
        }
        entries.append(create_config_entry(layout_config))

        dimensions = [
            EXCALIBUR_DIMENSIONS[self.sensor][1] + sum(y_gaps),
            EXCALIBUR_DIMENSIONS[self.sensor][0] + sum(x_gaps)
        ]
        dataset_config = {
            _FileWriterPlugin.NAME: {
                "dataset": {
                    _FileWriterPlugin.DATASET_NAME: {
                        "dims": OneLineEntry(dimensions),
                        "chunks": OneLineEntry([1] + dimensions),
                    }
                }
            }
        }
        entries.append(create_config_entry(dataset_config))
        dataset_config = {
            _FileWriterPlugin.NAME: {
                "dataset": {
                    "data2": {
                        "datatype": "uint16",
                        "dims": OneLineEntry(dimensions),
                        "chunks": OneLineEntry([1] + dimensions),
                    }
                }
            }
        }
        entries.append(create_config_entry(dataset_config))

        return entries
