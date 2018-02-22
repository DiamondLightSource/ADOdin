from iocbuilder import AutoSubstitution, Device
from iocbuilder.arginfo import makeArgInfo, Simple, Ident
from iocbuilder.modules.asyn import AsynPort
from iocbuilder.modules.ADCore import ADCore, ADBaseTemplate, makeTemplateInstance
from iocbuilder.modules.restClient import restClient
from iocbuilder.modules.OdinData import FileWriterPlugin
from iocbuilder.modules.ExcaliburDetector import ExcaliburProcessPlugin


__all__ = ["OdinDetector", "OdinData"]


class excaliburDetectorTemplate(AutoSubstitution):
    TemplateFile = "excaliburDetector.template"

class excaliburFemStatusTemplate(AutoSubstitution):
    WarnMacros = False
    TemplateFile = "excaliburFemStatus.template"

def add_excalibur_fem_status(cls):
    """Convenience function to add excaliburFemStatusTemplate attributes to a class that
    includes it via an msi include statement rather than verbatim"""
    cls.Arguments = excaliburFemStatusTemplate.Arguments + [x for x in cls.Arguments if x not in excaliburFemStatusTemplate.Arguments]
    cls.ArgInfo = excaliburFemStatusTemplate.ArgInfo + cls.ArgInfo.filtered(without=excaliburFemStatusTemplate.ArgInfo.Names())
    cls.Defaults.update(excaliburFemStatusTemplate.Defaults)
    return cls

@add_excalibur_fem_status
class excalibur2FemStatusTemplate(AutoSubstitution):
    TemplateFile = "excalibur2FemStatus.template"

class OdinDetectorTemplate(AutoSubstitution):
    TemplateFile = "odinDetector.template"


