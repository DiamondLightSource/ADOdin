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
    data_file_path
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


class ArcDimensions:
    FEM_PIXELS_PER_CHIP_X = 256
    FEM_PIXELS_PER_CHIP_Y = 256
    FEM_CHIPS_PER_SUPER_MODULE_X = 3
    FEM_CHIPS_PER_SUPER_MODULE_Y = 2
    FEM_SUPER_MODULES_PER_FEM_X = 1
    FEM_SUPER_MODULES_PER_FEM_Y = 6
    FEM_CHIP_GAP_PIXELS_X = 3
    FEM_CHIP_GAP_PIXELS_Y = 3

    def __init__(self, super_module_count=1):
        # the following calculations will then determine number of FEMS and pixel
        # dimensions from the super module count (assuming that the modules are
        # installed upwards from 0,0 )

        self.fem_count = (
            int(
                super_module_count
                / (self.FEM_SUPER_MODULES_PER_FEM_X * self.FEM_SUPER_MODULES_PER_FEM_Y)
            )
            + 1
        )

        self.x_pixels = self.FEM_PIXELS_PER_CHIP_X * self.FEM_CHIPS_PER_SUPER_MODULE_X
        self.y_pixels = (
            self.FEM_PIXELS_PER_CHIP_Y
            * self.FEM_CHIPS_PER_SUPER_MODULE_Y
            * super_module_count
        )

        # TODO TODO TODO - the pixels in the first example UDP capture file 
        # are 256 * 1280 which does not line up with any definition of 
        # super module -> dimensions calculation 
        # SUGGESTION: make the code agnostic of dimensions and use the 
        # packet header info only - is that possible?
        # if not just supply dimensions and rebuild everything for each change
        self.x_pixels = 256
        self.y_pixels = 1280

        self.pixels = self.x_pixels * self.y_pixels


class _ArcProcessPlugin(_DatasetCreationPlugin):

    NAME = "arc"
    CLASS_NAME = "ArcProcessPlugin"
    LIBRARY_PATH = OdinPaths.ARC_DETECTOR

    def __init__(self, SUPER_MODULES=12):
        self.dims = ArcDimensions(SUPER_MODULES)

        d_dims = [self.dims.y_pixels, self.dims.x_pixels]
        d_chunks = [1, self.dims.y_pixels, self.dims.x_pixels]

        self.DATASETS = [
            dict(name="data", datatype="uint16", dims=d_dims, chunks=d_chunks),
            dict(name="data2", datatype="uint16", dims=d_dims, chunks=d_chunks),
        ]
        super(_ArcProcessPlugin, self).__init__(None)

    def create_extra_config_entries(self, rank, total):
        entries = super(_ArcProcessPlugin, self).create_extra_config_entries(self, rank)
        dimensions_entry = {
            self.NAME: {
                "width": self.dims.x_pixels,
                "height": self.dims.y_pixels,
            }
        }
        entries.append(create_config_entry(dimensions_entry))

        return entries

    ArgInfo = _FrameProcessorPlugin.ArgInfo + makeArgInfo(
        __init__, SUPER_MODULES=Simple("Super Module Count", int)
    )


class _ArcOdinData(_OdinData):

    CONFIG_TEMPLATES = {
        1: {"FrameProcessor": "fp_arc.json", "FrameReceiver": "fr_arc1.json"},
        2: {"FrameProcessor": "fp_arc.json", "FrameReceiver": "fr_arc2.json"},
    }

    def __init__(
        self, server, READY, RELEASE, META, PLUGINS, SUPER_MODULES, BASE_UDP_PORT
    ):
        super(_ArcOdinData, self).__init__(server, READY, RELEASE, META, PLUGINS)
        self.plugins = PLUGINS
        self.sensor = "Arc {} FEM".format(SUPER_MODULES)
        self.dims = ArcDimensions(SUPER_MODULES)
        self.base_udp_port = BASE_UDP_PORT

    def create_config_files(self, index, total):
        macros = dict(
            DETECTOR=OdinPaths.ARC_DETECTOR,
            RX_PORT_1=self.base_udp_port,
            RX_PORT_2=self.base_udp_port + 1,
            # 2 - 3 will be ignored in the 1FEM template
            RX_PORT_3=self.base_udp_port + 2,
            RX_PORT_4=self.base_udp_port + 3,
            WIDTH=self.dims.x_pixels,
            HEIGHT=self.dims.y_pixels,
        )

        if self.plugins is None:
            super(_ArcOdinData, self).create_config_file(
                "fp",
                self.CONFIG_TEMPLATES[self.dims.fem_count]["FrameProcessor"],
                extra_macros=macros,
            )
        else:
            super(_ArcOdinData, self).create_config_file(
                "fp", "fp_custom.json", extra_macros=macros
            )

        super(_ArcOdinData, self).create_config_file(
            "fr",
            self.CONFIG_TEMPLATES[self.dims.fem_count]["FrameReceiver"],
            extra_macros=macros,
        )


