from pybuilder.core import use_plugin, init

use_plugin("python.core")
use_plugin("python.unittest")
use_plugin("python.coverage")
use_plugin("python.distutils")


@init
def initialize(project):
    project.set_property("dir_source_main_python", "lib/")
    project.set_property("dir_source_unittest_python", "test/mocked")
    project.set_property("unittest_module_glob", "*_test.py")

default_task = 'publish'
