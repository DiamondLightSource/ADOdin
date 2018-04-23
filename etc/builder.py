from iocbuilder import AutoSubstitution, Device
from iocbuilder.arginfo import makeArgInfo, Simple, Ident, Choice
from iocbuilder.iocinit import IocDataStream
from iocbuilder.modules.asyn import AsynPort
from iocbuilder.modules.ADCore import ADCore, ADBaseTemplate, makeTemplateInstance
from iocbuilder.modules.restClient import restClient
from iocbuilder.modules.OdinData import FileWriterPlugin
from iocbuilder.modules.ExcaliburDetector import ExcaliburProcessPlugin, ExcaliburReceiverPlugin

import os
from string import Template

FILE_WRITER_ROOT = FileWriterPlugin.ModuleVersion.LibPath()
EXCALIBUR_ROOT = ExcaliburProcessPlugin.ModuleVersion.LibPath()

DATA = os.path.join(os.path.dirname(__file__), "../data")

__all__ = ["ExcaliburDetector", "OdinDataServer"]


class OdinDetectorTemplate(AutoSubstitution):
    TemplateFile = "odinDetector.template"


class OdinDetector(AsynPort):

    """Create an odin detector"""

    Dependencies = (ADCore, restClient)

    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = "PORT"

    def __init__(self, PORT, SERVER, ODIN_SERVER_PORT, DETECTOR, BUFFERS = 0, MEMORY = 0, **args):
        # Init the superclass (AsynPort)
        self.__super.__init__(PORT)
        # Update the attributes of self from the commandline args
        self.__dict__.update(locals())

    # __init__ arguments
    ArgInfo = ADBaseTemplate.ArgInfo + makeArgInfo(__init__,
        PORT=Simple("Port name for the detector", str),
        SERVER=Simple("Server host name", str),
        ODIN_SERVER_PORT=Simple("Odin server port", int),
        DETECTOR=Simple("Name of detector", str),
        BUFFERS=Simple("Maximum number of NDArray buffers to be created for plugin callbacks", int),
        MEMORY=Simple("Max memory to allocate, should be maxw*maxh*nbuffer for driver and all "
                      "attached plugins", int))

    # Device attributes
    LibFileList = ['odinDetector']
    DbdFileList = ['odinDetectorSupport']

    def Initialise(self):
        print "# odinDetectorConfig(const char * portName, const char * serverPort, " \
              "int odinServerPort, const char * detectorName, " \
              "int maxBuffers, size_t maxMemory, int priority, int stackSize)"
        print "odinDetectorConfig(\"%(PORT)s\", \"%(SERVER)s\", " \
              "%(ODIN_SERVER_PORT)d, \"%(DETECTOR)s\", " \
              "%(BUFFERS)d, %(MEMORY)d)" % self.__dict__
              
    def daq_templates(self):
        return None


class ExcaliburDetectorTemplate(AutoSubstitution):
    TemplateFile = "excaliburDetector.template"


class ExcaliburFPTemplate(AutoSubstitution):
    TemplateFile = "excaliburFP.template"


def add_excalibur_fp_template(cls):
    """Convenience function to add excaliburFPTemplate attributes to a class that
    includes it via an msi include statement rather than verbatim"""
    cls.Arguments = ExcaliburFPTemplate.Arguments + \
        [x for x in cls.Arguments if x not in ExcaliburFPTemplate.Arguments]
    cls.ArgInfo = ExcaliburFPTemplate.ArgInfo + cls.ArgInfo.filtered(
        without=ExcaliburFPTemplate.ArgInfo.Names())
    cls.Defaults.update(ExcaliburFPTemplate.Defaults)
    return cls


@add_excalibur_fp_template
class Excalibur2NodeFPTemplate(AutoSubstitution):
    TemplateFile = "excalibur2NodeFP.template"


@add_excalibur_fp_template
class Excalibur4NodeFPTemplate(AutoSubstitution):
    TemplateFile = "excalibur4NodeFP.template"


