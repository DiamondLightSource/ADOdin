from iocbuilder import AutoSubstitution, Device
from iocbuilder.arginfo import makeArgInfo, Simple, Ident, Choice

class ExcaliburProcessPlugin(Device):

    """Store configuration for ExcaliburProcessPlugin."""

    NAME = "excalibur"

    # Device attributes
    AutoInstantiate = True

    def __init__(self, MACRO):
        self.__super.__init__()
        # Update attributes with parameters
        self.__dict__.update(locals())

    ArgInfo = makeArgInfo(__init__,
                          MACRO=Simple('Dependency MACRO as in configure/RELEASE', str))


class ExcaliburReceiverPlugin(Device):

    """Store configuration for ExcaliburReceiverPlugin."""

    NAME = "excalibur"

    # Device attributes
    AutoInstantiate = True

    def __init__(self, MACRO):
        self.__super.__init__()
        # Update attributes with parameters
        self.__dict__.update(locals())

    ArgInfo = makeArgInfo(__init__,
                          MACRO=Simple('Dependency MACRO as in configure/RELEASE', str))



