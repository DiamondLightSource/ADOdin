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


class OdinDetectorTemplate(AutoSubstitution):
    TemplateFile = "odinDetector.template"


class OdinDataTemplate(AutoSubstitution):
    TemplateFile = "odinData.template"


class OdinData(Device):

    """Store configuration for OdinData."""
    INDEX = 1  # Unique index for each OdinData instance

    # Device attributes
    AutoInstantiate = True

    def __init__(self, IP, READY, RELEASE, META, FILE_WRITER, DETECTOR=None):
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
                          META=Simple("Port for Meta Channel", int),
                          FILE_WRITER=Ident("FileWriterPlugin configuration", FileWriterPlugin),
                          DETECTOR=Ident("Odin detector configuration", ExcaliburProcessPlugin))


class OdinDetector(AsynPort):

    """Create an odin detector"""

    Dependencies = (ADCore, restClient, FileWriterPlugin, ExcaliburProcessPlugin)

    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = "PORT"

    _SpecificTemplate = OdinDetectorTemplate

    def __init__(self, PORT, SERVER, ODIN_SERVER_PORT, DATASET="data",
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
                    OdinDataMeta(odin_data.IP, odin_data.READY, odin_data.RELEASE, odin_data.META,
                                 odin_data.FILE_WRITER, DATASET, odin_data.DETECTOR)
                )
                # Use some OdinDetector macros to instantiate an odinData.template
                args["PORT"] = PORT
                args["R"] = odin_data.R
                OdinDataTemplate(**args)

        self.DETECTOR_NAME = OdinDataMeta.DETECTOR_NAME

    # __init__ arguments
    ArgInfo = ADBaseTemplate.ArgInfo + _SpecificTemplate.ArgInfo + makeArgInfo(__init__,
        PORT=Simple("Port name for the detector", str),
        SERVER=Simple("Server host name", str),
        ODIN_SERVER_PORT=Simple("Odin server port", int),
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
        print "# odinDataConfig(const char * odinDataLibraryPath, " \
              "const char * detectorName, const char * detectorLibraryPath, " \
              "const char * datasetName)"
        print "odinDataConfig(\"$(%(ODIN_DATA_MACRO)s)\", " \
              "\"%(DETECTOR_NAME)s\", \"$(%(DETECTOR_MACRO)s)\", " \
              "\"%(DATASET)s\")" % OdinDataMeta.__dict__
        # Configure up to 8 OdinData processes
        print "# odinDataProcessConfig(const char * ipAddress, int readyPort, " \
              "int releasePort, int metaPort)"
        for process in self.ODIN_DATA_PROCESSES:
            print "odinDataProcessConfig(\"%(IP)s\", %(READY)d, " \
                  "%(RELEASE)d, %(META)d)" % process.__dict__
        print "# odinDetectorConfig(const char * portName, const char * serverPort, " \
              "int odinServerPort, const char * detectorName, " \
              "int maxBuffers, size_t maxMemory, int priority, int stackSize)"
        print "odinDetectorConfig(\"%(PORT)s\", \"%(SERVER)s\", " \
              "%(ODIN_SERVER_PORT)d, \"%(DETECTOR_NAME)s\", " \
              "%(BUFFERS)d, %(MEMORY)d)" % self.__dict__


class OdinDataMeta(object):

    ODIN_DATA_MACRO = ""
    DETECTOR_NAME = ""
    DETECTOR_MACRO = ""
    DATASET = ""

    def __init__(self, ip, ready, release, meta, fw_plugin, dataset, process_plugin):
        self.IP = ip
        self.READY = ready
        self.RELEASE = release
        self.META = meta

        if not any([OdinDataMeta.ODIN_DATA_MACRO, OdinDataMeta.DATASET,
                    OdinDataMeta.DETECTOR_NAME, OdinDataMeta.DETECTOR_MACRO]):
            OdinDataMeta.ODIN_DATA_MACRO = fw_plugin.MACRO
            OdinDataMeta.DATASET = dataset
            OdinDataMeta.DETECTOR_NAME = process_plugin.NAME
            OdinDataMeta.DETECTOR_MACRO = process_plugin.MACRO