class ExcaliburFemHousekeepingTemplate(AutoSubstitution):
    TemplateFile = "excaliburFemHousekeeping.template"


class ExcaliburFemStatusTemplate(AutoSubstitution):
    WarnMacros = False
    TemplateFile = "excaliburFemStatus.template"


def add_excalibur_fem_status(cls):
    """Convenience function to add excaliburFemStatusTemplate attributes to a class that
    includes it via an msi include statement rather than verbatim"""
    cls.Arguments = ExcaliburFemStatusTemplate.Arguments + \
        [x for x in cls.Arguments if x not in ExcaliburFemStatusTemplate.Arguments]
    cls.ArgInfo = ExcaliburFemStatusTemplate.ArgInfo + cls.ArgInfo.filtered(
        without=ExcaliburFemStatusTemplate.ArgInfo.Names())
    cls.Defaults.update(ExcaliburFemStatusTemplate.Defaults)
    return cls


@add_excalibur_fem_status
class Excalibur2FemStatusTemplate(AutoSubstitution):
    TemplateFile = "excalibur2FemStatus.template"


@add_excalibur_fem_status
class Excalibur6FemStatusTemplate(AutoSubstitution):
    TemplateFile = "excalibur6FemStatus.template"


class ExcaliburDetector(OdinDetector):

    """Create an Excalibur detector"""

    DETECTOR = "excalibur"
    SENSOR_OPTIONS = {  # (AutoSubstitution Template, Number of FEMs)
        "1M": (Excalibur2FemStatusTemplate, 2),
        "3M": (Excalibur6FemStatusTemplate, 6)
    }

    CONFIG_TEMPLATES = {
        "1M": {
                "ProcessPlugin": "fp_excalibur_1m.json",
                "ReceiverPlugin": "fr_excalibur_1m.json"
              },
        "3M": {
                "ProcessPlugin": "fp_excalibur_3m.json",
                "ReceiverPlugin": "fr_excalibur_3m.json"
              }
    }

    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = "PORT"

    _SpecificTemplate = ExcaliburDetectorTemplate

    def __init__(self, PORT, SERVER, ODIN_SERVER_PORT, SENSOR, BUFFERS = 0, MEMORY = 0, NODE_1_NAME = None, NODE_1_MAC = None, NODE_1_IPADDR = None, NODE_1_PORT = None, NODE_2_NAME = None, NODE_2_MAC = None, NODE_2_IPADDR = None, NODE_2_PORT = None, NODE_3_NAME = None, NODE_3_MAC = None, NODE_3_IPADDR = None, NODE_3_PORT = None, NODE_4_NAME = None, NODE_4_MAC = None, NODE_4_IPADDR = None, NODE_4_PORT = None, **args):
        # Init the superclass (OdinDetector)
        self.__super.__init__(PORT, SERVER, ODIN_SERVER_PORT, self.DETECTOR,
                              BUFFERS, MEMORY, **args)
        # Update the attributes of self from the commandline args
        self.__dict__.update(locals())
        # Make an instance of our template
        makeTemplateInstance(self._SpecificTemplate, locals(), args)

        # Add the FEM housekeeping template
        fem_hk_template = ExcaliburFemHousekeepingTemplate
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
        status_args = {
            "P": args["P"],
            "R": args["R"],
            "ADDRESS": "0",
            "PORT": PORT,
            "TIMEOUT": args["TIMEOUT"],
            "TOTAL": self.SENSOR_OPTIONS[SENSOR][1]
        }
        status_template(**status_args)
        
        self.create_udp_file()

    def daq_templates(self):
        print str(self.CONFIG_TEMPLATES[self.SENSOR])
        return self.CONFIG_TEMPLATES[self.SENSOR]

    def create_udp_file(self):
        output_file = IocDataStream("udp_excalibur.json")
        number_of_nodes = 0
        output_text = '{\n\
    "fems": [\n\
        {\n\
            "name": "fem1",\n\
            "mac": "62:00:00:00:00:01",\n\
            "ipaddr": "10.0.2.101",\n\
            "port": 60001,\n\
            "dest_port_offset": 0\n\
        },\n\
        {\n\
            "name": "fem2",\n\
            "mac": "62:00:00:00:00:02",\n\
            "ipaddr": "10.0.2.102",\n\
            "port": 60002,\n\
            "dest_port_offset": 1\n\
        },\n\
        {\n\
            "name": "fem3",\n\
            "mac": "62:00:00:00:00:03",\n\
            "ipaddr": "10.0.2.103",\n\
            "port": 60003,\n\
            "dest_port_offset": 2\n\
        },\n\
        {\n\
            "name": "fem4",\n\
            "mac": "62:00:00:00:00:04",\n\
            "ipaddr": "10.0.2.104",\n\
            "port": 60004,\n\
            "dest_port_offset": 3\n\
        },\n\
        {\n\
            "name": "fem5",\n\
            "mac": "62:00:00:00:00:05",\n\
            "ipaddr": "10.0.2.105",\n\
            "port": 60005,\n\
            "dest_port_offset": 4\n\
        },\n\
        {\n\
            "name": "fem6",\n\
            "mac": "62:00:00:00:00:06",\n\
            "ipaddr": "10.0.2.106",\n\
            "port": 60006,\n\
            "dest_port_offset": 5\n\
        }\n\
    ],\n\
    "nodes": [\n'
    
        if self.NODE_1_NAME is not None:
            output_text = output_text + '        {{\n\
            "name": "{}",\n\
            "mac" : "{}",\n\
            "ipaddr" : "{}",\n\
            "port": {}\n\
        }}'.format(self.NODE_1_NAME,
                   self.NODE_1_MAC,
                   self.NODE_1_IPADDR,
                   self.NODE_1_PORT)
            number_of_nodes += 1
            
        if self.NODE_2_NAME is not None:
            if number_of_nodes > 0:
                output_text = output_text + ',\n'
            
            output_text = output_text + '        {{\n\
            "name": "{}",\n\
            "mac" : "{}",\n\
            "ipaddr" : "{}",\n\
            "port": {}\n\
        }}'.format(self.NODE_2_NAME,
                   self.NODE_2_MAC,
                   self.NODE_2_IPADDR,
                   self.NODE_2_PORT)
            number_of_nodes += 1
            
        if self.NODE_3_NAME is not None:
            if number_of_nodes > 0:
                output_text = output_text + ',\n'
            
            output_text = output_text + '        {{\n\
            "name": "{}",\n\
            "mac" : "{}",\n\
            "ipaddr" : "{}",\n\
            "port": {}\n\
        }}'.format(self.NODE_3_NAME,
                   self.NODE_3_MAC,
                   self.NODE_3_IPADDR,
                   self.NODE_3_PORT)
            number_of_nodes += 1
            
        if self.NODE_4_NAME is not None:
            if number_of_nodes > 0:
                output_text = output_text + ',\n'
            
            output_text = output_text + '        {{\n\
            "name": "{}",\n\
            "mac" : "{}",\n\
            "ipaddr" : "{}",\n\
            "port": {}\n\
        }}'.format(self.NODE_4_NAME,
                   self.NODE_4_MAC,
                   self.NODE_4_IPADDR,
                   self.NODE_4_PORT)
            number_of_nodes += 1
            
            
        output_text = output_text + '\n    ],\n\
    "farm_mode" : {{\n\
        "enable": 1,\n\
        "num_dests": {}\n\
    }}\n\
}}\n'.format(number_of_nodes)
        output_file.write(output_text)

    # __init__ arguments
    ArgInfo = ADBaseTemplate.ArgInfo + _SpecificTemplate.ArgInfo + makeArgInfo(__init__,
        PORT=Simple("Port name for the detector", str),
        SERVER=Simple("Server host name", str),
        ODIN_SERVER_PORT=Simple("Odin server port", int),
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
        NODE_4_PORT=Simple("Port of detector output node 4", int))


