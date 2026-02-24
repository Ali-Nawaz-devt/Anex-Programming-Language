from src.anex_ast import (
    Program,
    Unit,
    VarDecl,
    EmitStmt,
    IfStmt,
    WhileStmt,
    FuncDecl,
    ReturnStmt,
    FuncCall,
    BinOp,
    Number,
    Identifier,
    LogicalOp,
    NotOp,
    BoolLiteral,
    TextLiteral,
)


class Parser:
    def __init__(self, lexer):
        self.lexer = lexer
        self.current = self.lexer.get_next_token()

    # =========================
    # UTIL
    # =========================
    def eat(self, kind, value=None):
        if self.current.kind != kind:
            raise Exception(f"Expected {kind}, got {self.current}")

        if value is not None and self.current.value != value:
            raise Exception(f"Expected {value}, got {self.current.value}")

        self.current = self.lexer.get_next_token()

    # =========================
    # PROGRAM
    # =========================
    def parse(self):
        return self.program()

    def program(self):
        unit = self.unit_decl()
        return Program(unit)

    def unit_decl(self):
        self.eat("KEYWORD", "unit")
        name = self.current.value
        self.eat("IDENT")
        self.eat("SYM", "{")

        statements = []
        while not (self.current.kind == "SYM" and self.current.value == "}"):
            statements.append(self.statement())

        self.eat("SYM", "}")
        return Unit(name, statements)

    # =========================
    # STATEMENTS
    # =========================
    def statement(self):

        # variable declaration
        if self.current.kind == "KEYWORD" and self.current.value in ("int", "bool", "text"):
            return self.var_decl()

        # assignment
        if self.current.kind == "IDENT":
            name = self.current.value
            self.eat("IDENT")

            if self.current.kind == "OP" and self.current.value == "=":
                self.eat("OP", "=")
                expr = self.expression()
                self.eat("SYM", ";")
                return ("assign", name, expr)

            raise Exception("Invalid statement")

        if self.current.kind == "KEYWORD" and self.current.value == "if":
            return self.if_stmt()

        if self.current.kind == "KEYWORD" and self.current.value == "while":
            return self.while_stmt()

        if self.current.kind == "KEYWORD" and self.current.value == "emit":
            return self.emit_stmt()

        if self.current.kind == "KEYWORD" and self.current.value == "func":
            return self.func_decl()

        if self.current.kind == "KEYWORD" and self.current.value == "return":
            return self.return_stmt()

        raise Exception(f"Unknown statement starting with {self.current}")

    # =========================
    # VAR DECL
    # =========================
    def var_decl(self):
        dtype = self.current.value
        self.eat("KEYWORD")

        name = self.current.value
        self.eat("IDENT")

        self.eat("OP", "=")
        value = self.expression()

        self.eat("SYM", ";")
        return VarDecl(dtype, name, value)

    # =========================
    # EMIT
    # =========================
    def emit_stmt(self):
        self.eat("KEYWORD", "emit")
        self.eat("SYM", "(")
        expr = self.expression()
        self.eat("SYM", ")")
        self.eat("SYM", ";")
        return EmitStmt(expr)

    # =========================
    # IF
    # =========================
    def if_stmt(self):
        self.eat("KEYWORD", "if")
        condition = self.expression()

        self.eat("SYM", "{")
        then_body = []
        while not (self.current.kind == "SYM" and self.current.value == "}"):
            then_body.append(self.statement())
        self.eat("SYM", "}")

        else_body = None
        if self.current.kind == "KEYWORD" and self.current.value == "else":
            self.eat("KEYWORD", "else")
            self.eat("SYM", "{")
            else_body = []
            while not (self.current.kind == "SYM" and self.current.value == "}"):
                else_body.append(self.statement())
            self.eat("SYM", "}")

        return IfStmt(condition, then_body, else_body)

    # =========================
    # WHILE
    # =========================
    def while_stmt(self):
        self.eat("KEYWORD", "while")
        condition = self.expression()

        self.eat("SYM", "{")
        body = []
        while not (self.current.kind == "SYM" and self.current.value == "}"):
            body.append(self.statement())
        self.eat("SYM", "}")

        return WhileStmt(condition, body)

    # =========================
    # FUNCTION
    # =========================
    def func_decl(self):
        self.eat("KEYWORD", "func")
        name = self.current.value
        self.eat("IDENT")

        self.eat("SYM", "(")
        params = []

        if self.current.kind == "IDENT":
            params.append(self.current.value)
            self.eat("IDENT")

            while self.current.kind == "SYM" and self.current.value == ",":
                self.eat("SYM", ",")
                params.append(self.current.value)
                self.eat("IDENT")

        self.eat("SYM", ")")
        self.eat("SYM", "{")

        body = []
        while not (self.current.kind == "SYM" and self.current.value == "}"):
            body.append(self.statement())

        self.eat("SYM", "}")
        return FuncDecl(name, params, body)

    def return_stmt(self):
        self.eat("KEYWORD", "return")
        expr = self.expression()
        self.eat("SYM", ";")
        return ReturnStmt(expr)

    # =========================
    # EXPRESSIONS
    # =========================
    def expression(self):
        return self.logical_or()

    def logical_or(self):
        left = self.logical_and()
        while self.current.kind == "KEYWORD" and self.current.value == "or":
            self.eat("KEYWORD", "or")
            right = self.logical_and()
            left = LogicalOp(left, "or", right)
        return left

    def logical_and(self):
        left = self.comparison()
        while self.current.kind == "KEYWORD" and self.current.value == "and":
            self.eat("KEYWORD", "and")
            right = self.comparison()
            left = LogicalOp(left, "and", right)
        return left

    def comparison(self):
        left = self.additive()
        while self.current.kind == "OP" and self.current.value in (">","<",">=","<=","==","!="):
            op = self.current.value
            self.eat("OP")
            right = self.additive()
            left = BinOp(left, op, right)
        return left

    def additive(self):
        left = self.multiplicative()
        while self.current.kind == "OP" and self.current.value in ("+","-"):
            op = self.current.value
            self.eat("OP")
            right = self.multiplicative()
            left = BinOp(left, op, right)
        return left

    def multiplicative(self):
        left = self.unary()
        while self.current.kind == "OP" and self.current.value in ("*","/"):
            op = self.current.value
            self.eat("OP")
            right = self.unary()
            left = BinOp(left, op, right)
        return left

    def unary(self):
        if self.current.kind == "KEYWORD" and self.current.value == "not":
            self.eat("KEYWORD", "not")
            return NotOp(self.unary())
        return self.factor()

    def factor(self):

        if self.current.kind == "NUMBER":
            value = int(self.current.value)
            self.eat("NUMBER")
            return Number(value)

        if self.current.kind == "STRING":
            value = self.current.value
            self.eat("STRING")
            return TextLiteral(value)

        if self.current.kind == "KEYWORD" and self.current.value in ("true", "false"):
            val = self.current.value == "true"
            self.eat("KEYWORD")
            return BoolLiteral(val)
        # admit input
        if self.current.kind == "KEYWORD" and self.current.value == "admit":
            self.eat("KEYWORD", "admit")
            return ("admit",)
        if self.current.kind == "IDENT":
            name = self.current.value
            self.eat("IDENT")

            if self.current.kind == "SYM" and self.current.value == "(":
                self.eat("SYM", "(")
                args = []

                if not (self.current.kind == "SYM" and self.current.value == ")"):
                    args.append(self.expression())
                    while self.current.kind == "SYM" and self.current.value == ",":
                        self.eat("SYM", ",")
                        args.append(self.expression())

                self.eat("SYM", ")")
                return FuncCall(name, args)

            return Identifier(name)

        if self.current.kind == "SYM" and self.current.value == "(":
            self.eat("SYM", "(")
            expr = self.expression()
            self.eat("SYM", ")")
            return expr

        raise Exception(f"Unexpected token in factor: {self.current}")