class OdinDetector(AsynPort):

    """Create an odin detector"""

    Dependencies = (ADCore, restClient)

    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = "PORT"

    _SpecificTemplate = OdinDetectorTemplate  # TODO: Remove and force subclassing

    def __init__(self, PORT, SERVER, ODIN_SERVER_PORT, DETECTOR, BUFFERS = 0, MEMORY = 0, **args):
        # Init the superclass (AsynPort)
        self.__super.__init__(PORT)
        # Update the attributes of self from the commandline args
        self.__dict__.update(locals())
        # Make an instance of our template
        makeTemplateInstance(self._SpecificTemplate, locals(), args)

    # __init__ arguments
    ArgInfo = ADBaseTemplate.ArgInfo + _SpecificTemplate.ArgInfo + makeArgInfo(__init__,
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


class OdinDataTemplate(AutoSubstitution):
    TemplateFile = "odinData.template"


class OdinData(Device):

    """Store configuration for OdinData."""
    INDEX = 1  # Unique index for each OdinData instance

    # Device attributes
    AutoInstantiate = True

    def __init__(self, IP, READY, RELEASE, META):
        self.__super.__init__()
        # Update attributes with parameters
        self.__dict__.update(locals())

        # Create unique R MACRO for template file - OD1, OD2 etc.
        self.R = ":OD{}:".format(self.INDEX)
        OdinData.INDEX += 1

        self.instantiated = False  # Make sure instances are only used once

    ArgInfo = makeArgInfo(__init__,
                          IP=Simple("IP address of server hosting processes", str),
                          READY=Simple("Port for Ready Channel", int),
                          RELEASE=Simple("Port for Release Channel", int),
                          META=Simple("Port for Meta Channel", int))


class OdinDataDriverTemplate(AutoSubstitution):
    TemplateFile = "odinDataDriver.template"


class OdinDataDriver(AsynPort):

    """Create an OdinData driver"""

    Dependencies = (ADCore, restClient, FileWriterPlugin, ExcaliburProcessPlugin)

    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = "PORT"

    _SpecificTemplate = OdinDataDriverTemplate

    def __init__(self, PORT, SERVER, ODIN_SERVER_PORT, PROCESS_PLUGIN, FILE_WRITER, DATASET="data",
                 ODIN_DATA_1=None, ODIN_DATA_2=None, ODIN_DATA_3=None, ODIN_DATA_4=None,
                 ODIN_DATA_5=None, ODIN_DATA_6=None, ODIN_DATA_7=None, ODIN_DATA_8=None,
                 BUFFERS = 0, MEMORY = 0, **args):
        # Init the superclass (AsynPort)
        self.__super.__init__(PORT)
        # Update the attributes of self from the commandline args
        self.__dict__.update(locals())
        # Make an instance of our template
        makeTemplateInstance(self._SpecificTemplate, locals(), args)

        self.ODIN_DATA_PROCESSES = []
        for idx in range(1, 9):
            odin_data = eval("ODIN_DATA_{}".format(idx))
            if odin_data is not None:
                if odin_data.instantiated:
                    raise ValueError("Same OdinData object given twice")
                else:
                    odin_data.instantiated = True
                self.ODIN_DATA_PROCESSES.append(
                    OdinDataMeta(odin_data.IP, odin_data.READY, odin_data.RELEASE, odin_data.META)
                )
                # Use some OdinDataDriver macros to instantiate an odinData.template
                args["PORT"] = PORT
                args["R"] = odin_data.R
                OdinDataTemplate(**args)

        self.FILE_WRITER_MACRO = FILE_WRITER.MACRO
        self.DETECTOR = PROCESS_PLUGIN.NAME
        self.PROCESS_PLUGIN_MACRO = PROCESS_PLUGIN.MACRO

    # __init__ arguments
    ArgInfo = ADBaseTemplate.ArgInfo + _SpecificTemplate.ArgInfo + makeArgInfo(__init__,
        PORT=Simple("Port name for the detector", str),
        SERVER=Simple("Server host name", str),
        ODIN_SERVER_PORT=Simple("Odin server port", int),
        PROCESS_PLUGIN=Ident("Odin detector configuration", ExcaliburProcessPlugin),
        FILE_WRITER=Ident("FileWriterPlugin configuration", FileWriterPlugin),
        DATASET=Simple("Name of Dataset", str),
        ODIN_DATA_1=Ident("OdinData process 1 configuration", OdinData),
        ODIN_DATA_2=Ident("OdinData process 2 configuration", OdinData),
        ODIN_DATA_3=Ident("OdinData process 3 configuration", OdinData),
        ODIN_DATA_4=Ident("OdinData process 4 configuration", OdinData),
        ODIN_DATA_5=Ident("OdinData process 5 configuration", OdinData),
        ODIN_DATA_6=Ident("OdinData process 6 configuration", OdinData),
        ODIN_DATA_7=Ident("OdinData process 7 configuration", OdinData),
        ODIN_DATA_8=Ident("OdinData process 8 configuration", OdinData),
        BUFFERS=Simple("Maximum number of NDArray buffers to be created for plugin callbacks", int),
        MEMORY=Simple("Max memory to allocate, should be maxw*maxh*nbuffer for driver and all "
                      "attached plugins", int))

    # Device attributes
    LibFileList = ['odinDetector']
    DbdFileList = ['odinDetectorSupport']

    def Initialise(self):
        # Put the actual macros in the src boot script to be substituted by `make`
        # Configure up to 8 OdinData processes
        print "# odinDataProcessConfig(const char * ipAddress, int readyPort, " \
              "int releasePort, int metaPort)"
        for process in self.ODIN_DATA_PROCESSES:
            print "odinDataProcessConfig(\"%(IP)s\", %(READY)d, " \
                  "%(RELEASE)d, %(META)d)" % process.__dict__

        print "# odinDataDriverConfig(const char * portName, const char * serverPort," \
              "int odinServerPort, " \
              "const char * datasetName, const char * fileWriterLibraryPath, " \
              "const char * detectorName, const char * processPluginLibraryPath, " \
              "int maxBuffers, size_t maxMemory)"
        print "odinDataDriverConfig(\"%(PORT)s\", \"%(SERVER)s\", " \
              "%(ODIN_SERVER_PORT)d, " \
              "\"%(DATASET)s\", \"$(%(FILE_WRITER_MACRO)s)\", " \
              "\"%(DETECTOR)s\", \"$(%(PROCESS_PLUGIN_MACRO)s)\", " \
              "%(BUFFERS)d, %(MEMORY)d)" % self.__dict__


class OdinDataMeta(object):

    def __init__(self, ip, ready, release, meta):
        self.IP = ip
        self.READY = ready
        self.RELEASE = release
        self.META = meta
