# ast.py
# Minimal AST nodes for ANEX v0.1


class Program:
    def __init__(self, unit):
        self.unit = unit

    def __repr__(self):
        return f"Program({self.unit})"


class Unit:
    def __init__(self, name, statements):
        self.name = name
        self.statements = statements

    def __repr__(self):
        return f"Unit({self.name}, {self.statements})"
    
    
class VarDecl:
    def __init__(self, var_type, name, value):
        self.var_type = var_type
        self.name = name
        self.value = value

    def __repr__(self):
        return f"VarDecl({self.var_type} {self.name} = {self.value})"

class EmitStmt:
    def __init__(self, expr):
        self.expr = expr

    def __repr__(self):
        return f"Emit({self.expr})"


class BinOp:
    def __init__(self, left, op, right):
        self.left = left
        self.op = op
        self.right = right

    def __repr__(self):
        return f"({self.left} {self.op} {self.right})"
class LogicalOp:
    def __init__(self, left, op, right):
        self.left = left
        self.op = op      # 'and' | 'or'
        self.right = right

    def __repr__(self):
        return f"({self.left} {self.op} {self.right})"


class NotOp:
    def __init__(self, expr):
        self.expr = expr

    def __repr__(self):
        return f"(not {self.expr})"


class Number:
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return str(self.value)
    

class BoolLiteral:
    def __init__(self, value: bool):
        self.value = value

    def __repr__(self):
        return f"Bool({self.value})"


class TextLiteral:
    def __init__(self, value: str):
        self.value = value

    def __repr__(self):
        return f'Text("{self.value}")'


class Identifier:
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self.name
class IfStmt:
    def __init__(self, condition, then_body, else_body=None):
        self.condition = condition
        self.then_body = then_body
        self.else_body = else_body

    def __repr__(self):
        return f"If({self.condition}, {self.then_body}, else={self.else_body})"



class WhileStmt:
    def __init__(self, condition, body):
        self.condition = condition
        self.body = body

    def __repr__(self):
        return f"While({self.condition}, {self.body})"


class FuncDecl:
    def __init__(self, name, params, body):
        self.name = name
        self.params = params      # list of parameter names
        self.body = body          # list of statements

    def __repr__(self):
        return f"FuncDecl({self.name}, {self.params}, {self.body})"


class ReturnStmt:
    def __init__(self, expr):
        self.expr = expr

    def __repr__(self):
        return f"Return({self.expr})"


class FuncCall:
    def __init__(self, name, args):
        self.name = name
        self.args = args

    def __repr__(self):
        return f"Call({self.name}, {self.args})"
