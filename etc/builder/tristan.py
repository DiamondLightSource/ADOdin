import os
import json

from iocbuilder import Device, AutoSubstitution
from iocbuilder.arginfo import makeArgInfo, Simple, Ident, Choice
from iocbuilder.modules.ADCore import ADBaseTemplate, makeTemplateInstance

from plugins import _DatasetCreationPlugin, _FileWriterPlugin
from util import OdinPaths, expand_template_file, debug_print, create_batch_entry, create_config_entry
from odin import (
    _OdinDetector, _OdinData, _OdinDataDriver, _OdinDataServer, _OdinControlServer,
    _PluginConfig
)

debug_print("Tristan: {}".format(OdinPaths.TRISTAN_DETECTOR), 1)

TRISTAN_DIMENSIONS = {
    # Sensor: (Width, Height)
    "1M": (2048, 512),
    "2M": (2048, 1024),
    "10M": (4096, 2560)
}


class _TristanProcessPlugin(_DatasetCreationPlugin):

    NAME = "tristan"
    CLASS_NAME = "LATRDProcessPlugin"
    LIBRARY_PATH = OdinPaths.TRISTAN_DETECTOR
    DATASETS = [
        dict(name="raw_data", type="uint64", chunks=[524288]),
        dict(name="event_id", type="uint32", chunks=[524288]),
        dict(name="event_time_offset", type="uint64", chunks=[524288]),
        dict(name="event_energy", type="uint32", chunks=[524288]),
        dict(name="image", type="uint16", dims=[512, 2048], chunks=[1, 512, 2048]),
        dict(name="time_slice", type="uint32", chunks=[40])
    ]

    def __init__(self, sensor):
        super(_TristanProcessPlugin, self).__init__(None)
        self._sensor = sensor

    def create_extra_config_entries(self, rank, total):
        entries = []
        entries = super(_TristanProcessPlugin, self).create_extra_config_entries(rank, total)
        entries.append(
            create_config_entry(
                {
                    self.NAME: {
                        "process": {
                            "number": total,
                            "rank": rank
                        },
                        "sensor": {
                            "width": TRISTAN_DIMENSIONS[self._sensor][0],
                            "height": TRISTAN_DIMENSIONS[self._sensor][1]
                        }
                    }
                }
            )
        )

        return entries


class _TristanMetaListenerTemplate(AutoSubstitution):
    TemplateFile = "MetaListener.template"


class _TristanMetaListener(Device):

    """Create startup file for a TristanMetaListener process"""

    # Device attributes
    AutoInstantiate = True

    def __init__(self, IP, ODIN_DATA_SERVERS=None, NUMA_NODE=-1, **args):
        self.__super.__init__()
        # Update attributes with parameters
        self.__dict__.update(locals())

        self.ip_list = []
        self.sensor = None
        if ODIN_DATA_SERVERS is not None:
            for server in ODIN_DATA_SERVERS:
                if server is not None:
                    base_port = 5000
                    for odin_data in server.processes:
                        port = base_port + 8
                        self.ip_list.append("tcp://{}:{}".format(odin_data.IP, port))
                        base_port += 10
                        self.set_sensor(odin_data.sensor)

        self.create_startup_file()

    def set_sensor(self, sensor):
        if self.sensor is None:
            self.sensor = sensor
        else:
            if self.sensor != sensor:
                raise ValueError("Inconsistent sensor sizes given on OdinData processes")

    def create_startup_file(self):
        if self.NUMA_NODE >= 0:
            numa_call = "numactl --membind={node} --cpunodebind={node} ".format(node=self.NUMA_NODE)
        else:
            numa_call = ""
        macros = dict(TRISTAN_DETECTOR_PATH=OdinPaths.TRISTAN_DETECTOR,
                      IP_LIST=",".join(self.ip_list),
                      ODIN_DATA=OdinPaths.ODIN_DATA,
                      SENSOR=self.sensor,
                      NUMA=numa_call)

        expand_template_file("tristan_meta_startup", macros, "stTristanMetaListener.sh",
                             executable=True)

    def add_batch_entry(self, entries, beamline, number):
        entries.append(create_batch_entry(beamline, number, "TristanMetaListener"))
        return number + 1


