# tokens.py
# Token definitions for ANEX language

KEYWORDS = {
    "unit",
    "int",
    "bool",      # ✅ ADD
    "emit",
    "admit",
    "if",
    "else",
    "while",
    "and",
    "or",
    "not",
    "true",      # ✅ ADD
    "false",     # ✅ ADD
    "func",
    "return",
    "text",
}

# Symbols (single-character)
SYMBOLS = {
    "{",
    "}",
    "(",
    ")",
    ";",
    ",",
}

# Operators
OPERATORS = {
    "+", "-", "*", "/",
    "=",
    ">", "<",
    ">=", "<=",
    "==", "!=",
}
