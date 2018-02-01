from iocbuilder import AutoSubstitution, Device
from iocbuilder.arginfo import makeArgInfo, Simple, Ident
from iocbuilder.modules.asyn import AsynPort
from iocbuilder.modules.ADCore import ADCore, ADBaseTemplate, makeTemplateInstance
from iocbuilder.modules.restClient import restClient
from iocbuilder.modules.OdinData import OdinData
from iocbuilder.modules.ExcaliburDetector import ExcaliburProcessPlugin


__all__ = ['odinDetector']


class excaliburDetectorTemplate(AutoSubstitution):
    TemplateFile = "excaliburDetector.template"


class odinDetectorTemplate(AutoSubstitution):
    TemplateFile = "odin.template"


class odinDetector(AsynPort):

    """Create an odin detector"""

    Dependencies = (ADCore, restClient, OdinData, ExcaliburProcessPlugin)

    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = "PORT"

    _SpecificTemplate = odinDetectorTemplate

    def __init__(self, PORT, SERVER, ODIN_SERVER_PORT, DETECTOR,
                 ODIN_DATA_1=None, ODIN_DATA_2=None, ODIN_DATA_3=None, ODIN_DATA_4=None,
                 ODIN_DATA_5=None, ODIN_DATA_6=None, ODIN_DATA_7=None, ODIN_DATA_8=None,
                 BUFFERS = 0, MEMORY = 0, **args):
        # Init the superclass (AsynPort)
        self.__super.__init__(PORT)
        # Update the attributes of self from the commandline args
        self.__dict__.update(locals())
        # Make an instance of our template
        makeTemplateInstance(self._SpecificTemplate, locals(), args)

        self.DETECTOR_NAME = DETECTOR.NAME
        self.DETECTOR_MACRO = DETECTOR.MACRO

        self.ODIN_DATA_PROCESSES = []
        for idx in range(1, 9):
            param = eval("ODIN_DATA_{}".format(idx))
            if param is not None:
                self.ODIN_DATA_PROCESSES.append(
                    OdinDataMeta(param.MACRO, param.IP, param.READY, param.RELEASE, param.META)
                )

    # __init__ arguments
    ArgInfo = ADBaseTemplate.ArgInfo + _SpecificTemplate.ArgInfo + makeArgInfo(__init__,
        PORT=Simple('Port name for the detector', str),
        SERVER=Simple('Server host name', str),
        DETECTOR=Ident('Odin detector configuration', ExcaliburProcessPlugin),
        ODIN_SERVER_PORT=Simple('Odin server port', int),
        ODIN_DATA_1=Ident('OdinData process 1 configuration', OdinData),
        ODIN_DATA_2=Ident('OdinData process 2 configuration', OdinData),
        ODIN_DATA_3=Ident('OdinData process 3 configuration', OdinData),
        ODIN_DATA_4=Ident('OdinData process 4 configuration', OdinData),
        ODIN_DATA_5=Ident('OdinData process 5 configuration', OdinData),
        ODIN_DATA_6=Ident('OdinData process 6 configuration', OdinData),
        ODIN_DATA_7=Ident('OdinData process 7 configuration', OdinData),
        ODIN_DATA_8=Ident('OdinData process 8 configuration', OdinData),
        BUFFERS=Simple('Maximum number of NDArray buffers to be created for plugin callbacks', int),
        MEMORY=Simple('Max memory to allocate, should be maxw*maxh*nbuffer for driver and all '
                      'attached plugins', int))

    # Device attributes
    LibFileList = ['odinDetector']
    DbdFileList = ['odinDetectorSupport']

    def Initialise(self):
        # Put the actual macros in the src boot script to be substituted by `make`
        print '# odinDataConfig(const char * libraryPath, int ipAddress, int ctrlPort, ' \
              'int readyPort, int releasePort, int metaPort)'
        # Configure up to 8 OdinData processes
        for process in self.ODIN_DATA_PROCESSES:
            print 'odinDataConfig("$(%(MACRO)s)", %(ip)s, ' \
                  '%(ready)s, %(release)s, %(meta)s)' % process.__dict__
        print '# odinDataDetectorConfig(const char * detectorName, const char * libraryPath)'
        print 'odinDataDetectorConfig("%(DETECTOR_NAME)s", "$(%(DETECTOR_MACRO)s)")' % self.__dict__
        print "# odinDetectorConfig(const char * portName, const char * serverPort, " \
              "int odinServerPort, const char * detectorName, " \
              "int maxBuffers, size_t maxMemory, int priority, int stackSize)"
        print 'odinDetectorConfig("%(PORT)s", %(SERVER)s, %(ODIN_SERVER_PORT)s, ' \
              '%(DETECTOR_NAME)s, %(BUFFERS)s, %(MEMORY)d)' % self.__dict__


class OdinDataMeta(object):

    MACRO = ""

    def __init__(self, macro, ip, ready, release, meta):
        if self.MACRO == "":
            self.MACRO = macro
        self.ip = ip
        self.ready = ready
        self.release = release
        self.meta = meta
