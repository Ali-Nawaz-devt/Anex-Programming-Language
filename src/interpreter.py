from src.anex_ast import BoolLiteral, WhileStmt
from src.anex_ast import TextLiteral

from src.anex_ast import (
    Program,
    VarDecl,
    EmitStmt,
    IfStmt,
    WhileStmt,
    BinOp,
    Number,
    Identifier,
    LogicalOp,
    NotOp,
    FuncDecl,
    ReturnStmt,
    FuncCall,
)

class ReturnException(Exception):
    def __init__(self, value):
        self.value = value


class Interpreter:
    def __init__(self):
        self.env = {}
        self.functions = {}

    def run(self, program: Program):
        for stmt in program.unit.statements:
            self.visit(stmt)

    # --------------------
    # Statement execution
    # --------------------

    def visit(self, node):

        # Variable declaration
        if isinstance(node, VarDecl):
            if node.value is None:
                raise Exception(f"Variable '{node.name}' declared without initializer")
            self.env[node.name] = self.eval_expr(node.value)

        # Assignment
        elif isinstance(node, tuple) and node[0] == "assign":
            _, name, expr = node
            if name not in self.env:
                raise Exception(f"Undefined variable '{name}'")
            self.env[name] = self.eval_expr(expr)

        # Function declaration
        elif isinstance(node, FuncDecl):
            self.functions[node.name] = node

        # Return
        elif isinstance(node, ReturnStmt):
            value = self.eval_expr(node.expr)
            raise ReturnException(value)

        # If
        elif isinstance(node, IfStmt):
            if self.eval_expr(node.condition):
                for stmt in node.then_body:
                    self.visit(stmt)
            elif node.else_body:
                for stmt in node.else_body:
                    self.visit(stmt)

        # While
        elif isinstance(node, WhileStmt):
            while self.eval_expr(node.condition):
                for stmt in node.body:
                    self.visit(stmt)

        # Emit
        elif isinstance(node, EmitStmt):
            value = self.eval_expr(node.expr)

            if isinstance(value, bool):
                print("true" if value else "false")
            else:
                print(value)

    # --------------------
    # Expression evaluation
    # --------------------

    def eval_expr(self, expr):
        if isinstance(expr, TextLiteral):
            return expr.value


        # Function call
        if isinstance(expr, FuncCall):
            if expr.name not in self.functions:
                raise Exception(f"Undefined function '{expr.name}'")

            func = self.functions[expr.name]

            if len(expr.args) != len(func.params):
                raise Exception("Argument count mismatch")

            # 🔐 Save environment
            old_env = self.env
            self.env = old_env.copy()

            for param, arg in zip(func.params, expr.args):
                self.env[param] = self.eval_expr(arg)

            try:
                for stmt in func.body:
                    self.visit(stmt)
            except ReturnException as r:
                self.env = old_env
                return r.value

            self.env = old_env
            return None

        # admit
        if isinstance(expr, tuple) and expr[0] == "admit":
            return int(input())

        # literal
        if isinstance(expr, Number):
            return expr.value

        # variable
        if isinstance(expr, Identifier):
            if expr.name not in self.env:
                raise Exception(f"Undefined variable '{expr.name}'")
            return self.env[expr.name]
        if isinstance(expr, BoolLiteral):
            return expr.value
        if isinstance(expr, BinOp):
            left = self.eval_expr(expr.left)
            right = self.eval_expr(expr.right)

            if expr.op == "+":
                return left + right
            elif expr.op == "-":
                return left - right
            elif expr.op == "*":
                return left * right
            elif expr.op == "/":
                if right == 0:
                    raise Exception("Runtime Error: Division by zero")
                return left // right
            elif expr.op == ">":
                return left > right
            elif expr.op == "<":
                return left < right
            elif expr.op == ">=":
                return left >= right
            elif expr.op == "<=":
                return left <= right
            elif expr.op == "==":
                return left == right
            elif expr.op == "!=":
                return left != right

            raise Exception(f"Unknown operator {expr.op}")


        # logical
        if isinstance(expr, NotOp):
            return not self.eval_expr(expr.expr)

        if isinstance(expr, LogicalOp):
            if expr.op == "and":
                return self.eval_expr(expr.left) and self.eval_expr(expr.right)
            if expr.op == "or":
                return self.eval_expr(expr.left) or self.eval_expr(expr.right)

        raise Exception(f"Unknown expression: {expr}")






    def safe_div(self, left, right):
        if right == 0:
            raise Exception("Runtime Error: Division by zero")
        return left // right
