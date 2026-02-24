import sys
from src.lexer import Lexer
from src.parser import Parser
from src.interpreter import Interpreter


def run_file(path):
    with open(path, "r") as f:
        source = f.read()

    lexer = Lexer(source)
    parser = Parser(lexer)
    program = parser.parse()

    interpreter = Interpreter()
    interpreter.run(program)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: anex <file.anx>")
        sys.exit(1)

    run_file(sys.argv[1])