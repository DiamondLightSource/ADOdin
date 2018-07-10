import os

from iocbuilder import AutoSubstitution, Device
from iocbuilder.arginfo import makeArgInfo, Simple, Ident, Choice
from iocbuilder.iocinit import IocDataStream
from iocbuilder.modules.ADCore import ADCore, ADBaseTemplate, makeTemplateInstance

from odin import OdinDetector, ProcessPlugin, find_module_path, ADODIN_ROOT, FILE_WRITER_ROOT

__all__ = ["ExcaliburDetector", "ExcaliburProcessPlugin", "ExcaliburReceiverPlugin",
           "Excalibur2FemStatusTemplate", "Excalibur6FemStatusTemplate",
           "Excalibur2NodeFPTemplate", "Excalibur4NodeFPTemplate", "Excalibur8NodeFPTemplate"]


EXCALIBUR_ROOT = find_module_path("excalibur-detector")
print("Excalibur root: {}".format(EXCALIBUR_ROOT))


class ExcaliburProcessPlugin(ProcessPlugin):

    """Store configuration for ExcaliburProcessPlugin."""


class ExcaliburReceiverPlugin(ProcessPlugin):

    """Store configuration for ExcaliburReceiverPlugin."""

    # Device attributes
    AutoInstantiate = True

    def __init__(self, MACRO):
        self.__super.__init__()
        # Update attributes with parameters
        self.__dict__.update(locals())

    ArgInfo = makeArgInfo(__init__,
                          MACRO=Simple('Dependency MACRO as in configure/RELEASE', str))


class ExcaliburDetectorTemplate(AutoSubstitution):
    TemplateFile = "excaliburDetector.template"


class ExcaliburFPTemplate(AutoSubstitution):
    TemplateFile = "excaliburFP.template"


def add_excalibur_fp_template(cls):
    """Convenience function to add excaliburFPTemplate attributes to a class that
    includes it via an msi include statement rather than verbatim"""
    cls.Arguments = ExcaliburFPTemplate.Arguments + \
        [x for x in cls.Arguments if x not in ExcaliburFPTemplate.Arguments]
    cls.ArgInfo = ExcaliburFPTemplate.ArgInfo + cls.ArgInfo.filtered(
        without=ExcaliburFPTemplate.ArgInfo.Names())
    cls.Defaults.update(ExcaliburFPTemplate.Defaults)
    return cls


@add_excalibur_fp_template
class Excalibur2NodeFPTemplate(AutoSubstitution):
    TemplateFile = "excalibur2NodeFP.template"


@add_excalibur_fp_template
class Excalibur4NodeFPTemplate(AutoSubstitution):
    TemplateFile = "excalibur4NodeFP.template"


