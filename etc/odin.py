import os
from string import Template

from iocbuilder import AutoSubstitution, Device
from iocbuilder.arginfo import makeArgInfo, Simple, Ident, Choice
from iocbuilder.iocinit import IocDataStream
from iocbuilder.modules.asyn import AsynPort
from iocbuilder.modules.ADCore import ADCore, ADBaseTemplate, makeTemplateInstance
from iocbuilder.modules.calc import Calc
from iocbuilder.modules.restClient import restClient


DATA = os.path.join(os.path.dirname(__file__), "../data")

__all__ = ["OdinDetector"]


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

    def create_config_file(self, prefix, template, index, extra_macros=None):
        macros = dict(IP=self.IP, RD_PORT=self.READY, RL_PORT=self.RELEASE,
                      FW_ROOT=FILE_WRITER_ROOT, PP_ROOT=EXCALIBUR_ROOT)
        if extra_macros is not None:
            macros.update(extra_macros)
        with open(os.path.join(DATA, template)) as template_file:
            template_config = Template(template_file.read())

        output = template_config.substitute(macros)

        output_file = IocDataStream("{}{}.json".format(prefix, index))
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
    Dependencies = (ADCore, Calc, restClient, FileWriterPlugin)

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

                port_number=61649
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
                        odin_data.create_config_file('fp', daq_templates["ProcessPlugin"], address+1)
                        odin_data.create_config_file('fr', daq_templates["ReceiverPlugin"], address+1, extra_macros=macros)
                    index_number += self.server_count

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

              
class FrameProcessor(Device):

    def __init__(self, IOC, LOG_CFG):
        self.__super.__init__()
        # Update attributes with parameters
        self.__dict__.update(locals())
        self.create_startup_file()

    def create_startup_file(self):
        macros = dict(LOG_CFG=self.LOG_CFG, FW_ROOT=FILE_WRITER_ROOT)
        template_config = Template('#!/bin/bash\n\
cd $FW_ROOT\n\
./bin/frameProcessor --logconfig $LOG_CFG\n')

        output = template_config.substitute(macros)

        output_file = IocDataStream("st{}.sh".format(self.IOC))
        output_file.write(output)

    # __init__ arguments
    ArgInfo = makeArgInfo(__init__,
        IOC=Simple("Name of the IOC", str),
        LOG_CFG=Simple("Full path to the Log configuration file", str))



