from lexer import Lexer
from parser import Parser
from interpreter import Interpreter

with open("examples/tests.anx") as f:
    source = f.read()

lexer = Lexer(source)
parser = Parser(lexer)
program = parser.parse()



interpreter = Interpreter()
interpreter.run(program)
