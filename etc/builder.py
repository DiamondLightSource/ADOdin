from iocbuilder import AutoSubstitution, Device
from iocbuilder.arginfo import makeArgInfo, Simple
from iocbuilder.modules.asyn import AsynPort
from iocbuilder.modules.ADCore import ADCore, ADBaseTemplate, makeTemplateInstance
from iocbuilder.modules.restClient import restClient
from iocbuilder.modules.OdinData import OdinData
from iocbuilder.modules.ExcaliburDetector import ExcaliburDetector


__all__ = ['odinDetector']


class odinDetectorTemplate(AutoSubstitution):
    TemplateFile = "odin.template"


class odinDetector(AsynPort):

    """Create an odin detector"""

    Dependencies = (ADCore, restClient, OdinData, ExcaliburDetector)

    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = "PORT"

    _SpecificTemplate = odinDetectorTemplate

    def __init__(self, PORT, SERVER, DETECTOR, BUFFERS = 0, MEMORY = 0, **args):
        # Init the superclass (AsynPort)
        self.__super.__init__(PORT)
        # Update the attributes of self from the commandline args
        self.__dict__.update(locals())
        # Make an instance of our template
        makeTemplateInstance(self._SpecificTemplate, locals(), args)

        self.DETECTOR_MACRO = self.DETECTOR.upper()

    # __init__ arguments
    ArgInfo = ADBaseTemplate.ArgInfo + _SpecificTemplate.ArgInfo + makeArgInfo(__init__,
        PORT=Simple('Port name for the detector', str),
        SERVER=Simple('Server host name', str),
        DETECTOR=Simple('Name of Odin detector', str),
        BUFFERS=Simple('Maximum number of NDArray buffers to be created for plugin callbacks', int),
        MEMORY=Simple('Max memory to allocate, should be maxw*maxh*nbuffer for driver and all attached plugins', int))

    # Device attributes
    LibFileList = ['odinDetector', 'frozen']
    DbdFileList = ['odinDetectorSupport']

    def Initialise(self):
        print '# odinDataConfig(const char * libraryPath)'
        print 'odinDataConfig("$(ODINDATA)")'  # Put the actual macro in the src boot script to be substituted by `make`
        print '# odinDataConfig(const char * detectorName, const char * libraryPath)'
        print 'odinDataDetectorConfig("%(DETECTOR)s", "$(%(DETECTOR_MACRO)sDETECTOR)")' % self.__dict__  # Put the actual macro in the src boot script to be substituted by `make`
        print "# odinDetectorConfig(const char *portName, const char *serverPort, int maxBuffers, size_t maxMemory, int priority, int stackSize)"
        print 'odinDetectorConfig("%(PORT)s", %(SERVER)s, %(BUFFERS)s, %(MEMORY)d)' % self.__dict__