@add_excalibur_fp_template
class Excalibur8NodeFPTemplate(AutoSubstitution):
    TemplateFile = "excalibur8NodeFP.template"


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

    CONFIG_TEMPLATES = {
        "1M": {
                "ProcessPlugin": "fp_excalibur_1m.json",
                "ReceiverPlugin": "fr_excalibur_1m.json"
              },
        "3M": {
                "ProcessPlugin": "fp_excalibur_3m.json",
                "ReceiverPlugin": "fr_excalibur_3m.json"
              }
    }

    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = "PORT"

    _SpecificTemplate = ExcaliburDetectorTemplate

    def __init__(self, PORT, SERVER, ODIN_SERVER_PORT, SENSOR, BUFFERS = 0, MEMORY = 0, FEMS_REVERSED = 0, PWR_CARD_IDX = 1, SHARED_MEM_SIZE = 1048576000, NODE_1_NAME = None, NODE_1_CTRL_IP = None, NODE_1_MAC = None, NODE_1_IPADDR = None, NODE_1_PORT = None, NODE_2_NAME = None, NODE_2_CTRL_IP = None, NODE_2_MAC = None, NODE_2_IPADDR = None, NODE_2_PORT = None, NODE_3_NAME = None, NODE_3_CTRL_IP = None, NODE_3_MAC = None, NODE_3_IPADDR = None, NODE_3_PORT = None, NODE_4_NAME = None, NODE_4_CTRL_IP = None, NODE_4_MAC = None, NODE_4_IPADDR = None, NODE_4_PORT = None, NODE_5_NAME = None, NODE_5_CTRL_IP = None, NODE_5_MAC = None, NODE_5_IPADDR = None, NODE_5_PORT = None, NODE_6_NAME = None, NODE_6_CTRL_IP = None, NODE_6_MAC = None, NODE_6_IPADDR = None, NODE_6_PORT = None, NODE_7_NAME = None, NODE_7_CTRL_IP = None, NODE_7_MAC = None, NODE_7_IPADDR = None, NODE_7_PORT = None, NODE_8_NAME = None, NODE_8_CTRL_IP = None, NODE_8_MAC = None, NODE_8_IPADDR = None, NODE_8_PORT = None, **args):
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
            "R": args["R"],
            "PORT": PORT,
            "TIMEOUT": args["TIMEOUT"]
        }
        fem_hk_template(**fem_hk_args)

        assert SENSOR in self.SENSOR_OPTIONS.keys()
        # Instantiate template corresponding to SENSOR, passing through some of own args
        status_template = self.SENSOR_OPTIONS[SENSOR][0]
        gui_name = PORT[:PORT.find(".")] + ".Status"
        status_args = {
            "P": args["P"],
            "R": args["R"],
            "ADDRESS": "0",
            "PORT": PORT,
            "NAME": gui_name,
            "TIMEOUT": args["TIMEOUT"],
            "TOTAL": self.SENSOR_OPTIONS[SENSOR][1]
        }
        status_template(**status_args)

        self.create_udp_file()
        self.create_odin_server_config_file()
        self.create_fr_startup_scripts()
        self.create_fp_startup_scripts()
        self.create_odin_server_startup_scripts()

    def daq_templates(self):
        print str(self.CONFIG_TEMPLATES[self.SENSOR])
        return self.CONFIG_TEMPLATES[self.SENSOR]

    def create_udp_file(self):
        output_file = IocDataStream("udp_excalibur.json")
        names = [self.NODE_1_NAME, self.NODE_2_NAME, self.NODE_3_NAME, self.NODE_4_NAME, self.NODE_5_NAME, self.NODE_6_NAME, self.NODE_7_NAME, self.NODE_8_NAME]
        macs = [self.NODE_1_MAC, self.NODE_2_MAC, self.NODE_3_MAC, self.NODE_4_MAC, self.NODE_5_MAC, self.NODE_6_MAC, self.NODE_7_MAC, self.NODE_8_MAC]
        ips = [self.NODE_1_IPADDR, self.NODE_2_IPADDR, self.NODE_3_IPADDR, self.NODE_4_IPADDR, self.NODE_5_IPADDR, self.NODE_6_IPADDR, self.NODE_7_IPADDR, self.NODE_8_IPADDR]
        ports = [self.NODE_1_PORT, self.NODE_2_PORT, self.NODE_3_PORT, self.NODE_4_PORT, self.NODE_5_PORT, self.NODE_6_PORT, self.NODE_7_PORT, self.NODE_8_PORT]
        number_of_nodes = 0
        output_text = '{\n\
    "fems": [\n'
        for index in [1,2,3,4,5,6]:
            offset = index - 1
            output_text = output_text + '        {{\n\
            "name": "fem{}",\n\
            "mac": "62:00:00:00:00:0{}",\n\
            "ipaddr": "10.0.2.10{}",\n\
            "port": 6000{},\n\
            "dest_port_offset": {}\n\
        }}'.format(index, index, index, index, offset)
            if index < 6:
                output_text = output_text + ',\n'
            else:
                output_text = output_text + '\n'
        output_text = output_text + '    ],\n\
    "nodes": [\n'
        for NAME, MAC, IPADDR, PORT in zip(names, macs, ips, ports):
            if NAME is not None:
                output_text = output_text + '        {{\n\
            "name": "{}",\n\
            "mac" : "{}",\n\
            "ipaddr" : "{}",\n\
            "port": {}\n\
        }},\n'.format(NAME, MAC, IPADDR, PORT)
                number_of_nodes += 1
        output_text = output_text[:-2]
        output_text = output_text + '\n    ],\n\
    "farm_mode" : {{\n\
        "enable": 1,\n\
        "num_dests": {}\n\
    }}\n\
}}\n'.format(number_of_nodes)
        output_file.write(output_text)

    def create_odin_server_config_file(self):
        ips = [self.NODE_1_CTRL_IP, self.NODE_2_CTRL_IP, self.NODE_3_CTRL_IP, self.NODE_4_CTRL_IP, self.NODE_5_CTRL_IP, self.NODE_6_CTRL_IP, self.NODE_7_CTRL_IP, self.NODE_8_CTRL_IP]
        output_file = IocDataStream("excalibur_odin_{}.cfg".format(self.SENSOR))
        if self.SENSOR == '1M':
            chip_mask = '0xFF, 0xFF'
            if self.FEMS_REVERSED == 0:
                fem_list = '192.168.0.101:6969, 192.168.0.102:6969'
            else:
                fem_list = '192.168.0.102:6969, 192.168.0.101:6969'
        if self.SENSOR == '3M':
            chip_mask = '0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF'
            if self.FEMS_REVERSED == 0:
                fem_list = '192.168.0.101:6969, 192.168.0.102:6969, 192.168.0.103:6969, 192.168.0.104:6969, 192.168.0.105:6969, 192.168.0.106:6969'
            else:
                fem_list = '192.168.0.106:6969, 192.168.0.105:6969, 192.168.0.104:6969, 192.168.0.103:6969, 192.168.0.102:6969, 192.168.0.101:6969'

        # Loop over the UDP destinations, for each one setup a FP and FR control address
        # FP ports will always start 5004 and increment by 10
        # FR ports will always start 5000 and increment by 10
        fp_server_count = {}
        fp_ctrl_addresses = {}
        fr_endpoints = ""
        fp_endpoints = ""
        for ip in ips:
            if ip is not None:
                if ip not in fp_server_count:
                    fp_server_count[ip] = 0
                fp_port_number = 5004 + (10 * fp_server_count[ip])
                fr_port_number = 5000 + (10 * fp_server_count[ip])
                fp_server_count[ip] += 1
                fr_endpoints = fr_endpoints + ", {}:{}".format(ip, fr_port_number)
                fp_endpoints = fp_endpoints + ", {}:{}".format(ip, fp_port_number)
        fr_endpoints = fr_endpoints[2:]
        fp_endpoints = fp_endpoints[2:]
        print(fr_endpoints)
        print(fp_endpoints)

        output_text = '[server]\n\
debug_mode  = 1\n\
http_port   = 8888\n\
http_addr   = 0.0.0.0\n\
adapters    = excalibur, fp, fr\n\
\n\
[tornado]\n\
logging = error\n\
\n\
[adapter.excalibur]\n\
module = excalibur.adapter.ExcaliburAdapter\n\
detector_fems = {}\n\
powercard_fem_idx = {}\n\
chip_enable_mask = {}\n\
\n\
[adapter.fp]\n\
module = odin_data.frame_processor_adapter.FrameProcessorAdapter\n\
endpoints = {}\n\
update_interval = 0.2\n\
\n\
[adapter.fr]\n\
module = odin_data.odin_data_adapter.OdinDataAdapter\n\
endpoints = {}\n\
update_interval = 0.2\n\
\n'.format(fem_list, self.PWR_CARD_IDX, chip_mask, fp_endpoints, fr_endpoints)
        output_file.write(output_text)

    def create_fr_startup_scripts(self):
        ips = [self.NODE_1_CTRL_IP, self.NODE_2_CTRL_IP, self.NODE_3_CTRL_IP, self.NODE_4_CTRL_IP, self.NODE_5_CTRL_IP, self.NODE_6_CTRL_IP, self.NODE_7_CTRL_IP, self.NODE_8_CTRL_IP]
        fr_server_count = {}
        counter = 0
        for ip in ips:
            if ip is not None:
                counter += 1
                if ip not in fr_server_count:
                    fr_server_count[ip] = 0
                fr_port_number = 5000 + (10 * fr_server_count[ip])
                fr_rdy_port_number = 5001 + (10 * fr_server_count[ip])
                fr_rel_port_number = 5002 + (10 * fr_server_count[ip])
                fr_server_count[ip] += 1
                output_file = IocDataStream("stFrameReceiver{}.sh".format(counter), 0755)
                bin_path = os.path.join(FILE_WRITER_ROOT, "prefix")
                data_path = os.path.join(ADODIN_ROOT, "data")
                output_text = '#!/bin/bash\n\
cd {}\n\
./bin/frameReceiver --sharedbuf=exc_buf_{} -m {} --ctrl=tcp://0.0.0.0:{} --ready=tcp://*:{} --release=tcp://*:{} --logconfig {}/fr_log4cxx.xml\n'.format(bin_path, counter, self.SHARED_MEM_SIZE, fr_port_number, fr_rdy_port_number, fr_rel_port_number, data_path)
                output_file.write(output_text)
                print(output_text)

    def create_fp_startup_scripts(self):
        ips = [self.NODE_1_CTRL_IP, self.NODE_2_CTRL_IP, self.NODE_3_CTRL_IP, self.NODE_4_CTRL_IP, self.NODE_5_CTRL_IP, self.NODE_6_CTRL_IP, self.NODE_7_CTRL_IP, self.NODE_8_CTRL_IP]
        fp_server_count = {}
        counter = 0
        for ip in ips:
            if ip is not None:
                counter += 1
                if ip not in fp_server_count:
                    fp_server_count[ip] = 0
                fp_port_number = 5004 + (10 * fp_server_count[ip])
                fp_server_count[ip] += 1
                output_file = IocDataStream("stFrameProcessor{}.sh".format(counter), 0755)
                bin_path = os.path.join(FILE_WRITER_ROOT, "prefix")
                data_path = os.path.join(ADODIN_ROOT, "data")
                output_text = '#!/bin/bash\n\
cd {}\n\
./bin/frameProcessor --ctrl=tcp://0.0.0.0:{} --logconfig {}/fp_log4cxx.xml\n'.format(bin_path, fp_port_number, data_path)
                output_file.write(output_text)
                print(output_text)

    def create_odin_server_startup_scripts(self):
        output_file = IocDataStream("stExcaliburOdinServer.sh", 0755)
        bin_path = os.path.join(EXCALIBUR_ROOT, "prefix/bin/excalibur_odin")
        output_text = '#!/bin/bash\nSCRIPT_DIR="$( cd "$( dirname "$0" )" && pwd )"\n{} --config=$SCRIPT_DIR/excalibur_odin_{}.cfg --logging=error\n'.format(bin_path, self.SENSOR)
        output_file.write(output_text)
        print(output_text)

    # __init__ arguments
    ArgInfo = ADBaseTemplate.ArgInfo + _SpecificTemplate.ArgInfo + makeArgInfo(__init__,
        PORT=Simple("Port name for the detector", str),
        SERVER=Simple("Server host name", str),
        ODIN_SERVER_PORT=Simple("Odin server port", int),
        SENSOR=Choice("Sensor type", ["1M", "3M"]),
        BUFFERS=Simple("Maximum number of NDArray buffers to be created for plugin callbacks", int),
        MEMORY=Simple("Max memory to allocate, should be maxw*maxh*nbuffer for driver and all "
                      "attached plugins", int),
        FEMS_REVERSED=Simple("Are the FEM IP addresses reversed 106..101", int),
        PWR_CARD_IDX=Simple("Index of the power card", int),
        SHARED_MEM_SIZE=Simple("Size of shared memory buffers in bytes", int),
        NODE_1_NAME=Simple("Name of detector output node 1", str),
        NODE_1_CTRL_IP=Simple("IP address for control of FR and FP", str),
        NODE_1_MAC=Simple("Mac address of detector output node 1", str),
        NODE_1_IPADDR=Simple("IP address of detector output node 1", str),
        NODE_1_PORT=Simple("Port of detector output node 1", int),
        NODE_2_NAME=Simple("Name of detector output node 2", str),
        NODE_2_CTRL_IP=Simple("IP address for control of FR and FP", str),
        NODE_2_MAC=Simple("Mac address of detector output node 2", str),
        NODE_2_IPADDR=Simple("IP address of detector output node 2", str),
        NODE_2_PORT=Simple("Port of detector output node 2", int),
        NODE_3_NAME=Simple("Name of detector output node 3", str),
        NODE_3_CTRL_IP=Simple("IP address for control of FR and FP", str),
        NODE_3_MAC=Simple("Mac address of detector output node 3", str),
        NODE_3_IPADDR=Simple("IP address of detector output node 3", str),
        NODE_3_PORT=Simple("Port of detector output node 3", int),
        NODE_4_NAME=Simple("Name of detector output node 4", str),
        NODE_4_CTRL_IP=Simple("IP address for control of FR and FP", str),
        NODE_4_MAC=Simple("Mac address of detector output node 4", str),
        NODE_4_IPADDR=Simple("IP address of detector output node 4", str),
        NODE_4_PORT=Simple("Port of detector output node 4", int),
        NODE_5_NAME=Simple("Name of detector output node 5", str),
        NODE_5_CTRL_IP=Simple("IP address for control of FR and FP", str),
        NODE_5_MAC=Simple("Mac address of detector output node 5", str),
        NODE_5_IPADDR=Simple("IP address of detector output node 5", str),
        NODE_5_PORT=Simple("Port of detector output node 5", int),
        NODE_6_NAME=Simple("Name of detector output node 6", str),
        NODE_6_CTRL_IP=Simple("IP address for control of FR and FP", str),
        NODE_6_MAC=Simple("Mac address of detector output node 6", str),
        NODE_6_IPADDR=Simple("IP address of detector output node 6", str),
        NODE_6_PORT=Simple("Port of detector output node 6", int),
        NODE_7_NAME=Simple("Name of detector output node 7", str),
        NODE_7_CTRL_IP=Simple("IP address for control of FR and FP", str),
        NODE_7_MAC=Simple("Mac address of detector output node 7", str),
        NODE_7_IPADDR=Simple("IP address of detector output node 7", str),
        NODE_7_PORT=Simple("Port of detector output node 7", int),
        NODE_8_NAME=Simple("Name of detector output node 8", str),
        NODE_8_CTRL_IP=Simple("IP address for control of FR and FP", str),
        NODE_8_MAC=Simple("Mac address of detector output node 8", str),
        NODE_8_IPADDR=Simple("IP address of detector output node 8", str),
        NODE_8_PORT=Simple("Port of detector output node 8", int))
