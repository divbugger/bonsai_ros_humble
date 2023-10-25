# Modified ROS Model Extractor file with using Clang directly
# Run by humbleExample.py

import os
from collections import deque
from ctypes import ArgumentError


from haros.cmake_parser import RosCMakeParser
from haros.metamodel import Node, Package, RosName, SourceFile
from bonsai.cpp.model import *
from bonsai.analysis import *
from bonsai.cpp.clang_parser import  AnalysisData, MultipleDefinitionError, CodeAstParser, CppTopLevelBuilder


import clang.cindex as clang

CK = clang.CursorKind


class RosHumbleCMakeExtractor:

    CMAKE_FILE = "CMakeLists.txt"
    EXTRACT_ALL_NODES = '__ALL__'
    
    def __init__(self, rosWorkSpace:str, 
                 rosPkg:Package, 
                 nodesToExtract=EXTRACT_ALL_NODES):

        self._ws = rosWorkSpace
        self._pkg = rosPkg 
        self._node_to_extract = nodesToExtract

        self._build_dir = None
        self._cmake_parser = None
        self._node_database = None

        self.cmakeExtractBuilder()

    
    def setRosWorkSpace(self, newWs:str):
        self._ws = newWs

    def getRosWorkSpace(self,):
        return self._ws
    
    def setRosPkg(self, newPkg:Package):
        self._pkg = newPkg
    
    def getRosPkg(self):
        return self._pkg
    
    def calcRosBuildDir(self, buildDirName="build"):
        self._build_dir = os.path.join(self.getRosWorkSpace(), buildDirName)

    def getRosBuildDir(self,):
        return self._build_dir
    
    def createCMakeParser(self, srcdir:str, bindir:str, pkgs:list):
        return RosCMakeParser(srcdir, bindir, pkgs = pkgs)

    def checkFileExsist(self, pathToCheck:str, fileToCheck:str = CMAKE_FILE):
        if os.path.isfile(os.path.join(pathToCheck, fileToCheck)):
            return True
        else:
            return False
    
    def doPkgAllNodeExtraction(self,):
        
        node_db = dict()
        for target in self._cmake_parser.executables.values():
            node_name = target.output_name
            node = Node(node_name, self._pkg, rosname=RosName(node_name))
            
            for file_in in target.files:
                full_path = file_in
                relative_path = full_path.replace(self._pkg.path+"/","").rpartition("/")[0]
                file_name = full_path.rsplit('/', 1)[-1]
                source_file = SourceFile(file_name, relative_path , self._pkg)
                node.source_files.append(source_file)
            
            # Append to node db
            node_db[node_name] = node

        self._node_database = node_db

    def getNodeByName(self, nameToSearch:str):

        if nameToSearch in self._node_database.keys:
            return {nameToSearch : self._node_database[nameToSearch]}
        else:
            raise Exception('Node name: {}, not found in the node database'.format(nameToSearch))


    def getPkgNodeDatabase(self,):
        return self._node_database
    
    def cmakeExtractBuilder(self,):

        self.calcRosBuildDir()
        self._cmake_parser = self.createCMakeParser(srcdir=self._pkg.path,
                               bindir=self._build_dir,
                               pkgs=[self._pkg])
        
        # Parse CmakeFile to the parser
        cmakeFile = os.path.abspath(os.path.join(self._pkg.path, RosHumbleCMakeExtractor.CMAKE_FILE)) 
        if self.checkFileExsist(pathToCheck=self._pkg.path):
            self._cmake_parser.parse(cmakeFile)
        else:
            raise Exception('CMakeList.txt not found at : {}'.format(cmakeFile))
        
        self.doPkgAllNodeExtraction()
    
    def requestNodeEntityFromPkg(self, node_names_to_search=EXTRACT_ALL_NODES):
        
        if node_names_to_search == RosHumbleCMakeExtractor.EXTRACT_ALL_NODES:
            return self._node_database
        else:

            assert isinstance(node_names_to_search, list), "node_names is not a list"
            for item in node_names_to_search:
                assert isinstance(item, str), "node_names List contains non-string element"

            node_dict = dict()
            for name in node_names_to_search:
                node_dict.update(self.getNodeByName(name))
            
            return node_dict
        