class TristanControlSimulator(Device):

    # Device attributes
    AutoInstantiate = True

    """Store configuration for an TristanOdinControlServer"""
    def __init__(self, PORT=10100, **args):
        self.__dict__.update(locals())
        macros = dict(TRISTAN_DETECTOR_PATH=OdinPaths.TRISTAN_DETECTOR,
                      PORT=PORT)

        expand_template_file("tristan_simulator_startup", macros, "stTristanSimulator.sh", executable=True)
        super(TristanControlSimulator, self).__init__()

    # __init__ arguments
    ArgInfo = makeArgInfo(__init__,
        PORT=Simple("Port number of the simulator", int)
    )


class TristanOdinControlServer(_OdinControlServer):

    """Store configuration for an TristanOdinControlServer"""

    ODIN_SERVER = os.path.join(OdinPaths.TRISTAN_DETECTOR, "prefix/bin/tristan_odin")

    def __init__(self, IP, PORT=8888,
                 HARDWARE_ENDPOINT="tcp://127.0.0.1:10100",
                 META_IP=None,
                 ODIN_DATA_SERVER_1=None, ODIN_DATA_SERVER_2=None,
                 ODIN_DATA_SERVER_3=None, ODIN_DATA_SERVER_4=None,
                 ODIN_DATA_SERVER_5=None, ODIN_DATA_SERVER_6=None,
                 ODIN_DATA_SERVER_7=None, ODIN_DATA_SERVER_8=None,
                 ODIN_DATA_SERVER_9=None, ODIN_DATA_SERVER_10=None):
        self.__dict__.update(locals())
        self.ADAPTERS.append("tristan")
        if self.META_IP is not None:
            self.ADAPTERS.append("meta_listener")

        super(TristanOdinControlServer, self).__init__(
            IP, PORT,
            ODIN_DATA_SERVER_1,
            ODIN_DATA_SERVER_2,
            ODIN_DATA_SERVER_3,
            ODIN_DATA_SERVER_4,
            ODIN_DATA_SERVER_5,
            ODIN_DATA_SERVER_6,
            ODIN_DATA_SERVER_7,
            ODIN_DATA_SERVER_8,
            ODIN_DATA_SERVER_9,
            ODIN_DATA_SERVER_10
        )

    # __init__ arguments
    ArgInfo = makeArgInfo(__init__,
        IP=Simple("IP address of control server", str),
        PORT=Simple("Port of control server", int),
        HARDWARE_ENDPOINT=Simple("Detector endpoint", str),
        META_IP=Simple("IP address of meta listener", str),
        ODIN_DATA_SERVER_1=Ident("OdinDataServer 1 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_2=Ident("OdinDataServer 2 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_3=Ident("OdinDataServer 3 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_4=Ident("OdinDataServer 4 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_5=Ident("OdinDataServer 5 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_6=Ident("OdinDataServer 6 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_7=Ident("OdinDataServer 7 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_8=Ident("OdinDataServer 8 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_9=Ident("OdinDataServer 9 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_10=Ident("OdinDataServer 10 configuration", _OdinDataServer)
    )

    def create_odin_server_config_entries(self):
        config_entries = [
            self._create_tristan_config_entry(),
            self._create_odin_data_config_entry()
            ]
        if self.META_IP is not None:
            config_entries.append(self._create_meta_listener_config_entry())
        return config_entries

    def create_odin_server_static_path(self):
        return OdinPaths.TRISTAN_DETECTOR + "/prefix/html/static"

    def _create_tristan_config_entry(self):
        return (
            "[adapter.tristan]\n"
            "module = latrd.detector.tristan_control_adapter.TristanControlAdapter\n"
            "endpoint = {}\n"
            "firmware = 0.0.1"
        ).format(self.HARDWARE_ENDPOINT)

    def _create_meta_listener_config_entry(self):
        return (
            "[adapter.meta_listener]\n"
            "module = odin_data.meta_listener_adapter.MetaListenerAdapter\n"
            "endpoints = {}:5659\n"
            "update_interval = 0.5"
        ).format(self.META_IP)


class _TristanDetectorTemplate(AutoSubstitution):
    TemplateFile = "TristanDetector.template"


class _TristanStatusTemplate(AutoSubstitution):
    WarnMacros = False
    TemplateFile = "TristanStatus.template"


def add_tristan_status(cls):
    """Convenience function to add tristanStatusTemplate attributes to a class that
    includes it via an msi include statement rather than verbatim"""
    cls.Arguments = (
        _TristanStatusTemplate.Arguments +
        [x for x in cls.Arguments if x not in _TristanStatusTemplate.Arguments]
    )
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
    cls.Arguments = (
        _TristanFemStatusTemplate.Arguments +
        [x for x in cls.Arguments if x not in _TristanFemStatusTemplate.Arguments]
    )
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
class _Tristan2MStatusTemplate(AutoSubstitution):
    TemplateFile = "Tristan2MStatus.template"


@add_tristan_status
@add_tristan_fem_status
class _Tristan10MStatusTemplate(AutoSubstitution):
    TemplateFile = "Tristan10MStatus.template"


class TristanDetector(_OdinDetector):

    """Create a Tristan detector"""

    DETECTOR = "tristan"
    SENSOR_OPTIONS = {  # (AutoSubstitution Template, Number of modules)
        "1M": (_Tristan1MStatusTemplate, 1),
        "2M": (_Tristan2MStatusTemplate, 2),
        "10M": (_Tristan10MStatusTemplate, 10)
    }

    UDP_OPTIONS = [
        "ROUNDROBIN",
        "ONE2ONE"
    ]

    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = "PORT"

    _SpecificTemplate = _TristanDetectorTemplate

    # We don't really need the OdinDataDriver, but we need to know it is instantiated as it
    # defines the RANK on all the OdinData instances and we need to sort by RANK for the UDP config
    def __init__(self, PORT, ODIN_CONTROL_SERVER, ODIN_DATA_DRIVER, SENSOR,
                 UDP_CONFIG='ROUNDROBIN', BUFFERS=0, MEMORY=0, **args):
        # Init the superclass (OdinDetector)
        self.__super.__init__(PORT, ODIN_CONTROL_SERVER, self.DETECTOR,
                              BUFFERS, MEMORY, **args)
        # Update the attributes of self from the commandline args
        self.__dict__.update(locals())
        # Make an instance of our template
        makeTemplateInstance(self._SpecificTemplate, locals(), args)

        self.control_server = ODIN_CONTROL_SERVER

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

        if self.UDP_CONFIG == 'ROUNDROBIN':
            self.create_round_robin_udp_file()
        elif self.UDP_CONFIG == 'ONE2ONE':
            self.create_one_to_one_udp_file()

    def create_one_to_one_udp_file(self):
        nodes = self.generate_point_to_point_config()
        # Now verify the number of lists matches the number of nodes
        if self.SENSOR_OPTIONS[self.SENSOR][1] != len(nodes):
            raise ValueError("Number of FEMs does not match number of servers")

        udp_config = {}
        # Loop over the fems to create a one to one mapping
        for index in range(self.SENSOR_OPTIONS[self.SENSOR][1]):
            module_key = "module{:02d}".format(index+1)
            udp_config[module_key] = {'nodes': nodes[index]}

        # Generate the udp configuration file
        macros = dict(
            MODULE_CONFIG="{}".format(json.dumps(udp_config, indent=4, sort_keys=True))
        )
        expand_template_file("udp_tristan.json", macros, "udp_tristan.json")

    def create_round_robin_udp_file(self):
        nodes = self.generate_multi_server_config()
        fems = self.SENSOR_OPTIONS[self.SENSOR][1]
        div_floor, div_rem = divmod(len(nodes), fems)
        # Split the list of all available nodes (FR applications) into equally sized lists
        node_list = list(nodes[i * div_floor + min(i, div_rem):(i + 1) * div_floor + min(i + 1, div_rem)] for i in range(fems))

        udp_config = {}
        # Now loop over the modules, creating a full node list for each
        # After each iteration, move the first block of nodes to the back of the list
        # This creates a round robin list for each module across all nodes, with each
        # starting node spread equally across all available nodes
        for index in range(fems):
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
        expand_template_file("udp_tristan.json", macros, "udp_tristan.json")

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
                    links=[1, 0, 0, 0, 0, 0, 0, 0]
                )
                fem_config.append(config)
            node_config.append(fem_config)
        return node_config

    def generate_multi_server_config(self):
        node_config = []
        for server in self.control_server.odin_data_servers:
            for idx, process in enumerate(sorted(server.processes, key=lambda x: x.RANK)):
                config = dict(
                    mac=process.server.FEM_DEST_MAC,
                    name=process.server.FEM_DEST_NAME,
                    ipaddr=process.server.FEM_DEST_IP,
                    port=process.base_udp_port,
                    subnet=process.server.FEM_DEST_SUBNET,
                    links=[1, 0, 0, 0, 0, 0, 0, 0]
                )
                node_config.append(config)

        return node_config

    # __init__ arguments
    ArgInfo = (
        ADBaseTemplate.ArgInfo +
        _SpecificTemplate.ArgInfo +
        makeArgInfo(__init__,
            PORT=Simple("Port name for the detector", str),
            ODIN_CONTROL_SERVER=Ident("Odin control server instance", _OdinControlServer),
            ODIN_DATA_DRIVER=Ident("OdinDataDriver instance", _OdinDataDriver),
            SENSOR=Choice("Sensor type", SENSOR_OPTIONS.keys()),
            UDP_CONFIG=Choice("Type of packet distribution", UDP_OPTIONS),
            BUFFERS=Simple("Maximum number of NDArray buffers to be created for plugin callbacks", int),
            MEMORY=Simple("Max memory to allocate, should be maxw*maxh*nbuffer for driver and all "
                          "attached plugins", int)
        )
    )


class _TristanOdinData(_OdinData):

    CONFIG_TEMPLATES = {
        "1M": {
            "FrameProcessor": "fp_tristan.json",
            "FrameReceiver": "fr_tristan.json"
        },
        "10M": {
            "FrameProcessor": "fp_tristan.json",
            "FrameReceiver": "fr_tristan.json"
        }
    }

    def __init__(self, server, READY, RELEASE, META, SENSOR, BASE_UDP_PORT):
        # Create the Tristan plugin chain
        tristan_plugin = _TristanProcessPlugin(SENSOR)
        fw_plugin = _FileWriterPlugin(source=tristan_plugin)
        plugins = _PluginConfig(
            PLUGIN_1=tristan_plugin,
            PLUGIN_2=fw_plugin
        )

        super(_TristanOdinData, self).__init__(server, READY, RELEASE, META, plugins)
        self.sensor = SENSOR
        self.base_udp_port = BASE_UDP_PORT

    def create_config_files(self, index, total):
        macros = dict(DETECTOR_ROOT=OdinPaths.TRISTAN_DETECTOR,
                      PROC_NUMBER=total,
                      PROC_RANK=index-1,
                      RX_PORT_1=self.base_udp_port,
                      RX_PORT_2=self.base_udp_port + 1,
                      RX_PORT_3=self.base_udp_port + 2,
                      RX_PORT_4=self.base_udp_port + 3,
                      WIDTH=TRISTAN_DIMENSIONS[self.sensor][0],
                      HEIGHT=TRISTAN_DIMENSIONS[self.sensor][1])

        # Generate the frame processor config files
#        super(_TristanOdinData, self).create_config_file(
#            "fp", self.CONFIG_TEMPLATES[self.sensor]["FrameProcessor"], extra_macros=macros
#        )
        super(_TristanOdinData, self).create_config_file(
            "fp", "fp_custom.json", extra_macros=macros
        )

        # Generate the frame receiver config files
        super(_TristanOdinData, self).create_config_file(
            "fr", self.CONFIG_TEMPLATES[self.sensor]["FrameReceiver"], extra_macros=macros
        )


class TristanOdinDataServer(_OdinDataServer):

    """Store configuration for a TristanOdinDataServer"""

    BASE_UDP_PORT = 61649

    def __init__(self, IP, PROCESSES, SENSOR, FEM_DEST_MAC, FEM_DEST_IP="127.0.0.1",
                 FEM_DEST_NAME="em0", FEM_DEST_SUBNET=24,
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
        FEM_DEST_NAME=Simple("Name of the destination netowrk interface", str),
        FEM_DEST_SUBNET=Simple("Subnet mask node transmits on", int),
        SHARED_MEM_SIZE=Simple("Size of shared memory buffers in bytes", int),
        PLUGIN_CONFIG=Ident("Define a custom set of plugins", _PluginConfig)
    )

    def create_odin_data_process(self, server, ready, release, meta, plugin_config):
        process = _TristanOdinData(server, ready, release, meta, self.sensor, self.BASE_UDP_PORT)
        self.BASE_UDP_PORT += 1
        return process


class _TristanFPTemplate(AutoSubstitution):
    TemplateFile = "TristanOD.template"


def add_tristan_fp_template(cls):
    """Convenience function to add tristanFPTemplate attributes to a class that
    includes it via an msi include statement rather than verbatim"""
    template_substitutions = ["TOTAL", "ADDRESS"]

    cls.Arguments = (
        _TristanFPTemplate.Arguments +
        [x for x in cls.Arguments if x not in _TristanFPTemplate.Arguments]
    )
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


@add_tristan_fp_template
class _Tristan16NodeFPTemplate(AutoSubstitution):
    TemplateFile = "Tristan16NodeOD.template"


class TristanOdinDataDriver(_OdinDataDriver):

    """Create a Tristan OdinData driver"""

    FP_TEMPLATES = {
        # Number of OdinData nodes: Template
        4: _Tristan4NodeFPTemplate,
        8: _Tristan8NodeFPTemplate,
        16: _Tristan16NodeFPTemplate
    }

    def __init__(self, **args):
        detector_arg = args["R"]
        args["R"] = ":OD:"
        self.__super.__init__(DETECTOR="tristan", **args)
        # Update the attributes of self from the commandline args
        self.__dict__.update(locals())

        if self.control_server.META_IP is not None:
            self._meta = _TristanMetaListener(
                IP=self.control_server.META_IP,
                ODIN_DATA_SERVERS=self.control_server.odin_data_servers
            )

        if self.odin_data_processes not in self.FP_TEMPLATES.keys():
            raise ValueError(
                "Total number of OdinData processes must be {}".format(self.FP_TEMPLATES.keys())
            )
        else:
            sensor = self.ODIN_DATA_PROCESSES[0].sensor
            gui_name = args["PORT"][:args["PORT"].find(".")] + ".OdinHDF"
            template_args = {
                "P": args["P"],
                "R": ":OD:",
                "DET": detector_arg,
                "PORT": args["PORT"],
                "name": gui_name,
                "TIMEOUT": args["TIMEOUT"]
            }
            _TristanXNodeFPTemplate = self.FP_TEMPLATES[len(self.ODIN_DATA_PROCESSES)]
            _TristanXNodeFPTemplate(**template_args)

            if self.control_server.META_IP is not None:
                template_args = {
                    "P": args["P"],
                    "R": ":OD:",
                    "PORT": args["PORT"]
                }
                _TristanMetaListenerTemplate(**template_args)

    # __init__ arguments
    ArgInfo = _OdinDataDriver.ArgInfo.filtered(without=["DETECTOR"])
