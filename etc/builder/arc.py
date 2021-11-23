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


debug_print("Arc: {}".format(OdinPaths.ARC_DETECTOR), 1)

ARC_DIMENSIONS = {
    # Sensor: (Width, Height)
    "1FEM": (768, 3072),
    "2FEM": (768, 6144)
}


class _ArcProcessPlugin(_DatasetCreationPlugin):

    NAME = "arc"
    CLASS_NAME = "ArcProcessPlugin"
    LIBRARY_PATH = OdinPaths.ARC_DETECTOR

    def __init__(self, sensor):
        ddims = [ARC_DIMENSIONS[sensor][1], ARC_DIMENSIONS[sensor][0]]
        dchunks = [1, ARC_DIMENSIONS[sensor][1], ARC_DIMENSIONS[sensor][0]]

        DATASETS = [
            dict(name="data", datatype="uint16", dims=ddims, chunks=dchunks),
            dict(name="data2", datatype="uint16", dims=ddims, chunks=dchunks)
        ]
        super(_ArcProcessPlugin, self).__init__(None)

        self.sensor = sensor

    def create_extra_config_entries(self, rank, total):
        entries = []
        dimensions_entry = {
            self.NAME: {
                "width": ARC_DIMENSIONS[self.sensor][0],
                "height": ARC_DIMENSIONS[self.sensor][1]
            }
        }
        entries.append(create_config_entry(dimensions_entry))

        return entries

    ArgInfo = _FrameProcessorPlugin.ArgInfo + makeArgInfo(__init__,
        sensor=Choice("Sensor type", ["1FEM", "2FEM"])
    )


class _ArcOdinData(_OdinData):

    CONFIG_TEMPLATES = {
        "1FEM": {
            "FrameProcessor": "fp_arc.json",
            "FrameReceiver": "fr_arc_1.json"
        },
        "2FEM": {
            "FrameProcessor": "fp_arc.json",
            "FrameReceiver": "fr_arc_2.json"
        }
    }

    def __init__(self, server, READY, RELEASE, META, PLUGINS, SENSOR, BASE_UDP_PORT):
        super(_ArcOdinData, self).__init__(server, READY, RELEASE, META, PLUGINS)
        self.plugins = PLUGINS
        self.sensor = SENSOR
        self.base_udp_port = BASE_UDP_PORT

    def create_config_files(self, index, total):
        macros = dict(DETECTOR=OdinPaths.ARC_DETECTOR,
                      RX_PORT_1=self.base_udp_port,
                      RX_PORT_2=self.base_udp_port + 1,
                      RX_PORT_3=self.base_udp_port + 2,  # 2 - 3 will be ignored in the 1FEM template
                      RX_PORT_4=self.base_udp_port + 3,
                      WIDTH=ARC_DIMENSIONS[self.sensor][0],
                      HEIGHT=ARC_DIMENSIONS[self.sensor][1])

        if self.plugins is None:
            super(_ArcOdinData, self).create_config_file(
                "fp", self.CONFIG_TEMPLATES[self.sensor]["FrameProcessor"], extra_macros=macros)
        else:
            super(_ArcOdinData, self).create_config_file(
                "fp", "fp_custom.json", extra_macros=macros)

        super(_ArcOdinData, self).create_config_file(
            "fr", self.CONFIG_TEMPLATES[self.sensor]["FrameReceiver"], extra_macros=macros)


class _ArcModeTemplate(AutoSubstitution):
    TemplateFile = "ArcODMode.template"