class OdinDataTemplate(AutoSubstitution):
    TemplateFile = "odinData.template"


class OdinData(Device):

    """Store configuration for an OdinData process"""
    INDEX = 1  # Unique index for each OdinData instance

    # Device attributes
    AutoInstantiate = True

    def __init__(self, IP, READY, RELEASE, META):
        self.__super.__init__()
        # Update attributes with parameters
        self.__dict__.update(locals())

        # Create unique R MACRO for template file - OD1, OD2 etc.
        self.R = ":OD{}:".format(self.INDEX)
        self.index = OdinData.INDEX
        OdinData.INDEX += 1

    def create_config_file(self, prefix, template, extra_macros=None):
        macros = dict(IP=self.IP, RD_PORT=self.READY, RL_PORT=self.RELEASE,
                      FW_ROOT=FILE_WRITER_ROOT, PP_ROOT=EXCALIBUR_ROOT)
        if extra_macros is not None:
            macros.update(extra_macros)
        with open(os.path.join(DATA, template)) as template_file:
            template_config = Template(template_file.read())

        output = template_config.substitute(macros)

        output_file = IocDataStream("{}{}.json".format(prefix, self.index))
        output_file.write(output)


class OdinDataServer(Device):

    """Store configuration for an OdinDataServer"""
    PORT_BASE = 5000

    # Device attributes
    AutoInstantiate = True

    def __init__(self, IP, PROCESSES):
        self.__super.__init__()
        # Update attributes with parameters
        self.__dict__.update(locals())

        self.processes = []
        for _ in range(PROCESSES):
            self.processes.append(
                OdinData(IP, self.PORT_BASE + 1, self.PORT_BASE + 2, self.PORT_BASE + 3)
            )
            self.PORT_BASE += 10

        self.instantiated = False  # Make sure instances are only used once

    ArgInfo = makeArgInfo(__init__,
                          IP=Simple("IP address of server hosting processes", str),
                          PROCESSES=Simple("Number of OdinData processes on this server", int))


