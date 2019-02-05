import os
from string import Template

from iocbuilder.iocinit import IocDataStream
from dls_dependency_tree import dependency_tree


def debug_print(message, level):
    if int(os.getenv("ODIN_BUILDER_DEBUG", 0)) == level:
        print(message)


ADODIN_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.."))
ADODIN_DATA = os.path.join(ADODIN_ROOT, "data")

TREE = None


def find_module_path(module):
    global TREE
    if TREE is None:
        TREE = dependency_tree()
        TREE.process_module(ADODIN_ROOT)
    for macro, path in TREE.macros.items():
        if "/{}".format(module) in path:
            return macro, path


def data_file_path(file_name):
    return os.path.join(ADODIN_DATA, file_name)


def expand_template_file(template, macros, output_file, executable=False):
    if executable:
        mode = 0755
    else:
        mode = None

    with open(os.path.join(ADODIN_DATA, template)) as template_file:
        template_config = Template(template_file.read())

    output = template_config.substitute(macros)
    debug_print("--- {} ----------------------------------------------".format(output_file), 2)
    debug_print(output, 2)
    debug_print("---", 2)

    stream = IocDataStream(output_file, mode)
    stream.write(output)


def create_batch_entry(beamline, number, name):
    return "{beamline}-EA-ODN-{number:02d} st{name}.sh".format(
        beamline=beamline, number=number, name=name
    )
