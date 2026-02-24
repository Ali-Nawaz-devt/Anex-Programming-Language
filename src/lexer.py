# lexer.py
# Lexical analyzer for ANEX

from src.tokens import KEYWORDS, SYMBOLS, OPERATORS


class Token:
    def __init__(self, kind, value, line):
        self.kind = kind
        self.value = value
        self.line = line

    def __repr__(self):
        return f"{self.kind}({self.value})"


class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1

    def current_char(self):
        if self.pos >= len(self.source):
            return None
        return self.source[self.pos]

    def advance(self):
        if self.current_char() == "\n":
            self.line += 1
        self.pos += 1

    def skip_whitespace(self):
        while True:
            ch = self.current_char()
            if ch is None or not ch.isspace():
                break
            self.advance()

    def read_identifier(self):
        start = self.pos  # ✅ FIX: define start
        while True:
            ch = self.current_char()
            if ch is None or not (ch.isalnum() or ch == "_"):
                break
            self.advance()

        value = self.source[start:self.pos]
        kind = "KEYWORD" if value in KEYWORDS else "IDENT"
        return Token(kind, value, self.line)

    def read_number(self):
        start = self.pos  # ✅ FIX: define start
        while True:
            ch = self.current_char()
            if ch is None or not ch.isdigit():
                break
            self.advance()

        value = int(self.source[start:self.pos])
        return Token("NUMBER", value, self.line)

    def get_next_token(self):
        self.skip_whitespace()

        ch = self.current_char()

        if ch is None:
            return Token("EOF", None, self.line)
        if ch == '"':
            return self.read_string()
        
        if ch.isalpha() or ch == "_":
            return self.read_identifier()

        if ch.isdigit():
            return self.read_number()

              # Operators (handle multi-character first)
        next_ch = None
        if self.pos + 1 < len(self.source):
            next_ch = self.source[self.pos + 1]

        # Two-character operators
        if next_ch and (ch + next_ch) in OPERATORS:
            op = ch + next_ch
            self.advance()
            self.advance()
            return Token("OP", op, self.line)

        # Single-character operators
        if ch in OPERATORS:
            self.advance()
            return Token("OP", ch, self.line)

        if ch in SYMBOLS:
            self.advance()
            return Token("SYM", ch, self.line)

        raise Exception(f"Unexpected character '{ch}' at line {self.line}")
    def read_string(self):
        # skip opening quote
        self.advance()

        start = self.pos
        while True:
            ch = self.current_char()
            if ch is None:
                raise Exception("Unterminated string literal")
            if ch == '"':
                break
            self.advance()

        value = self.source[start:self.pos]
        self.advance()  # skip closing quote
        return Token("STRING", value, self.line)
