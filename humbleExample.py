# Modified cpp_example.py, from Bonsai, for rosHumbleExtractor.py


from __future__ import print_function
from __future__ import unicode_literals
from builtins import next
from builtins import object

from collections import deque
from ctypes import ArgumentError
import os

import clang.cindex as clang

from bonsai.cpp.model import *
from bonsai.analysis import *
from bonsai.cpp.clang_parser import  AnalysisData, MultipleDefinitionError, CodeAstParser, CppTopLevelBuilder

from haros.metamodel import Node, Package, RosName, SourceFile
from rosHumbleExtractor import RosHumbleCMakeExtractor, CppParserHumble


def cppHandler(filename:str ,
         pkg:Package,
         wsRos:str, 
         usr_include:list, 
         clangVersion:int=14):

    CppParserHumble.set_library_path(lib_path="/usr/lib/llvm-{v}/lib".format(v=clangVersion))
    CppParserHumble.set_standard_includes("/usr/lib/llvm-{v}/lib/clang/{v}.0/include".format(v=clangVersion))

    
    cppParser = CppParserHumble(workspace = pkg.path, 
                                user_includes=usr_include)
    cppParser.parse(fileToParse)

    db_dir = os.path.join(wsRos, "build")
    if os.path.isfile(os.path.join(db_dir, "compile_commands.json")):
        cppParser.set_database(db_dir)
    else:
      print("The compile_commands.json file can't be found")

    # print(cppParser.global_scope.pretty_str())
    # print("\n----------------------------------\n")

    cppParser.rosHumbleAstTest()


if __name__ == "__main__":

    fileToParse = "/home/divya/ros2_ws/src/ros_tutorials/turtlesim/src/turtle_frame.cpp"
    userIncludePath = ["/home/divya/ros2_ws/src/ros_tutorials/turtlesim/include"]
    rosPkgWorkSpace = "/home/divya/ros2_ws/src/ros_tutorials/turtlesim"
    rosWorkSpace = "/home/divya/ros2_ws"
    pkgName="turtlesim"
    pkg= Package(pkgName)
    pkg.path = rosPkgWorkSpace
    node_name = 'turtlesim_node'

    ## -- Cmake parser Section 
    cmake_parser = RosHumbleCMakeExtractor(rosPkg=pkg, rosWorkSpace=rosWorkSpace)
    requestedNode = cmake_parser.requestNodeEntityFromPkg()


    for key, values in requestedNode.items():
        print(values.source_files)

    ## -- Cpp parser Section
    cppHandler(filename=fileToParse,
               pkg=pkg,
               wsRos=rosWorkSpace,
               usr_include=userIncludePath)


