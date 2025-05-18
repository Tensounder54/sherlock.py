""" Analyse code to ensure that it can be converted. """
import ast
from sherlock.codelib.generator import CodeGenerator
from sherlock.codelib.cmd import analyze_cmd
from sherlock.codelib.analyzer.function import Function, Functions
from sherlock.codelib.analyzer.variable import Type, Variable, Variables
from sherlock.codelib.system_function import is_system_function, SystemFunction
from sherlock.errors import CompileError, SyntaxNotSupportError, ParamTypeMismatchError


class CodeAnalyzer(object):
    """ Provides functions for analysing python code for conversion to bash. """

    def __init__(self, code):
        """
        Creates a new instance of a CodeAnalyzer.

        :param code: The code to be analysed.
        :type code: str

        :raises CompileError: when ast fails to parse the code.
        """
        self.code = code
        self.module_node = ast.parse(self.code)
        self.functions = Functions()
        self.variables = Variables()
        if not isinstance(self.module_node, ast.Module):
            raise CompileError()

    def analysis(self):
        """
        Analyses the code that's a property of this analyser. 

        :returns: A new CodeGenerator based on the code nodes that are a property of this CodeAnalyser.
        :rtype: CodeGenerator
        """
        for node in self.module_node.body:
            if isinstance(node, ast.Assign):
                self.analysis_assign_node(self.variables, node)
            elif isinstance(node, ast.Expr):
                if isinstance(node.value, ast.Call):
                    self.get_type(node.value)
            elif isinstance(node, ast.ImportFrom):
                analyze_cmd(node)
        generator = CodeGenerator(self.code, functions=self.functions, variables=self.variables)
        return generator

    def analysis_function(self, function_node, args_type=[]):
        """
        Function to analyse the code.

        :param function_node: The nodes of the function being analised.
        :type function_node: Module

        :param args_type: The types of the function passed in's arguments.
        :type args_type: list

        :returns: A new code generator based on the passed in functions.
        :rtype: CodeGenerator

        :returns: The return type of the function passed in.
        :rtype: (None | VOID)
        """
        variables = Variables()
        return_type = Type.VOID

        for node in function_node.body:
            if isinstance(node, ast.Assign):
                self.analysis_assign_node(variables, node)
            elif isinstance(node, ast.Return):
                return_type = self.get_type(node.value)
                if return_type is None:
                    return_type = Type.VOID
        generator = CodeGenerator(self.code,variables=variables)
        return generator, return_type

    def analysis_assign_node(self, variables, node):
        """
        Analyses nodes that have been assigned.

        :param variables: The list of variables for the code being analysed.
        :type variables: list[Variables]

        :param node: An stmt pulled in through the AST library.
        :type node: stmt
        """
        if len(node.targets) > 1:
            raise SyntaxNotSupportError('Tuple assignment is not support yet.')
        target = node.targets[0]
        variables.append(Variable(name=target.id, var_type=self.get_type(node.value)))

    def get_function_return_type(self, function_name, args_type=[]):
        """
        Function to analyse the code.

        :param function_name: The name of the function we're looking to get the return type for.
        :type function_name: str

        :param args_type: The types of the function passed in's arguments.
        :type args_type: list

        :returns: The return type of the retrieved function.
        :rtype: Function.return_type

        :returns: A blank STRING type.
        :rtype: STRING

        :raises ParamTypeMismatchError: When the passed in function name cannot be found.
        """
        function = self.functions[function_name]
        if is_system_function(function_name):
            return SystemFunction.get_function(function_name).return_type
        if function is not None:
            if function.is_args_type_match(args_type):
                return function.return_type
            else:
                raise ParamTypeMismatchError("Function '%s' parameter type is not match", function_name)
        else:
            for node in self.module_node.body:
                if isinstance(node, ast.FunctionDef) and node.name == function_name:
                    generator, return_type = self.analysis_function(node, args_type)
                    self.functions.append(Function(function_name, args_type, return_type, generator))
                    return return_type
            return Type.STRING  # when function is not exist: string

    def get_type(self, node):
        """
        Get the type of the passed in node.

        :param node: An stmt pulled in through the AST library.
        :type node: stmt

        :returns: The type of the passed in stmt object.
        :rtype: (Type.NUMBER | Type.STRING | Type.LIST | Any)

        :raises SyntaxNotSupportError: When an a non number unary operator is passed in.
        """
        if isinstance(node, ast.BinOp):
            left_type = self.get_type(node.left)
            right_type = self.get_type(node.right)

            if isinstance(node.op, ast.Add):
                if left_type.is_number and right_type.is_number:
                    return Type.NUMBER
                else:
                    return Type.STRING
            elif left_type.is_number and right_type.is_number:
                return Type.NUMBER
            else:
                raise CompileError("Can not '%s' operator with string." % node.op.__class__.__name__)
        elif isinstance(node, ast.UnaryOp):
            if isinstance(operand, ast.Num):
                return Type.NUMBER
            else:
                raise SyntaxNotSupportError("Not support unary operator except number.")

        elif isinstance(node, ast.Num):
            return Type.NUMBER

        elif isinstance(node, ast.Str):
            return Type.STRING
        elif isinstance(node, ast.List):
            return Type.LIST
        elif isinstance(node, ast.Call):
            args_type = [self.get_type(arg) for arg in node.args]
            return self.get_function_return_type(node.func.id, args_type)
        elif isinstance(node, ast.Name):
            return self.variables[node.id].var_type

