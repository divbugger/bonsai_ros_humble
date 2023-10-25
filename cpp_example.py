#!/usr/bin/env python

#Copyright (c) 2017 Andre Santos
#
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:

#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.

#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.

from __future__ import print_function
from __future__ import unicode_literals
from builtins import range

import sys
from bonsai.analysis import *
from bonsai.cpp.clang_parser import CppAstParser
import os



# ----- Setup ------------------------------------------------------------------

# if len(sys.argv) < 2:
#     print("Please provide a file to be analysed.")
#     sys.exit(1)
# v = "3.8"
# argi = 1
# if sys.argv[1] == "-v":
#     if len(sys.argv) < 4:
#         print("Please provide a file to be analysed.")
#         sys.exit(1)
#     v = sys.argv[2]
#     argi = 3

# Hard setting the values for testing 
v=14
argi=3
fileToParse = "/home/divya/ros2_ws/src/ros_tutorials/turtlesim/src/turtle_frame.cpp"

CppAstParser.set_library_path(lib_path="/usr/lib/llvm-{v}/lib".format(v=v))
CppAstParser.set_standard_includes(
    "/usr/lib/llvm-{v}/lib/clang/{v}.0/include".format(v=v))
parser = CppAstParser(workspace = "/home/divya/ros2_ws/src/ros_tutorials/turtlesim", 
                      user_includes=["/home/divya/ros2_ws/src/ros_tutorials/turtlesim/include"])
parser.parse(fileToParse)

# for i in range(argi, len(sys.argv)):
#     if parser.parse(sys.argv[i]) is None:
#         print("No compile commands for file", sys.argv[i])
#         sys.exit(1)
# ----- Printing Program -------------------------------------------------------
print(parser.global_scope)
print("\n----------------------------------\n")
# ----- Performing Queries -----------------------------------------------------

def printCppObjInfo(cppobj, type_of_property):
    print("[{}:{}]".format(cppobj.line, cppobj.column), cppobj.pretty_str())

    if hasattr(cppobj, "result"):
        print("[type]", cppobj.result)
        if 'dependent type' in cppobj.result:
            print('dep true')
    
    if hasattr(cppobj, "canonical_type"):
        print("[canon. type]", cppobj.canonical_type)
    if hasattr(cppobj, "reference"):
        print("[reference]", cppobj.reference or "unknown")

    if 'reference' in type_of_property:
        value = resolve_reference(cppobj)
        if not value is None and value != cppobj:
            print("[value]", value)
        if is_under_control_flow(cppobj, recursive = True):
            print("[conditional evaluation]")
        else:
            print("[always evaluated]")
    
    print("")


# List of function names to call, taken from AST Analysis (analysis.py)
function_names = ["all_definitions", "all_references"]

def recursiveCall(currObj):

    printCppObjInfo(currObj)
    
    if currObj._children():
        for child in currObj._children():
            
            recursiveCall(child)

# Loop through the function names and call each function
my_instance = CodeQuery(parser.global_scope)


for func_name in function_names:
    print("------", func_name,"-----")
    property = getattr(my_instance, func_name)
    for cppobj in (property.get()):
        
        printCppObjInfo(cppobj, type_of_property=func_name)