class CppParserHumble(CodeAstParser):
    lib_path = None
    lib_file = None
    includes = "/usr/lib/llvm-3.8/lib/clang/3.8.0/include"
    database = None

    # system required / user optional
    @staticmethod
    def set_library_path(lib_path='/usr/lib/llvm-3.8/lib'):
        clang.Config.set_library_path(lib_path)
        CppParserHumble.lib_path = lib_path

    @staticmethod
    def set_library_file(lib_file = "/usr/lib/llvm-3.8/lib/libclang.so"):
        clang.Config.set_library_file(lib_file)
        CppParserHumble.lib_file = lib_file

    # optional
    @staticmethod
    def set_database(db_path):
        if not CppParserHumble.lib_path:
            CppParserHumble.set_library_path()
        CppParserHumble.database = clang.CompilationDatabase.fromDirectory(db_path)
        CppParserHumble.database.db_path = db_path

    # optional
    @staticmethod
    def set_standard_includes(std_includes):
        CppParserHumble.includes = std_includes

    def __init__(self, workspace = "", user_includes = None, logger=None):
        CodeAstParser.__init__(self, workspace, logger)
    # public:
        self.workspace      = os.path.abspath(workspace) if workspace else ""
        self.global_scope   = CppGlobalScope()
        self.data           = AnalysisData()
        self.user_includes  = [] if user_includes is None else user_includes
    # private:
        self._index         = None
        self._db            = CppParserHumble.database
        self._top_cursor_tu = list()

    @CodeAstParser.with_logger
    def parse(self, file_path):
        file_path = os.path.abspath(file_path)
        if self._db is None:
            return self._parse_without_db(file_path)
        return self._parse_from_db(file_path)

    def get_ast(self, file_path):
        file_path = os.path.abspath(file_path)
        if self._db is None:
            return self._parse_without_db(file_path, just_ast=True)
        return self._parse_from_db(file_path, just_ast=True)

    def _parse_from_db(self, file_path, just_ast=False):
        # ----- command retrieval ---------------------------------------------
        cmd = self._db.getCompileCommands(file_path) or ()
        if not cmd:
            return None
        for c in cmd:
            with cwd(os.path.join(self._db.db_path, c.directory)):
                args = ['-I' + CppParserHumble.includes] + list(c.arguments)[1:]
                if self._index is None:
                    self._index = clang.Index.create()

                # ----- parsing and AST analysis ------------------------------
                unit = self._index.parse(None, args)
                self._check_compilation_problems(unit)
                if just_ast:
                    return self._ast_str(unit.cursor)
                self._ast_analysis(unit.cursor)

        self.global_scope._afterpass()
        return self.global_scope

    def _parse_without_db(self, file_path, just_ast=False):
        # ----- command retrieval ---------------------------------------------
        with cwd(os.path.dirname(file_path)):
            args = ['-I' + CppParserHumble.includes]

            for include_dir in self.user_includes:
                args.append('-I' + include_dir)

            args.append(file_path)

            if self._index is None:
                self._index = clang.Index.create()

            # ----- parsing and AST analysis ----------------------------------
            unit = self._index.parse(None, args)
            self._check_compilation_problems(unit)
            if just_ast:
                return self._ast_str(unit.cursor)
            self._ast_analysis(unit.cursor)
            self._top_cursor_tu.append(unit.cursor)
        self.global_scope._afterpass()
        return self.global_scope

    def _ast_analysis(self, top_cursor):
        assert top_cursor.kind == CK.TRANSLATION_UNIT
        cppobj = self.global_scope
        builders = [
            CppTopLevelBuilder(c, cppobj, cppobj)
            for c in top_cursor.get_children()
            if c.location.file
                    and c.location.file.name.startswith(self.workspace)
        ]

        queue = deque(builders)

        while queue:
            builder = queue.popleft()
            result = builder.build(self.data)

            if result:
                cppobj, builders = result
                if builder.insert_method:
                    builder.insert_method(cppobj)
                else:
                    builder.parent._add(cppobj)

                queue.extend(builders)

    # Function to print objects from CLANG Parser and trial to associate it with the node SharedPtr handle: nh_
    # More information about the available Cpp Entity objects in cindex.py 
    def rosHumbleAstTest(self, codeobj=None):

        targetKindList = [clang.CursorKind.FIELD_DECL]
        for curr_cursor in self._top_cursor_tu:
            for cursor in curr_cursor.walk_preorder():
                if cursor.kind in targetKindList:
                    print(cursor.type.spelling, cursor.displayname)
                    if cursor.displayname == 'nh_':
                        print(cursor.type.get_canonical().spelling, cursor.type.get_pointee())
                    # logging.info("{} --- {} --- {} -- {} -- {}".format(cursor.kind,cursor.spelling, cursor.type.get_canonical().spelling, cursor.location.line, cursor.location.file))
                    # if cursor.kind == clang.CursorKind.FIELD_DECL and cursor.location.line == 92:
                    #     print("FIELD type: {}: usage: {}:".format(cursor.type.spelling, cursor.get_usr()))

    def _ast_str(self, top_cursor):
        assert top_cursor.kind == CK.TRANSLATION_UNIT

        lines = []
        for cursor in top_cursor.get_children():
            if (cursor.location.file
                    and cursor.location.file.name.startswith(self.workspace)):
                lines.append(self._cursor_str(cursor, 0))
                indent = 0
                stack = list(cursor.get_children())
                stack.append(1)
                while stack:
                    c = stack.pop()
                    if isinstance(c, int):
                        indent += c
                    else:
                        lines.append(self._cursor_str(c, indent))
                        stack.append(-1)
                        stack.extend(c.get_children())
                        stack.append(1)
        return '\n'.join(lines)

    @staticmethod
    def _check_compilation_problems(translation_unit):
        if translation_unit.diagnostics:
            for diagnostic in translation_unit.diagnostics:
                if diagnostic.severity >= clang.Diagnostic.Error:
                    # logging.warning(diagnostic.spelling)
                    print('WARNING', diagnostic.spelling)

    @staticmethod
    def _cursor_str(cursor, indent):
        line = 0
        col = 0
        try:
            if cursor.location.file:
                line = cursor.location.line
                col = cursor.location.column
        except ArgumentError as e:
            pass
        name = repr(cursor.kind)[11:]
        spell = cursor.spelling or '[no spelling]'
        tokens = len(list(cursor.get_tokens()))
        prefix = indent * '| '
        return '{}[{}:{}] {}: {} [{} tokens]'.format(prefix, line, col,
                                                     name, spell, tokens)

    def runAnalysis(self, top_cursor):
        assert top_cursor.kind == CK.TRANSLATION_UNIT
        cppobj = self.global_scope

        builders = []

        for cursor in top_cursor.get_children():

            if cursor.location.file.name and cursor.location.file.name.startswith(self.workspace):
                builders.append(CppTopLevelBuilder(cursor, cppobj, cppobj))

        print(len(builders))
        print(builders)





class cwd(object):
    """Run a block of code from a specified working directory"""
    def __init__(self, path):
        self.dir = path

    def __enter__(self):
        self.old_dir = os.getcwd()
        os.chdir(self.dir)

    def __exit__(self, exc_type, exc_value, traceback):
        os.chdir(self.old_dir)


class RosHumbleCppExtractor:

    def __init__(self, ):
        pass

    