class _ArcPluginConfig(_PluginConfig):
    # Device attributes
    AutoInstantiate = True

    def __init__(self, SENSOR):
        arc = _ArcProcessPlugin(sensor=SENSOR)
        offset = _OffsetAdjustmentPlugin(source=arc)
        uid = _UIDAdjustmentPlugin(source=offset)
        sum = _SumPlugin(source=uid)
        gap = _ArcGapFillPlugin(source=sum, SENSOR=SENSOR, CHIP_GAP=3, MODULE_GAP=124)
        view = _LiveViewPlugin(source=gap)
        blosc = _BloscPlugin(source=gap)
        hdf = _FileWriterPlugin(source=blosc)
        super(_ArcPluginConfig, self).__init__(PLUGIN_1=arc,
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
        arc.add_mode('compression')
        offset.add_mode('compression', source=arc)
        uid.add_mode('compression', source=offset)
        sum.add_mode('compression', source=uid)
        gap.add_mode('compression', source=sum)
        view.add_mode('compression', source=gap)
        blosc.add_mode('compression', source=gap)
        hdf.add_mode('compression', source=blosc)

        # Now we need to create the no compression mode chain (no blosc in the chain)
        arc.add_mode('no_compression')
        offset.add_mode('no_compression', source=arc)
        uid.add_mode('no_compression', source=offset)
        sum.add_mode('no_compression', source=uid)
        gap.add_mode('no_compression', source=sum)
        view.add_mode('no_compression', source=gap)
        hdf.add_mode('no_compression', source=gap)

    def detector_setup(self, od_args):
        ## Make an instance of our template
        makeTemplateInstance(_ArcModeTemplate, locals(), od_args)


class ArcOdinDataServer(_OdinDataServer):

    """Store configuration for an ArcOdinDataServer"""

    BASE_UDP_PORT = 61649
    PLUGIN_CONFIG = None

    def __init__(self, IP, PROCESSES, SENSOR,
                 FEM_DEST_MAC, FEM_DEST_IP="10.0.2.2",
                 SHARED_MEM_SIZE=1048576000, PLUGIN_CONFIG=None,
                 FEM_DEST_MAC_2=None, FEM_DEST_IP_2=None, DIRECT_FEM_CONNECTION=False):
        self.sensor = SENSOR
        if PLUGIN_CONFIG is None:
            if ArcOdinDataServer.PLUGIN_CONFIG is None:
                # Create the standard Arc plugin config
                ArcOdinDataServer.PLUGIN_CONFIG = _ArcPluginConfig(SENSOR)

        self.__super.__init__(IP, PROCESSES, SHARED_MEM_SIZE, ArcOdinDataServer.PLUGIN_CONFIG)
        # Update attributes with parameters
        self.__dict__.update(locals())

    ArgInfo = makeArgInfo(__init__,
        IP=Simple("IP address of server hosting OdinData processes", str),
        PROCESSES=Simple("Number of OdinData processes on this server", int),
        SENSOR=Choice("Sensor type", ["1FEM", "2FEM"]),
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
        process = _ArcOdinData(server, ready, release, meta, plugin_config,
                                     self.sensor, self.BASE_UDP_PORT)
        self.BASE_UDP_PORT += 6
        return process


class ArcOdinControlServer(_OdinControlServer):

    """Store configuration for an ArcOdinControlServer"""

    ODIN_SERVER = os.path.join(OdinPaths.ARC_DETECTOR, "prefix/bin/arc_odin")
    CONFIG_TEMPLATES = {
        "1FEM": {
            "chip_mask": "0xFF",
            "fem_addresses": ["192.168.0.101:6969", ]
        },
        "2FEM": {
            "chip_mask": "0xFF, 0xFF",
            "fem_addresses": ["192.168.0.101:6969", "192.168.0.102:6969",]
        }
    }

    def __init__(self, IP, SENSOR, PORT=8888, META_WRITER_IP=None,
                 FEMS_REVERSED=False, POWER_CARD_IDX=1,
                 ODIN_DATA_SERVER_1=None, ODIN_DATA_SERVER_2=None,
                 ODIN_DATA_SERVER_3=None, ODIN_DATA_SERVER_4=None):
        self.__dict__.update(locals())
        self.ADAPTERS.append("arc")

        super(ArcOdinControlServer, self).__init__(
            IP, PORT, META_WRITER_IP,
            ODIN_DATA_SERVER_1, ODIN_DATA_SERVER_2, ODIN_DATA_SERVER_3, ODIN_DATA_SERVER_4
        )

    # __init__ arguments
    ArgInfo = makeArgInfo(__init__,
        IP=Simple("IP address of control server", str),
        SENSOR=Choice("Sensor type", ["1FEM", "2FEM"]),
        PORT=Simple("Port of control server", int),
        META_WRITER_IP=Simple("IP address of MetaWriter (None -> first OdinDataServer)", str),
        FEMS_REVERSED=Choice("Are the FEM IP addresses reversed 106..101", [True, False]),
        POWER_CARD_IDX=Simple("Index of the power card", int),
        ODIN_DATA_SERVER_1=Ident("OdinDataServer 1 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_2=Ident("OdinDataServer 2 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_3=Ident("OdinDataServer 3 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_4=Ident("OdinDataServer 4 configuration", _OdinDataServer)
    )

    def _add_python_modules(self):
        self.PYTHON_MODULES.update(dict(arc_detector=OdinPaths.ARC_DETECTOR))

    def get_extra_startup_macro(self):
        return '--staticlogfields beamline=${{BEAMLINE}},\
application_name="arc_odin",detector="Arc{}" \
--logserver="graylog2.diamond.ac.uk:12210" --access_logging=ERROR'.format(self.SENSOR)

    def create_extra_config_entries(self):
        return [
            self._create_arc_config_entry()
        ]

    def create_odin_server_static_path(self):
        return OdinPaths.ARC_DETECTOR + "/prefix/html/static"

    def _create_arc_config_entry(self):
        return "[adapter.arc]\n" \
               "module = arc.adapter.ArcAdapter\n" \
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
        if self.SENSOR == "1FEM":
            return "0xFF"
        if self.SENSOR == "2FEM":
            return "0xFF, 0xFF"


class ArcMetaWriter(_MetaWriter):
    DETECTOR = "Arc"


# ~~~~~~~~~~~~ #
# AreaDetector #
# ~~~~~~~~~~~~ #


class _ArcDetectorTemplate(AutoSubstitution):
    TemplateFile = "ArcDetector.template"


class _ArcFPTemplate(AutoSubstitution):
    TemplateFile = "ArcOD.template"


def add_arc_fp_template(cls):
    """Convenience function to add arcFPTemplate attributes to a class that
    includes it via an msi include statement rather than verbatim"""
    template_substitutions = ["TOTAL", "ADDRESS"]

    cls.Arguments = _ArcFPTemplate.Arguments + \
                    [x for x in cls.Arguments if x not in _ArcFPTemplate.Arguments]
    cls.Arguments = [entry for entry in cls.Arguments if entry not in template_substitutions]

    cls.ArgInfo = _ArcFPTemplate.ArgInfo + cls.ArgInfo.filtered(
        without=_ArcFPTemplate.ArgInfo.Names())
    cls.ArgInfo = cls.ArgInfo.filtered(without=template_substitutions)

    cls.Defaults.update(_ArcFPTemplate.Defaults)

    return cls


@add_arc_fp_template
class _Arc1NodeFPTemplate(AutoSubstitution):
    TemplateFile = "Arc1NodeOD.template"


@add_arc_fp_template
class _Arc2NodeFPTemplate(AutoSubstitution):
    TemplateFile = "Arc2NodeOD.template"


@add_arc_fp_template
class _Arc4NodeFPTemplate(AutoSubstitution):
    TemplateFile = "Arc4NodeOD.template"


class ArcOdinDataDriver(_OdinDataDriver):

    """Create an Arc OdinData driver"""

    FP_TEMPLATES = {
        # Number of OdinData nodes: Template
        1: _Arc1NodeFPTemplate,
        2: _Arc2NodeFPTemplate,
        4: _Arc4NodeFPTemplate,
    }
    META_WRITER_CLASS = ArcMetaWriter

    def __init__(self, **args):
        detector_arg = ":CAM:"
        args["R"] = ":OD:"
        self.__super.__init__(DETECTOR="arc", **args)
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
                OD_DET_CONFIG_GUI=self.gui_macro(args["PORT"], "OdinData.Arc"),
                ACQ_GUI=self.gui_macro(args["PORT"], "Acquisition"),
                **self.create_gui_macros(args["PORT"])
            )
            _ArcXNodeFPTemplate = self.FP_TEMPLATES[len(self.ODIN_DATA_PROCESSES)]
            _ArcXNodeFPTemplate(**template_args)

    # __init__ arguments
    ArgInfo = _OdinDataDriver.ArgInfo.filtered(without=["DETECTOR", "TOTAL", "R"])


class _Arc1FemHousekeepingTemplate(AutoSubstitution):
    TemplateFile = "Arc1FemHousekeeping.template"

class _Arc2FemHousekeepingTemplate(AutoSubstitution):
    TemplateFile = "Arc2FemHousekeeping.template"


class _ArcFemStatusTemplate(AutoSubstitution):
    WarnMacros = False
    TemplateFile = "ArcFemStatus.template"


def add_arc_fem_status(cls):
    """Convenience function to add arcFemStatusTemplate attributes to a class that
    includes it via an msi include statement rather than verbatim"""
    cls.Arguments = _ArcFemStatusTemplate.Arguments + \
        [x for x in cls.Arguments if x not in _ArcFemStatusTemplate.Arguments]
    cls.ArgInfo = _ArcFemStatusTemplate.ArgInfo + cls.ArgInfo.filtered(
        without=_ArcFemStatusTemplate.ArgInfo.Names())
    cls.Defaults.update(_ArcFemStatusTemplate.Defaults)
    return cls


@add_arc_fem_status
class _Arc1FemStatusTemplate(AutoSubstitution):
    TemplateFile = "Arc1FemStatus.template"

@add_arc_fem_status
class _Arc2FemStatusTemplate(AutoSubstitution):
    TemplateFile = "Arc2FemStatus.template"



class ArcDetector(_OdinDetector):

    """Create an Arc detector"""

    DETECTOR = "arc"
    SENSOR_OPTIONS = {  # (Status Template, Housekeeping Template, Number of FEMs)
        "1FEM": (_Arc1FemStatusTemplate, _Arc1FemHousekeepingTemplate, 2),
        "2FEM": (_Arc2FemStatusTemplate, _Arc2FemHousekeepingTemplate, 2),
    }

    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = "PORT"

    _SpecificTemplate = _ArcDetectorTemplate

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
        for offset in range(self.SENSOR_OPTIONS[self.SENSOR][2]):  # 1 for 1FEM, 2 for 2FEM
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
        expand_template_file("udp_arc.json", macros, "udp_arc.json")

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


class _ArcGapFillPlugin(_FrameProcessorPlugin):

    NAME = "gap"
    CLASS_NAME = "GapFillPlugin"

    def __init__(self, source=None, SENSOR="3M", CHIP_GAP=3, MODULE_GAP=124):
        super(_ArcGapFillPlugin, self).__init__(source)
        self.sensor = SENSOR
        self.chip_gap = CHIP_GAP
        self.module_gap = MODULE_GAP

    def create_extra_config_entries(self, rank, total):
        entries = []

        chip_size = [256, 256]
        x_gaps = [0] + [self.chip_gap] * 7 + [0]
        # TODO these will need adjusting
        if self.sensor == "1FEM":
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
            ARC_DIMENSIONS[self.sensor][1] + sum(y_gaps),
            ARC_DIMENSIONS[self.sensor][0] + sum(x_gaps)
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
