import os
import sys

from iocbuilder import AutoSubstitution, Device
from iocbuilder.arginfo import makeArgInfo, Simple, Ident, Choice
from iocbuilder.modules.asyn import AsynPort
from iocbuilder.modules.ADCore import ADCore, ADBaseTemplate, makeTemplateInstance
from iocbuilder.modules.restClient import restClient

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from odin import _OdinDataServer, _OdinControlServer, _OdinDataTemplate

###################################################################################################
# Import detector specific objects from other modules to expose them to builder
###################################################################################################

from excalibur import ExcaliburDetector, ExcaliburOdinDataServer, ExcaliburOdinControlServer, \
                      _Excalibur2FemStatusTemplate, _Excalibur6FemStatusTemplate, \
                      Excalibur2NodeFPTemplate, Excalibur4NodeFPTemplate, Excalibur8NodeFPTemplate

from eiger import EigerOdinDataServer, EigerOdinControlServer, EigerFan, EigerMetaListener

###################################################################################################


class _OdinDataDriverTemplate(AutoSubstitution):
    TemplateFile = "odinDataDriver.template"


class OdinDataDriver(AsynPort):

    """Create an OdinData driver"""

    Dependencies = (ADCore, restClient)

    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = "PORT"

    _SpecificTemplate = _OdinDataDriverTemplate

    def __init__(self, PORT, ODIN_CONTROL_SERVER, DETECTOR=None, DATASET="data",
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

        self.CONTROL_SERVER_IP = ODIN_CONTROL_SERVER.IP
        self.CONTROL_SERVER_PORT = ODIN_CONTROL_SERVER.PORT
        self.DETECTOR_PLUGIN = DETECTOR.lower()
        self.ODIN_DATA_PROCESSES = []

        # Count the number of servers
        server_count = 0
        for idx in range(1, 9):
            server = eval("ODIN_DATA_SERVER_{}".format(idx))
            if server is not None:
                server_count += 1
        print("Server count: {}".format(server_count))

        server_number = 0
        for idx in range(1, 9):
            server = eval("ODIN_DATA_SERVER_{}".format(idx))
            if server is not None:
                if server.instantiated:
                    raise ValueError("Same OdinDataServer object given twice")
                else:
                    server_number += 1
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
                    _OdinDataTemplate(**args)

                    odin_data.create_config_files(address + 1)

                    index_number += server_count

                server.create_od_startup_scripts(server_number, server_count)

    # __init__ arguments
    ArgInfo = ADBaseTemplate.ArgInfo + _SpecificTemplate.ArgInfo + makeArgInfo(__init__,
        PORT=Simple("Port name for the detector", str),
        ODIN_CONTROL_SERVER=Ident("Odin control server", _OdinControlServer),
        DATASET=Simple("Name of Dataset", str),
        DETECTOR=Choice("Detector type", ["Excalibur", "Eiger"]),
        ODIN_DATA_SERVER_1=Ident("OdinDataServer 1 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_2=Ident("OdinDataServer 2 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_3=Ident("OdinDataServer 3 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_4=Ident("OdinDataServer 4 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_5=Ident("OdinDataServer 5 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_6=Ident("OdinDataServer 6 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_7=Ident("OdinDataServer 7 configuration", _OdinDataServer),
        ODIN_DATA_SERVER_8=Ident("OdinDataServer 8 configuration", _OdinDataServer),
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
        print "odinDataDriverConfig(\"%(PORT)s\", \"%(CONTROL_SERVER_IP)s\", " \
              "%(CONTROL_SERVER_PORT)d, " \
              "\"%(DATASET)s\", \"%(DETECTOR_PLUGIN)s\", " \
              "%(BUFFERS)d, %(MEMORY)d)" % self.__dict__
