from iocbuilder import AutoSubstitution, Device
from iocbuilder.arginfo import makeArgInfo, Simple, Ident, Choice
from iocbuilder.iocinit import IocDataStream
from iocbuilder.modules.asyn import AsynPort
from iocbuilder.modules.ADCore import ADCore, ADBaseTemplate, makeTemplateInstance
from iocbuilder.modules.restClient import restClient
from iocbuilder.modules.OdinData import FileWriterPlugin
from iocbuilder.modules.ExcaliburDetector import ExcaliburProcessPlugin

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


class ExcaliburDetectorTemplate(AutoSubstitution):
    TemplateFile = "excaliburDetector.template"


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

    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = "PORT"

    _SpecificTemplate = ExcaliburDetectorTemplate

    def __init__(self, PORT, SERVER, ODIN_SERVER_PORT, SENSOR, BUFFERS = 0, MEMORY = 0, **args):
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
            "R": args["R"] + "F:",
            "PORT": PORT,
            "TIMEOUT": args["TIMEOUT"]
        }
        fem_hk_template(**fem_hk_args)
        
        assert SENSOR in self.SENSOR_OPTIONS.keys()
        # Instantiate template corresponding to SENSOR, passing through some of own args
        status_template = self.SENSOR_OPTIONS[SENSOR][0]
        status_args = {
            "P": args["P"],
            "R": args["R"] + "F",
            "ADDRESS": "0",
            "PORT": PORT,
            "TIMEOUT": args["TIMEOUT"],
            "TOTAL": self.SENSOR_OPTIONS[SENSOR][1]
        }
        status_template(**status_args)

    # __init__ arguments
    ArgInfo = ADBaseTemplate.ArgInfo + _SpecificTemplate.ArgInfo + makeArgInfo(__init__,
        PORT=Simple("Port name for the detector", str),
        SERVER=Simple("Server host name", str),
        ODIN_SERVER_PORT=Simple("Odin server port", int),
        SENSOR=Choice("Sensor type", ["1M", "3M"]),
        BUFFERS=Simple("Maximum number of NDArray buffers to be created for plugin callbacks", int),
        MEMORY=Simple("Max memory to allocate, should be maxw*maxh*nbuffer for driver and all "
                      "attached plugins", int))


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

    def create_config_file(self, template):
        macros = dict(IP=self.IP, RD_PORT=self.READY, RL_PORT=self.RELEASE,
                      FW_ROOT=FILE_WRITER_ROOT, PP_ROOT=EXCALIBUR_ROOT)
        with open(os.path.join(DATA, template)) as template_file:
            template_config = Template(template_file.read())

        output = template_config.substitute(macros)

        output_file = IocDataStream("fp{}.json".format(self.index))
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

    CONFIG_TEMPLATES = {
        ExcaliburProcessPlugin: "fp_excalibur.json"
    }

    Dependencies = (ADCore, restClient, FileWriterPlugin)

    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = "PORT"

    _SpecificTemplate = OdinDataDriverTemplate

    def __init__(self, PORT, SERVER, ODIN_SERVER_PORT, PROCESS_PLUGIN, FILE_WRITER, DATASET="data",
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

                for odin_data in server.processes:
                    self.ODIN_DATA_PROCESSES.append(odin_data)
                    # Use some OdinDataDriver macros to instantiate an odinData.template
                    args["PORT"] = PORT
                    args["ADDR"] = odin_data.index - 1
                    args["R"] = odin_data.R
                    OdinDataTemplate(**args)

                    odin_data.create_config_file(self.CONFIG_TEMPLATES[PROCESS_PLUGIN.__class__])

    # __init__ arguments
    ArgInfo = ADBaseTemplate.ArgInfo + _SpecificTemplate.ArgInfo + makeArgInfo(__init__,
        PORT=Simple("Port name for the detector", str),
        SERVER=Simple("Server host name", str),
        ODIN_SERVER_PORT=Simple("Odin server port", int),
        PROCESS_PLUGIN=Ident("Odin detector configuration", ExcaliburProcessPlugin),
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
