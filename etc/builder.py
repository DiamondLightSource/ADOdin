import os
import sys
from string import Template

from iocbuilder import AutoSubstitution, Device
from iocbuilder.arginfo import makeArgInfo, Simple, Ident, Choice
from iocbuilder.iocinit import IocDataStream
from iocbuilder.modules.asyn import AsynPort
from iocbuilder.modules.ADCore import ADCore, ADBaseTemplate, makeTemplateInstance
from iocbuilder.modules.restClient import restClient

###################################################################################################
# Import detector specific objects from other modules and expose them to builder ##################
###################################################################################################
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from excalibur import ExcaliburDetector, \
                      Excalibur2FemStatusTemplate, Excalibur6FemStatusTemplate, \
                      Excalibur2NodeFPTemplate, Excalibur4NodeFPTemplate, Excalibur8NodeFPTemplate
__all__ = ["ExcaliburDetector",
           "Excalibur2FemStatusTemplate", "Excalibur6FemStatusTemplate",
           "Excalibur2NodeFPTemplate", "Excalibur4NodeFPTemplate", "Excalibur8NodeFPTemplate"]

###################################################################################################

from odin import ProcessPlugin, OdinDataServer, ODIN_DATA_ROOT, ADODIN_DATA


class OdinDataTemplate(AutoSubstitution):
    TemplateFile = "odinData.template"


class FileWriterPlugin(ProcessPlugin):

    """Object to define generated config and boot script entries for FileWriterPlugin."""

    def create_config_file(self, **kwargs):
        pass


class FrameProcessor(Device):

    def __init__(self, IOC, LOG_CFG):
        self.__super.__init__()
        # Update attributes with parameters
        self.__dict__.update(locals())
        self.create_startup_file()

    def create_startup_file(self):
        macros = dict(LOG_CFG=self.LOG_CFG, FW_ROOT=ODIN_DATA_ROOT)
        template_config = Template('#!/bin/bash\n\
cd $FW_ROOT\n\
./bin/frameProcessor --logconfig $LOG_CFG\n')

        output = template_config.substitute(macros)

        output_file = IocDataStream("st{}.sh".format(self.IOC))
        output_file.write(output)

    # __init__ arguments
    ArgInfo = makeArgInfo(__init__,
                          IOC=Simple("Name of the IOC", str),
                          LOG_CFG=Simple("Full path to the Log configuration file", str)
                          )


class OdinDataDriverTemplate(AutoSubstitution):
    TemplateFile = "odinDataDriver.template"


class OdinDataDriver(AsynPort):

    """Create an OdinData driver"""

    Dependencies = (ADCore, restClient)

    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = "PORT"

    _SpecificTemplate = OdinDataDriverTemplate

    def __init__(self, PORT, SERVER, ODIN_SERVER_PORT, DETECTOR=None, DATASET="data",
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

        self.DETECTOR_PLUGIN = DETECTOR.lower()

        self.ODIN_DATA_PROCESSES = []

        # Count the number of servers
        self.server_count = 0
        for idx in range(1, 9):
            server = eval("ODIN_DATA_SERVER_{}".format(idx))
            if server is not None:
                self.server_count += 1
        print("Server count: {}".format(self.server_count))

        for idx in range(1, 9):
            server = eval("ODIN_DATA_SERVER_{}".format(idx))
            if server is not None:
                if server.instantiated:
                    raise ValueError("Same OdinDataServer object given twice")
                else:
                    server.instantiated = True

                index_number = 0
                for odin_data in server.processes:
                    address = idx + index_number - 1
                    print("Odin data idx: {}  index_number: {}  address: {}".format(idx, index_number, address))
                    self.ODIN_DATA_PROCESSES.append(odin_data)
                    # Use some OdinDataDriver macros to instantiate an odinData.template
                    args["PORT"] = PORT
                    args["ADDR"] = odin_data.index-1
                    args["R"] = odin_data.R
                    OdinDataTemplate(**args)

                    odin_data.create_config_files(address + 1)

                    index_number += self.server_count

    # __init__ arguments
    ArgInfo = ADBaseTemplate.ArgInfo + _SpecificTemplate.ArgInfo + makeArgInfo(__init__,
        PORT=Simple("Port name for the detector", str),
        SERVER=Simple("Server host name", str),
        ODIN_SERVER_PORT=Simple("Odin server port", int),
        DATASET=Simple("Name of Dataset", str),
        DETECTOR=Choice("Detector type", ["Excalibur", "Eiger"]),
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
              "\"%(DATASET)s\", \"%(DETECTOR_PLUGIN)s\", " \
              "%(BUFFERS)d, %(MEMORY)d)" % self.__dict__
