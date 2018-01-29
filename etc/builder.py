from iocbuilder import AutoSubstitution, Device
from iocbuilder.arginfo import makeArgInfo, Simple, Ident
from iocbuilder.modules.asyn import AsynPort
from iocbuilder.modules.ADCore import ADCore, ADBaseTemplate, makeTemplateInstance
from iocbuilder.modules.restClient import restClient
from iocbuilder.modules.OdinData import OdinData


__all__ = ['odinDetector', 'ExcaliburDetector']


class excaliburDetectorTemplate(AutoSubstitution):
    TemplateFile = "excaliburDetector.template"


class ExcaliburDetector(Device):

    """Store configuration for Excalibur Detector."""

    NAME = "excalibur"

    # Device attributes
    AutoInstantiate = True

    def __init__(self, MACRO):
        self.__super.__init__()
        # Update attributes with parameters
        self.__dict__.update(locals())

    ArgInfo = makeArgInfo(__init__,
                          MACRO=Simple('Dependency MACRO as in configure/RELEASE', str))


class odinDetectorTemplate(AutoSubstitution):
    TemplateFile = "odin.template"


class odinDetector(AsynPort):

    """Create an odin detector"""

    Dependencies = (ADCore, restClient, OdinData, ExcaliburDetector)

    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = "PORT"

    _SpecificTemplate = odinDetectorTemplate

    def __init__(self, PORT, SERVER, DETECTOR, ODIN_DATA, BUFFERS = 0, MEMORY = 0, **args):
        # Init the superclass (AsynPort)
        self.__super.__init__(PORT)
        # Update the attributes of self from the commandline args
        self.__dict__.update(locals())
        # Make an instance of our template
        makeTemplateInstance(self._SpecificTemplate, locals(), args)

        self.DETECTOR_NAME = DETECTOR.NAME
        self.DETECTOR_MACRO = DETECTOR.MACRO
        self.ODIN_DATA_MACRO = ODIN_DATA.MACRO
        self.ODIN_DATA_IP = ODIN_DATA.IP
        self.ODIN_DATA_READY = ODIN_DATA.READY
        self.ODIN_DATA_RELEASE = ODIN_DATA.RELEASE
        self.ODIN_DATA_META = ODIN_DATA.META

    # __init__ arguments
    ArgInfo = ADBaseTemplate.ArgInfo + _SpecificTemplate.ArgInfo + makeArgInfo(__init__,
        PORT=Simple('Port name for the detector', str),
        SERVER=Simple('Server host name', str),
        DETECTOR=Ident('Odin detector configuration', ExcaliburDetector),
        ODIN_DATA=Ident('OdinData configuration', OdinData),
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
        print 'odinDataConfig("$(%(ODIN_DATA_MACRO)s)", %(ODIN_DATA_IP)s, ' \
              '%(ODIN_DATA_READY)s, %(ODIN_DATA_RELEASE)s, %(ODIN_DATA_META)s)' % self.__dict__
        print '# odinDataDetectorConfig(const char * detectorName, const char * libraryPath)'
        print 'odinDataDetectorConfig("%(DETECTOR_NAME)s", "$(%(DETECTOR_MACRO)s)")' % self.__dict__
        print "# odinDetectorConfig(const char *portName, const char *serverPort, " \
              "int maxBuffers, size_t maxMemory, int priority, int stackSize)"
        print 'odinDetectorConfig("%(PORT)s", %(SERVER)s, %(DETECTOR_NAME)s, %(BUFFERS)s, %(MEMORY)d)' % self.__dict__

