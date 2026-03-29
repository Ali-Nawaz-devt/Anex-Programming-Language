
<div align="center">

```
 █████╗ ███╗   ██╗███████╗██╗  ██╗
██╔══██╗████╗  ██║██╔════╝╚██╗██╔╝
███████║██╔██╗ ██║█████╗   ╚███╔╝ 
██╔══██║██║╚██╗██║██╔══╝   ██╔██╗ 
██║  ██║██║ ╚████║███████╗██╔╝ ██╗
╚═╝  ╚═╝╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝
```

**A custom programming language and full visual compiler debugger — built from scratch in Python.**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-00ffaa?style=for-the-badge)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Active-ff3d96?style=for-the-badge)]()
[![Course](https://img.shields.io/badge/Course-Compiler_Construction-aa44ff?style=for-the-badge)]()

</div>

---

## What is ANEX?

ANEX is a fully custom programming language designed and implemented from scratch in Python — complete with a **visual compiler debugger** that lets you watch every stage of the compiler pipeline happen live, in real time, as your program runs.

Most people learn to *write* code. ANEX lets you *see* how code is actually read, parsed, executed, and compiled — from raw text all the way down to pseudo-assembly output.

> Built as a Compiler Construction course project.  
> Every stage in your textbook — implemented, visualized, and interactive.

---

## The Pipeline — 9 Stages, One Screen

```
Source Code  -->  Lexer  -->  Parser  -->  Interpreter  -->  Symbol Table
                                                  |
                                         Semantic Analysis
                                                  |
                                            Optimizer
                                                  |
                                         Code Generation
                                                  |
                                              Output
```

| # | Stage | What It Does |
|---|-------|-------------|
| 1 | **Source Code** | Write ANEX programs in the built-in editor with syntax highlighting |
| 2 | **Lexer** | Breaks source into typed tokens — KEYWORD, NUMBER, STRING, OP, SYM, IDENT |
| 3 | **Parser + AST** | Builds an interactive Abstract Syntax Tree — click any node to collapse |
| 4 | **Interpreter** | Walks the AST and traces every step of execution, live |
| 5 | **Symbol Table** | Tracks every variable (name, type, scope, value, update count) and function (params, call count, return value) |
| 6 | **Semantic Analysis** | Catches type mismatches, undeclared variables, duplicate declarations, and argument count errors — with fix suggestions |
| 7 | **Optimizer** | Applies constant folding, dead code elimination, identity elimination, and strength reduction — shows before/after |
| 8 | **Code Generation** | Translates your program into Three-Address Code and Pseudo-Assembly — split-pane view |
| 9 | **Output** | Every `emit()` statement rendered cleanly |

---

## The ANEX Language

ANEX is a statically-typed, interpreted language with clean, readable syntax.

### Data Types

```anex
int    x = 10;
bool   flag = true;
string name = "ANEX";
```

### Conditionals

```anex
if result > 12 {
    emit("Big result!");
} else {
    emit("Small result.");
}
```

### Loops

```anex
int i = 1;
while i <= 5 {
    emit(i);
    i = i + 1;
}
```

### Functions + Recursion

```anex
unit Main {
    func factorial(n) {
        if n <= 1 {
            return 1;
        }
        return n * factorial(n - 1);
    }

    int result = factorial(7);
    emit("7! =");
    emit(result);
}
```

### Logical Operators

```anex
bool a = true;
bool b = false;

emit(a and b);    // false
emit(a or b);     // true
emit(not a);      // false
emit(x > 10 and x < 20);
```

### Output

```anex
emit("Hello, ANEX!");
emit(result);
```

---

## Visual Debugger Interface

The debugger is built with Python + customtkinter and features:

- **Two-panel layout** — code editor on the left, analysis panels on the right
- **Tab-based navigation** — switch between all 9 pipeline stages instantly
- **Live pipeline indicator** — glowing dots show which stage just completed
- **Real-time stats bar** — token count, AST nodes, execution steps, variables, output lines, and runtime in ms
- **VS Code-style editor** — syntax highlighting, line numbers, collapsible editor panel (Ctrl+B)
- **Keyboard shortcuts** — `Ctrl+Enter` to run, `Ctrl+B` to toggle editor
- **Live clock** — always visible in the top bar
- **Status bar** — shows exactly what the pipeline is doing at every moment
- **Built-in examples** — Hello World, Factorial, Fibonacci, While Loop, Functions, Logic

---

## Getting Started

### Prerequisites

```bash
pip install customtkinter
```

### Installation

```bash
git clone https://github.com/Ali-Nawaz-devt/Anex-Programming-Language.git
cd Anex-Programming-Language
```

### Run the Visual Debugger

```bash
python gui.py
```

### Run an ANEX file directly

```bash
python anex.py program.anx
```

---

## Project Structure

```
Anex-Programming-Language/
│
├── gui.py                  # Visual compiler debugger (main interface)
├── anex.py                 # CLI runner for .anx files
│
└── src/
    ├── lexer.py            # Lexical analyser — source to tokens
    ├── parser.py           # Parser — tokens to AST
    ├── interpreter.py      # Interpreter — AST execution
    ├── anex_ast.py         # AST node definitions
    └── tokens.py           # Token types and keywords
```

---

## Example Programs

### Fibonacci Sequence

```anex
unit Main {
    func fib(n) {
        if n <= 1 {
            return n;
        }
        return fib(n - 1) + fib(n - 2);
    }

    int i = 0;
    while i <= 9 {
        emit(fib(i));
        i = i + 1;
    }
}
```

### Logic Operations

```anex
unit Main {
    bool a = true;
    bool b = false;
    int  x = 15;

    emit(a and b);
    emit(a or b);
    emit(not a);
    emit(x > 10 and x < 20);
    emit(x == 15);
}
```

---

## What the Optimizer Catches

| Optimization | Before | After |
|---|---|---|
| Constant Folding | `int x = 2 + 3` | `int x = 5` |
| Dead Code Elimination | `if false { ... }` | block removed |
| Identity Elimination | `x = x + 0` | `x = x` |
| Strength Reduction | `y = n * 0` | `y = 0` |

---

## What the Code Generator Produces

**Three-Address Code (TAC)**
```
BEGIN  Main
  t1  =  x
  t2  =  y
  t3  =  t1  +  t2
  result  =  t3
  if t4 goto THEN1 else goto ELSE1
THEN1:
  PRINT "Big result!"
  goto ENDIF1
ELSE1:
  PRINT "Small result."
ENDIF1:
END
```

**Pseudo-Assembly**
```
  LOAD   [x],  R1
  LOAD   [y],  R2
  ADD    R1,   R2,   R3
  STORE  R3,   [result]
  CMP    R4,   #true
  JEQ    THEN1
  JMP    ELSE1
```

---

## Built With

| Technology | Purpose |
|---|---|
| Python 3.10+ | Core language |
| customtkinter | GUI framework |
| tkinter Canvas | AST tree renderer |
| Threading | Non-blocking pipeline execution |
| Regex | Syntax highlighting |

---

## Why I Built This

Most developers use languages every day without ever understanding how they actually work.

I wanted to change that — for myself first.

Building ANEX forced me to understand every layer of a programming language from the ground up: how raw text becomes tokens, how tokens become structure, how structure becomes execution, and how execution can be optimized and compiled down to machine-level instructions.

Every stage you see in the debugger is something I implemented myself — the lexer, the parser, the interpreter, the symbol table, the semantic analyser, the optimizer, and the code generator.

This is what compiler construction actually looks like in practice.

---

## Author

**Ali Nawaz**  
BS Computer Science  
The Shaikh Ayaz University  

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/ali-nawaz-786w?utm_source=share_via&utm_content=profile&utm_medium=member_android)
[![GitHub](https://img.shields.io/badge/GitHub-Follow-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/Ali-Nawaz-devt)

---

<div align="center">

*If you find this project interesting, give it a star — it helps more people discover it.*

**Built with curiosity. Powered by Python. Driven by the need to understand.**

</div>