class _ArcModeTemplate(AutoSubstitution):
    TemplateFile = "ArcODMode.template"


class _ArcPluginConfig(_PluginConfig):
    # Class to define the standard set of plugins that an Arc Detector uses
    AutoInstantiate = True

    def __init__(self, dims=ArcDimensions(12)):
        arc = _ArcProcessPlugin(dims.fem_count)
        offset = _OffsetAdjustmentPlugin(source=arc)
        uid = _UIDAdjustmentPlugin(source=offset)
        sum = _SumPlugin(source=uid)
        # gap = _ArcGapFillPlugin(source=sum, dims=dims)
        view = _LiveViewPlugin(source=sum)
        hdf = _FileWriterPlugin(source=sum)
        super(_ArcPluginConfig, self).__init__(
            PLUGIN_1=arc,
            PLUGIN_3=offset,
            PLUGIN_4=uid,
            PLUGIN_5=sum,
            PLUGIN_6=view,
            PLUGIN_7=hdf,
            # PLUGIN_5=gap,
            # PLUGIN_7=blosc,
        )

        # Set the modes
        self.modes = ["compression", "no_compression"]

        # Now we need to create the no compression mode chain (no blosc in the chain)
        arc.add_mode("no_compression")
        offset.add_mode("no_compression", source=arc)
        uid.add_mode("no_compression", source=offset)
        sum.add_mode("no_compression", source=uid)
        # gap.add_mode("no_compression", source=sum)
        view.add_mode("no_compression", source=sum)
        hdf.add_mode("no_compression", source=sum)

    def detector_setup(self, od_args):
        # Make an instance of our template
        makeTemplateInstance(_ArcModeTemplate, locals(), od_args)


class ArcOdinDataServer(_OdinDataServer):

    """Store configuration for an ArcOdinDataServer"""

    BASE_UDP_PORT = 61000
    PLUGIN_CONFIG = None

    # TODO TODO In reality the Arc Server will have 4 FEM DEST NICs
    # so this class needs 4 sets of FEM details added OR the builder
    # model would need changing

    # for the moment with 1 FEM and n FR this works OK and I'm going to 
    # defer changes because I would prefer to rewrite a Python Odin 
    # config generator in Python3, supported by ibek and containerised
    # Odin IOCs
    def __init__(
        self,
        IP,
        PROCESSES,
        FEM_DEST_MAC,
        FEM_DEST_IP="10.0.2.2",
        FEM_DEST_SUBNET=24,
        FEM_DEST_NAME="em1",
        SUPER_MODULES=2,
        SHARED_MEM_SIZE=1048576000,
        PLUGIN_CONFIG=None
    ):
        self.sensor = "Arc {} FEM".format(SUPER_MODULES)
        dims = ArcDimensions(SUPER_MODULES)
        if PLUGIN_CONFIG is None:
            if ArcOdinDataServer.PLUGIN_CONFIG is None:
                # Create the standard Arc plugin config
                ArcOdinDataServer.PLUGIN_CONFIG = _ArcPluginConfig(dims)

        # Update attributes with parameters
        self.__dict__.update(locals())

        self.__super.__init__(
            IP, PROCESSES, SHARED_MEM_SIZE, ArcOdinDataServer.PLUGIN_CONFIG
        )

    ArgInfo = makeArgInfo(
        __init__,
        IP=Simple("IP address of server hosting OdinData processes", str),
        PROCESSES=Simple("Number of OdinData processes on this server", int),
        SUPER_MODULES=Simple("Number of super modules installed on detector", int),
        FEM_DEST_MAC=Simple(
            "MAC address of node data link (destination for FEM to send to)", str
        ),
        FEM_DEST_IP=Simple(
            "IP address of node data link (destination for FEM to send to)", str
        ),
        FEM_DEST_SUBNET=Simple(
            "Subnet bits of node data link IP (destination for FEM to send to)", str
        ),
        FEM_DEST_NAME=Simple(
            "NIC name of node data link (destination for FEM to send to)", str
        ),
        SHARED_MEM_SIZE=Simple("Size of shared memory buffers in bytes", int),
        PLUGIN_CONFIG=Ident("Define a custom set of plugins", _PluginConfig),
    )

    def create_odin_data_process(self, server, ready, release, meta, plugin_config):
        process = _ArcOdinData(
            server,
            ready,
            release,
            meta,
            plugin_config,
            self.SUPER_MODULES,
            self.BASE_UDP_PORT,
        )
        self.BASE_UDP_PORT += 1
        return process


