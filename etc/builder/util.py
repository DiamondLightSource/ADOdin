import json
import os
import re
import uuid
from string import Template

from iocbuilder.iocinit import IocDataStream


def debug_print(message, level):
    if int(os.getenv("ODIN_BUILDER_DEBUG", 0)) >= level:
        print(message)


ADODIN_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.."))
ADODIN_DATA = os.path.join(ADODIN_ROOT, "data")


def data_file_path(file_name):
    return os.path.join(ADODIN_DATA, file_name)


class OdinPaths(object):

    @classmethod
    def configure_paths(cls, release_path):
        paths = cls.parse_release_file(release_path)

        cls.ODIN_PROC_SERV_CONTROL = paths["ODIN_PROC_SERV_CONTROL"]
        cls.HDF5_FILTERS = os.path.join(paths["HDF5_FILTERS"], "prefix/hdf5_1.10/h5plugin")
        cls.ODIN_DATA_TOOL = paths["ODIN_DATA_TOOL"]
        cls.ODIN_DATA_PYTHON = paths["ODIN_DATA_PYTHON"]

        for detector_path in [
            path for module, path in paths.items()
            if module.endswith("TOOL") and not "ODIN_DATA" in module
        ]:
            detector_paths = cls.parse_release_file(
                os.path.join(detector_path, "../configure/RELEASE")
            )
            if detector_paths["ODIN_DATA"] != cls.ODIN_DATA_TOOL:
                print(
                    "WARNING: Mismatched odin-data dependency in {}".format(
                        detector_path
                    )
                )

        for module, path in paths.items():
            if module.endswith("TOOL") or module.endswith("PYTHON"):
                setattr(cls, module, path)

    @classmethod
    def parse_release_file(cls, release_path):
        macros = {}
        with open(release_path) as release_file:
            for line in release_file.readlines():
                if not line.startswith("#") and "=" in line:
                    module, path = line.split("=", 1)
                    macros[module.strip()] = path.strip()

        macro_re = re.compile(r"\$\(([^\)]+)\)")
        for macro in macros:
            for find in macro_re.findall(macros[macro]):
                if find in macros.keys():
                    macros[macro] = macros[macro].replace("$({})".format(find), macros[find])

        return macros


# Read Odin paths on import
OdinPaths.configure_paths(
    os.path.join(ADODIN_ROOT, "configure/RELEASE.local")
)


def expand_template_file(input_file, macros, output_file, executable=False):
    if executable:
        mode = 0o755
    else:
        mode = None

    with open(os.path.join(ADODIN_DATA, input_file)) as f:
        input_content = f.read()

    if macros is not None:
        output = Template(input_content).substitute(macros)
    else:
        output = input_content

    debug_print("--- {} ----------------------------------------------".format(output_file), 2)
    debug_print(output, 2)
    debug_print("---", 2)

    stream = IocDataStream(output_file, mode)
    stream.write(output)


def write_batch_file(batch_entries):
    stream = IocDataStream("configure_odin")
    stream.write("\n".join(batch_entries) + "\n")

class OneLineEntry(object):

    """A wrapper to stop JSON entries being split across multiple lines.

    Wrap this around lists, dictionaries, etc to stop json.dumps from
    splitting them over multiple lines. Must pass OneLineEncoder to
    json.dumps(cls=).

    """
    def __init__(self, value):
        self.value = value


class OneLineEncoder(json.JSONEncoder):

    def __init__(self, *args, **kwargs):
        super(OneLineEncoder, self).__init__(*args, **kwargs)
        self.kwargs = dict(kwargs)
        del self.kwargs["indent"]
        self._replacement_map = {}

    def default(self, o):
        if isinstance(o, OneLineEntry):
            key = uuid.uuid4().hex
            self._replacement_map[key] = json.dumps(o.value, **self.kwargs)
            return "@@%s@@" % (key,)
        else:
            return super(OneLineEncoder, self).default(o)

    def encode(self, o):
        result = super(OneLineEncoder, self).encode(o)
        for key, value in self._replacement_map.iteritems():
            result = result.replace("\"@@%s@@\"" % (key,), value)
        return result


def create_config_entry(dictionary):
    entry = json.dumps(dictionary, indent=2, cls=OneLineEncoder)
    return entry.replace("\n", "\n  ")