class OdinDataDriverTemplate(AutoSubstitution):
    TemplateFile = "odinDataDriver.template"


class OdinDataDriver(AsynPort):

    """Create an OdinData driver"""
    Dependencies = (ADCore, restClient, FileWriterPlugin)

    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = "PORT"

    _SpecificTemplate = OdinDataDriverTemplate

    def __init__(self, PORT, SERVER, ODIN_SERVER_PORT, PROCESS_PLUGIN, RECEIVER_PLUGIN, FILE_WRITER, DATASET="data",
                 DETECTOR=None,
                 ODIN_DATA_SERVER_1=None, ODIN_DATA_SERVER_2=None, ODIN_DATA_SERVER_3=None,
                 ODIN_DATA_SERVER_4=None, ODIN_DATA_SERVER_5=None, ODIN_DATA_SERVER_6=None,
                 ODIN_DATA_SERVER_7=None, ODIN_DATA_SERVER_8=None,
                 BUFFERS = 0, MEMORY = 0, **args):
        # Init the superclass (AsynPort)
        self.__super.__init__(PORT)
        # Update the attributes of self from the commandline args
        self.__dict__.update(locals())
        # Make an instance of our template
        makeTemplateInstance(self._SpecificTemplate, locals(), args)

        self.FILE_WRITER_MACRO = FILE_WRITER.MACRO
        self.DETECTOR = PROCESS_PLUGIN.NAME
        self.PROCESS_PLUGIN_MACRO = PROCESS_PLUGIN.MACRO

        self.ODIN_DATA_PROCESSES = []
        for idx in range(1, 9):
            server = eval("ODIN_DATA_SERVER_{}".format(idx))
            if server is not None:
                if server.instantiated:
                    raise ValueError("Same OdinDataServer object given twice")
                else:
                    server.instantiated = True

                port_number=61649
                for odin_data in server.processes:
                    self.ODIN_DATA_PROCESSES.append(odin_data)
                    # Use some OdinDataDriver macros to instantiate an odinData.template
                    args["PORT"] = PORT
                    args["ADDR"] = odin_data.index - 1
                    args["R"] = odin_data.R
                    OdinDataTemplate(**args)

                    detector = eval("DETECTOR")
                    daq_templates = detector.daq_templates()
                    if daq_templates is not None:
                        port_number_1 = port_number
                        port_number_2 = port_number+1
                        port_number_3 = port_number+2
                        port_number_4 = port_number+3
                        port_number_5 = port_number+4
                        port_number_6 = port_number+5
                        port_number += 6
                        macros = dict(RX_PORT_1=port_number_1,
                                      RX_PORT_2=port_number_2,
                                      RX_PORT_3=port_number_3,
                                      RX_PORT_4=port_number_4,
                                      RX_PORT_5=port_number_5,
                                      RX_PORT_6=port_number_6)
                        odin_data.create_config_file('fp', daq_templates["ProcessPlugin"])
                        odin_data.create_config_file('fr', daq_templates["ReceiverPlugin"], extra_macros=macros)

    # __init__ arguments
    ArgInfo = ADBaseTemplate.ArgInfo + _SpecificTemplate.ArgInfo + makeArgInfo(__init__,
        PORT=Simple("Port name for the detector", str),
        SERVER=Simple("Server host name", str),
        ODIN_SERVER_PORT=Simple("Odin server port", int),
        DETECTOR=Ident("Detector configuration", OdinDetector),
        PROCESS_PLUGIN=Ident("Odin detector configuration", ExcaliburProcessPlugin),
        RECEIVER_PLUGIN=Ident("Odin detector configuration", ExcaliburReceiverPlugin),
        FILE_WRITER=Ident("FileWriterPlugin configuration", FileWriterPlugin),
        DATASET=Simple("Name of Dataset", str),
        ODIN_DATA_SERVER_1=Ident("OdinDataServer 1 configuration", OdinDataServer),
        ODIN_DATA_SERVER_2=Ident("OdinDataServer 2 configuration", OdinDataServer),
        ODIN_DATA_SERVER_3=Ident("OdinDataServer 3 configuration", OdinDataServer),
        ODIN_DATA_SERVER_4=Ident("OdinDataServer 4 configuration", OdinDataServer),
        ODIN_DATA_SERVER_5=Ident("OdinDataServer 5 configuration", OdinDataServer),
        ODIN_DATA_SERVER_6=Ident("OdinDataServer 6 configuration", OdinDataServer),
        ODIN_DATA_SERVER_7=Ident("OdinDataServer 7 configuration", OdinDataServer),
        ODIN_DATA_SERVER_8=Ident("OdinDataServer 8 configuration", OdinDataServer),
        BUFFERS=Simple("Maximum number of NDArray buffers to be created for plugin callbacks", int),
        MEMORY=Simple("Max memory to allocate, should be maxw*maxh*nbuffer for driver and all "
                      "attached plugins", int))

    # Device attributes
    LibFileList = ['odinDetector']
    DbdFileList = ['odinDetectorSupport']

    def Initialise(self):
        # Configure up to 8 OdinData processes
        print "# odinDataProcessConfig(const char * ipAddress, int readyPort, " \
              "int releasePort, int metaPort)"
        for process in self.ODIN_DATA_PROCESSES:
            print "odinDataProcessConfig(\"%(IP)s\", %(READY)d, " \
                  "%(RELEASE)d, %(META)d)" % process.__dict__

        print "# odinDataDriverConfig(const char * portName, const char * serverPort, " \
              "int odinServerPort, " \
              "const char * datasetName, const char * detectorName, " \
              "int maxBuffers, size_t maxMemory)"
        print "odinDataDriverConfig(\"%(PORT)s\", \"%(SERVER)s\", " \
              "%(ODIN_SERVER_PORT)d, " \
              "\"%(DATASET)s\", \"%(DETECTOR)s\", " \
              "%(BUFFERS)d, %(MEMORY)d)" % self.__dict__