class ArcOdinControlServer(_OdinControlServer):

    """Store configuration for an ArcOdinControlServer"""

    ODIN_SERVER = os.path.join(OdinPaths.ARC_DETECTOR_PYTHON3, "bin/arc_odin")
    CONFIG_TEMPLATES = {
        "1FEM": {
            "chip_mask": "0xFF",
            "fem_addresses": [
                "192.168.0.101:6969",
            ],
        },
        "2FEM": {
            "chip_mask": "0xFF, 0xFF",
            "fem_addresses": [
                "192.168.0.101:6969",
                "192.168.0.102:6969",
            ],
        },
    }

    def __init__(
        self,
        IP,
        PORT=8888,
        META_WRITER_IP=None,
        HARDWARE_ENDPOINT="tcp://127.0.0.1:10100",
        ODIN_DATA_SERVER_1=None,
        ODIN_DATA_SERVER_2=None,
        ODIN_DATA_SERVER_3=None,
        ODIN_DATA_SERVER_4=None,
    ):
        self.__dict__.update(locals())
        self.ADAPTERS.append("arc")

        super(ArcOdinControlServer, self).__init__(
            IP,
            PORT,
            META_WRITER_IP,
            ODIN_DATA_SERVER_1,
            ODIN_DATA_SERVER_2,
            ODIN_DATA_SERVER_3,
            ODIN_DATA_SERVER_4,
        )

    # __init__ arguments
    ArgInfo = makeArgInfo(
        __init__,
        IP=Simple("IP address of control server", str),
        PORT=Simple("Port of control server", int),
        HARDWARE_ENDPOINT=Simple("Detector endpoint", str),
        META_WRITER_IP=Simple(
            "IP address of MetaWriter (None -> first OdinDataServer)", str
        ),
        ODIN_DATA_SERVER_1=Ident("OdinDataServer 1 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_2=Ident("OdinDataServer 2 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_3=Ident("OdinDataServer 3 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_4=Ident("OdinDataServer 4 configuration", _OdinDataServer),
    )

    def _add_python_modules(self):
        # return nothing since the python3 venv for arc odin server already has the
        # required dependencies
        pass

    def get_extra_startup_macro(self):
        return (
            "--staticlogfields beamline=${BEAMLINE},"
            'application_name="arc_odin",detector="Arc" '
            '--logserver="graylog2.diamond.ac.uk:12210" --access_logging=ERROR'
        )

    def create_extra_config_entries(self):
        return [self._create_arc_config_entry()]

    def create_odin_server_static_path(self):
        return OdinPaths.ARC_DETECTOR + "/prefix/html/static"

    def _create_arc_config_entry(self):
        upd_path = os.path.join('.',  'udp_arc.json')
        return (
            "[adapter.arc]\n"
            "module = arc.arc_adapter.ArcAdapter\n"
            "endpoint = {}\n"
            "firmware = 0.0.1\n"
            "udp_file = {}\n".format(self.HARDWARE_ENDPOINT, upd_path)
        )

    def _create_odin_data_config_entry(self):
        fp_endpoints = []
        fr_endpoints = []
        for process in sorted(self.odin_data_processes, key=lambda x: x.RANK):
            fp_endpoints.append(process.FP_ENDPOINT)
            fr_endpoints.append(process.FR_ENDPOINT)

        return (
            "[adapter.fp]\n"
            "module = odin_data.frame_processor_adapter.FrameProcessorAdapter\n"
            "endpoints = {}\n"
            "update_interval = 0.2\n"
            "datasets = data,data2\n\n"
            "[adapter.fr]\n"
            "module = odin_data.frame_receiver_adapter.FrameReceiverAdapter\n"
            "endpoints = {}\n"
            "update_interval = 0.2".format(
                ", ".join(fp_endpoints), ", ".join(fr_endpoints)
            )
        )


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

    cls.Arguments = _ArcFPTemplate.Arguments + [
        x for x in cls.Arguments if x not in _ArcFPTemplate.Arguments
    ]
    cls.Arguments = [
        entry for entry in cls.Arguments if entry not in template_substitutions
    ]

    cls.ArgInfo = _ArcFPTemplate.ArgInfo + cls.ArgInfo.filtered(
        without=_ArcFPTemplate.ArgInfo.Names()
    )
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
            raise ValueError(
                "Total number of OdinData processes must be {}".format(
                    self.FP_TEMPLATES.keys()
                )
            )
        else:
            template_args = dict(
                P=args["P"],
                R=":OD:",
                DET=detector_arg,
                PORT=args["PORT"],
                TIMEOUT=args["TIMEOUT"],
                **self.create_gui_macros(args["PORT"])
            )
            _ArcXNodeFPTemplate = self.FP_TEMPLATES[len(self.ODIN_DATA_PROCESSES)]
            _ArcXNodeFPTemplate(**template_args)

    # __init__ arguments
    ArgInfo = _OdinDataDriver.ArgInfo.filtered(without=["DETECTOR", "TOTAL", "R"])


class ArcDetector(_OdinDetector):

    """Create an Arc detector"""

    DETECTOR = "arc"

    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = "PORT"

    _SpecificTemplate = _ArcDetectorTemplate

    # We don't really need the OdinDataDriver, but we need to know it is instantiated as it
    # defines the RANK on all the OdinData instances and we need to sort by RANK for the UDP config
    def __init__(
        self,
        PORT,
        ODIN_CONTROL_SERVER,
        ODIN_DATA_DRIVER,
        FEMS=1,
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

        # Instantiate template corresponding to SENSOR, passing through some of own args
        # TODO add status template
        # status_template = self.SENSOR_OPTIONS[SENSOR][0]
        # gui_name = PORT[: PORT.find(".")] + ".Detector"
        # status_args = {
        #     "P": args["P"],
        #     "R": args["R"],
        #     "ADDRESS": "0",
        #     "PORT": PORT,
        #     "NAME": gui_name,
        #     "TIMEOUT": args["TIMEOUT"],
        #     "TOTAL": self.SENSOR_OPTIONS[SENSOR][2],
        # }
        # status_template(**status_args)

        self.create_udp_file()

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
            FEMS=Simple("FEM Count", int),
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

    def create_udp_file(self):
        nodes = self.generate_point_to_point_config()
        div_floor, div_rem = divmod(len(nodes), self.FEMS)
        # Split the list of all available nodes (FR applications) into equally sized lists
        node_list = list(nodes[i * div_floor + min(i, div_rem):(i + 1)
         * div_floor + min(i + 1, div_rem)] for i in range(self.FEMS))

        udp_config = {}
        # Now loop over the modules, creating a full node list for each
        # After each iteration, move the first block of nodes to the back of the list
        # This creates a round robin list for each module across all nodes, with each
        # starting node spread equally across all available nodes
        for index in range(self.FEMS):
            module_key = "module{:02d}".format(index+1)
            module_nodes = [element for node in node_list for element in node]
            udp_config[module_key] = {'nodes': module_nodes}
            first_node = node_list[0]
            node_list = node_list[1:]
            node_list.append(first_node)

        # Generate the udp configuration file
        macros = dict(
            MODULE_CONFIG=create_config_entry(udp_config)
        )

        expand_template_file("udp_arc.json", macros, "udp_arc.json")

    def generate_point_to_point_config(self):
        node_config = []
        for server in self.control_server.odin_data_servers:
            fem_config = []
            for idx, process in enumerate(sorted(server.processes, key=lambda x: x.RANK)):
                config = dict(
                    mac=process.server.FEM_DEST_MAC,
                    name=process.server.FEM_DEST_NAME,
                    ipaddr=process.server.FEM_DEST_IP,
                    port=process.base_udp_port,
                    subnet=process.server.FEM_DEST_SUBNET,
                    links=[1, 1, 0, 0, 0, 0, 0, 0]
                )
                fem_config.append(config)
            node_config.append(fem_config)
        return node_config

class _ArcGapFillPlugin(_FrameProcessorPlugin):

    NAME = "gap"
    CLASS_NAME = "GapFillPlugin"

    def __init__(self, source=None, dims=ArcDimensions(12)):
        super(_ArcGapFillPlugin, self).__init__(source)
        # TODO work out gaps from the dims values
        self.sensor = SENSOR
        self.chip_gap = CHIP_GAP
        self.module_gap = MODULE_GAP

    def create_extra_config_entries(self, rank, total):
        entries = []

        chip_size = [
            ArcDimensions.FEM_PIXELS_PER_CHIP_X,
            ArcDimensions.FEM_PIXELS_PER_CHIP_Y,
        ]
        x_gaps = [0] + [self.chip_gap] * 7 + [0]
        # TODO these will need adjusting
        if self.sensor == "1FEM":
            grid_size = [2, 8]
            y_gaps = [0, self.chip_gap, 0]
        else:
            grid_size = [6, 8]
            y_gaps = [
                0,
                self.chip_gap,
                self.module_gap,
                self.chip_gap,
                self.module_gap,
                self.chip_gap,
                0,
            ]

        layout_config = {
            self.NAME: {
                "grid_size": grid_size,
                "chip_size": chip_size,
                "x_gaps": x_gaps,
                "y_gaps": y_gaps,
            }
        }
        entries.append(create_config_entry(layout_config))

        dimensions = [
            ARC_DIMENSIONS[self.sensor][1] + sum(y_gaps),
            ARC_DIMENSIONS[self.sensor][0] + sum(x_gaps),
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
