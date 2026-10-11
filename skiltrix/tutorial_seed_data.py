"""
Curated original SkilTrix tutorial tracks and lessons.
High quality, conceptual, interactive, and completely original content.
"""

INITIAL_TRACKS = [
    {
        "track_id": "java",
        "title": "Java Programming",
        "category": "languages",
        "icon": "java",
        "description": "Master enterprise Java from basic syntax to object-oriented architecture, collections, streams, and concurrency.",
        "is_featured": True,
        "order": 1,
        "modules": [
            {
                "module_id": "java-intro",
                "title": "Java Introduction & Syntax",
                "level": "beginner",
                "order": 1,
                "description": "Fundamentals of the JVM, compiling Java programs, and basic syntax structure.",
                "lessons": [
                    {
                        "slug": "intro",
                        "title": "Java Introduction & JVM Architecture",
                        "reading_time_minutes": 5,
                        "order": 1,
                        "learning_objectives": [
                            "Understand what Java is and write once, run anywhere (WORA)",
                            "Distinguish between JDK, JRE, and JVM",
                            "Understand how bytecode executes",
                            "Structure a basic Java application"
                        ],
                        "explanation": """### What is Java?
Java is a class-based, object-oriented programming language designed to have as few implementation dependencies as possible. First released by Sun Microsystems in 1995, Java powers enterprise backend systems, Android applications, financial architectures, and high-performance cloud microservices.

### The Write Once, Run Anywhere Principle
When you write Java code (`.java`), the **Java Compiler (`javac`)** converts it into machine-independent **Bytecode (`.class`)**, rather than native CPU instructions. This bytecode runs inside the **Java Virtual Machine (JVM)**, which translates bytecode into optimized native machine code at runtime using the **Just-In-Time (JIT) Compiler**.

### Key Components of the Java Ecosystem
1. **JDK (Java Development Kit)**: The complete toolkit for developers, containing the compiler (`javac`), debugger, and development tools.
2. **JRE (Java Runtime Environment)**: Contains the libraries and runtime needed to execute Java programs (without compiler tools).
3. **JVM (Java Virtual Machine)**: The execution engine that executes bytecode, manages system memory through garbage collection, and provides operating system abstraction.

### Anatomy of a Java Program
Every executable Java program begins inside a class with a `main` method:

```java
public class Main {
    public static void main(String[] args) {
        System.out.println("Welcome to SkilTrix Java!");
    }
}
```

- **`public class Main`**: Defines a publicly accessible class named `Main`. The filename must match the class name (`Main.java`).
- **`public static void main(String[] args)`**: The entry point where program execution begins.
- **`System.out.println(...)`**: Prints the specified text followed by a new line to the console.
""",
                        "syntax_code": "public class ClassName {\n    public static void main(String[] args) {\n        // Code goes here\n    }\n}",
                        "code_examples": [
                            {
                                "title": "First Java Program",
                                "language": "java",
                                "code": "public class Main {\n    public static void main(String[] args) {\n        System.out.println(\"Hello, SkilTrix Learner!\");\n        System.out.println(\"Java runs on JVM.\");\n    }\n}",
                                "explanation": "This demonstrates basic console output using System.out.println.",
                                "output": "Hello, SkilTrix Learner!\nJava runs on JVM."
                            }
                        ],
                        "try_it_yourself": {
                            "task": "Modify the program to print 'Welcome to SkilTrix 2026' on the first line.",
                            "initial_code": "public class Main {\n    public static void main(String[] args) {\n        System.out.println(\"Hello World\");\n    }\n}",
                            "solution_code": "public class Main {\n    public static void main(String[] args) {\n        System.out.println(\"Welcome to SkilTrix 2026\");\n    }\n}",
                            "expected_output": "Welcome to SkilTrix 2026",
                            "hints": ["Replace 'Hello World' with 'Welcome to SkilTrix 2026' inside System.out.println()"],
                            "validation_type": "output_match"
                        },
                        "quiz": {
                            "question": "Which component is responsible for converting Java bytecode into native machine instructions at runtime?",
                            "options": [
                                "Java Compiler (javac)",
                                "Java Virtual Machine (JVM)",
                                "Java Archive (JAR)",
                                "Java Development Kit (JDK) installer"
                            ],
                            "correct_index": 1,
                            "explanation": "The JVM loads the compiled .class bytecode and translates it into native machine code on the host operating system."
                        },
                        "challenge": {
                            "title": "Print Formatted Banner",
                            "difficulty": "Easy",
                            "description": "Write a Java program that prints a two-line welcome banner with asterisk borders.",
                            "initial_code": "public class Main {\n    public static void main(String[] args) {\n        // Your code here\n    }\n}"
                        }
                    },
                    {
                        "slug": "variables",
                        "title": "Java Variables & Data Types",
                        "reading_time_minutes": 6,
                        "order": 2,
                        "learning_objectives": [
                            "Declare and initialize primitive variables in Java",
                            "Understand primitive types: int, double, boolean, char",
                            "Learn how reference types like String differ from primitives",
                            "Apply type casting safely"
                        ],
                        "explanation": """### What is a Variable?
A variable is a named storage location in memory that holds a value during program execution. Java is a **strongly typed** language, meaning every variable must be declared with an explicit data type before it can be used.

### Primitive Data Types in Java
Java includes 8 primitive types:

| Type | Size | Description | Example |
| :--- | :--- | :--- | :--- |
| `byte` | 1 byte | Whole numbers from -128 to 127 | `byte b = 100;` |
| `short` | 2 bytes | Whole numbers from -32,768 to 32,767 | `short s = 5000;` |
| `int` | 4 bytes | Standard integer numbers | `int count = 42;` |
| `long` | 8 bytes | Large integers (suffix with 'L') | `long distance = 9876543210L;` |
| `float` | 4 bytes | Single-precision decimal (suffix with 'f') | `float rate = 3.14f;` |
| `double` | 8 bytes | Double-precision decimal (standard) | `double price = 99.95;` |
| `boolean` | 1 bit | Stores `true` or `false` | `boolean isEnrolled = true;` |
| `char` | 2 bytes | Single Unicode character in single quotes | `char grade = 'A';` |

### Strings (Reference Type)
Strings in Java are not primitives; they are immutable objects of the `java.lang.String` class.

```java
String platform = "SkilTrix";
int lessons = 50;
System.out.println(platform + " offers " + lessons + " lessons.");
```
""",
                        "syntax_code": "dataType variableName = value;",
                        "code_examples": [
                            {
                                "title": "Variable Declaration and Arithmetic",
                                "language": "java",
                                "code": "public class Main {\n    public static void main(String[] args) {\n        int age = 22;\n        double score = 94.5;\n        char grade = 'A';\n        boolean certified = true;\n        String name = \"Ashok\";\n\n        System.out.println(\"Student: \" + name);\n        System.out.println(\"Score: \" + score + \" (Grade \" + grade + \")\");\n        System.out.println(\"Certified: \" + certified);\n    }\n}",
                                "explanation": "Demonstrates declaring primitive and reference variables and printing them.",
                                "output": "Student: Ashok\nScore: 94.5 (Grade A)\nCertified: true"
                            }
                        ],
                        "try_it_yourself": {
                            "task": "Create an integer variable 'targetScore' set to 100 and print 'Target: 100'.",
                            "initial_code": "public class Main {\n    public static void main(String[] args) {\n        // Declare targetScore and print \"Target: \" + targetScore\n    }\n}",
                            "solution_code": "public class Main {\n    public static void main(String[] args) {\n        int targetScore = 100;\n        System.out.println(\"Target: \" + targetScore);\n    }\n}",
                            "expected_output": "Target: 100",
                            "hints": ["Use int targetScore = 100;", "Use System.out.println(\"Target: \" + targetScore);"],
                            "validation_type": "output_match"
                        },
                        "quiz": {
                            "question": "Which Java data type is best suited for storing monetary currency or precise decimal values?",
                            "options": [
                                "int",
                                "double (or BigDecimal for precision)",
                                "char",
                                "short"
                            ],
                            "correct_index": 1,
                            "explanation": "double stores 64-bit floating point numbers. In enterprise finance, BigDecimal is preferred to prevent rounding artifacts."
                        },
                        "challenge": {
                            "title": "Temperature Converter",
                            "difficulty": "Easy",
                            "description": "Convert Celsius to Fahrenheit using the formula F = (C * 9.0/5.0) + 32.",
                            "initial_code": "public class Main {\n    public static void main(String[] args) {\n        double celsius = 25.0;\n        // Calculate and print fahrenheit\n    }\n}"
                        }
                    },
                    {
                        "slug": "control-flow",
                        "title": "Control Flow: If-Else & Switch",
                        "reading_time_minutes": 7,
                        "order": 3,
                        "learning_objectives": [
                            "Use conditional statements (if, else if, else)",
                            "Master comparison and logical operators",
                            "Implement modern switch expressions in Java"
                        ],
                        "explanation": """### Conditional Decision Making
Programs often need to choose different execution paths based on real-time data.

### 1. If-Else Structure
```java
int score = 85;
if (score >= 90) {
    System.out.println("Distinction");
} else if (score >= 75) {
    System.out.println("First Class");
} else {
    System.out.println("Pass");
}
```

### 2. Switch Expressions
In modern Java (Java 14+), switch expressions allow compact pattern matching and arrow syntax without verbose break statements:

```java
int day = 3;
String dayName = switch (day) {
    case 1 -> "Monday";
    case 2 -> "Tuesday";
    case 3 -> "Wednesday";
    default -> "Other day";
};
```
""",
                        "syntax_code": "if (condition) {\n    // block\n} else {\n    // block\n}",
                        "code_examples": [
                            {
                                "title": "Check Eligibility",
                                "language": "java",
                                "code": "public class Main {\n    public static void main(String[] args) {\n        int experienceYears = 3;\n        if (experienceYears >= 2) {\n            System.out.println(\"Eligible for Mid-level Role\");\n        } else {\n            System.out.println(\"Eligible for Junior Role\");\n        }\n    }\n}",
                                "explanation": "Evaluates boolean expression to select execution path.",
                                "output": "Eligible for Mid-level Role"
                            }
                        ],
                        "try_it_yourself": {
                            "task": "Write an if-else check that prints 'Access Granted' if age >= 18, else 'Access Denied'. Set age to 20.",
                            "initial_code": "public class Main {\n    public static void main(String[] args) {\n        int age = 20;\n        // Add if-else here\n    }\n}",
                            "solution_code": "public class Main {\n    public static void main(String[] args) {\n        int age = 20;\n        if (age >= 18) {\n            System.out.println(\"Access Granted\");\n        } else {\n            System.out.println(\"Access Denied\");\n        }\n    }\n}",
                            "expected_output": "Access Granted",
                            "hints": ["Check if (age >= 18) and print 'Access Granted'"],
                            "validation_type": "output_match"
                        },
                        "quiz": {
                            "question": "What happens if a traditional switch case block omits the 'break' keyword?",
                            "options": [
                                "A compilation error occurs",
                                "Execution falls through to subsequent case blocks",
                                "The program halts immediately",
                                "The switch statement repeats"
                            ],
                            "correct_index": 1,
                            "explanation": "Without break (or arrow syntax), control 'falls through' to execute the next case statements regardless of their conditions."
                        },
                        "challenge": {
                            "title": "Grade Calculator",
                            "difficulty": "Easy",
                            "description": "Output letter grade 'A' for >=90, 'B' for >=80, 'C' for >=70, otherwise 'F'.",
                            "initial_code": "public class Main {\n    public static void main(String[] args) {\n        int marks = 82;\n        // Print grade\n    }\n}"
                        }
                    }
                ]
            },
            {
                "module_id": "java-oop",
                "title": "Object-Oriented Programming (OOP)",
                "level": "intermediate",
                "order": 2,
                "description": "Classes, objects, constructors, encapsulation, inheritance, polymorphism, and abstraction.",
                "lessons": [
                    {
                        "slug": "classes-and-objects",
                        "title": "Classes & Objects",
                        "reading_time_minutes": 8,
                        "order": 1,
                        "learning_objectives": [
                            "Define classes with fields and methods",
                            "Instantiate objects on the heap using the 'new' keyword",
                            "Understand reference semantics and constructors"
                        ],
                        "explanation": """### The Object-Oriented Paradigm
Java is fundamentally built on Object-Oriented Programming (OOP). The four pillars of OOP are:
1. **Encapsulation**: Bundling state and behaviors together, protecting data with private fields.
2. **Inheritance**: Reusing code through parent-child class hierarchies (`extends`).
3. **Polymorphism**: The ability of an object to take many forms (method overriding and overloading).
4. **Abstraction**: Hiding internal implementation complexity behind clean interfaces.

### What is a Class vs Object?
- A **Class** is a blueprint or template (e.g., `Car`, `User`, `Account`).
- An **Object** is a concrete instance of that blueprint allocated in memory (e.g., `user1`, `account123`).

```java
public class Developer {
    // Fields (Attributes)
    String name;
    String primaryLanguage;

    // Constructor
    public Developer(String name, String primaryLanguage) {
        this.name = name;
        this.primaryLanguage = primaryLanguage;
    }

    // Method (Behavior)
    public void code() {
        System.out.println(name + " is building with " + primaryLanguage);
    }
}
```
""",
                        "syntax_code": "ClassName objectName = new ClassName();",
                        "code_examples": [
                            {
                                "title": "Instantiating an Object",
                                "language": "java",
                                "code": "class Student {\n    String name;\n    int rollNo;\n\n    Student(String name, int rollNo) {\n        this.name = name;\n        this.rollNo = rollNo;\n    }\n\n    void display() {\n        System.out.println(\"Student: \" + name + \" (ID: \" + rollNo + \")\");\n    }\n}\n\npublic class Main {\n    public static void main(String[] args) {\n        Student s1 = new Student(\"Kiran\", 101);\n        s1.display();\n    }\n}",
                                "explanation": "Defines a Student class and creates an instance with custom constructor parameters.",
                                "output": "Student: Kiran (ID: 101)"
                            }
                        ],
                        "try_it_yourself": {
                            "task": "Create a Book object with title 'Clean Code' and pages 464, then print 'Book: Clean Code, 464 pages'.",
                            "initial_code": "class Book {\n    String title;\n    int pages;\n    Book(String t, int p) {\n        title = t;\n        pages = p;\n    }\n}\n\npublic class Main {\n    public static void main(String[] args) {\n        // Instantiate Book and print\n    }\n}",
                            "solution_code": "class Book {\n    String title;\n    int pages;\n    Book(String t, int p) {\n        title = t;\n        pages = p;\n    }\n}\n\npublic class Main {\n    public static void main(String[] args) {\n        Book b = new Book(\"Clean Code\", 464);\n        System.out.println(\"Book: \" + b.title + \", \" + b.pages + \" pages\");\n    }\n}",
                            "expected_output": "Book: Clean Code, 464 pages",
                            "hints": ["Use new Book(\"Clean Code\", 464)", "Access b.title and b.pages"],
                            "validation_type": "output_match"
                        },
                        "quiz": {
                            "question": "Where are Java objects stored during execution?",
                            "options": [
                                "The Call Stack",
                                "The Heap Memory",
                                "The CPU Registers",
                                "Hard Drive disk cache"
                            ],
                            "correct_index": 1,
                            "explanation": "All Java objects are allocated dynamically on the Heap, while local variable references reside on the Stack."
                        },
                        "challenge": {
                            "title": "Bank Account Class",
                            "difficulty": "Medium",
                            "description": "Design a BankAccount class with deposit(double amount) and getBalance() methods.",
                            "initial_code": "class BankAccount {\n    private double balance = 0;\n    // implement deposit and getBalance\n}\n\npublic class Main {\n    public static void main(String[] args) {\n        // test account\n    }\n}"
                        }
                    }
                ]
            }
        ]
    },
    {
        "track_id": "python",
        "title": "Python Programming",
        "category": "languages",
        "icon": "python",
        "description": "Master clean Pythonic code, data structures, list comprehensions, decorators, and modern backend development.",
        "is_featured": True,
        "order": 2,
        "modules": [
            {
                "module_id": "python-basics",
                "title": "Python Basics & Syntax",
                "level": "beginner",
                "order": 1,
                "description": "Dynamic typing, indentation rules, control flow, functions, and standard libraries.",
                "lessons": [
                    {
                        "slug": "intro",
                        "title": "Python Introduction & Philosophy",
                        "reading_time_minutes": 4,
                        "order": 1,
                        "learning_objectives": [
                            "Understand the Python philosophy (The Zen of Python)",
                            "Learn how Python bytecode and interpreter work",
                            "Write clean, readable Python code"
                        ],
                        "explanation": """### Why Python?
Python is a high-level, interpreted, dynamically typed programming language known for its clear, expressive syntax. Created by Guido van Rossum in 1991, Python emphasizes readability and rapid developer productivity.

### Key Philosophy (PEP 20: The Zen of Python)
- Beautiful is better than ugly.
- Explicit is better than implicit.
- Simple is better than complex.
- Readability counts.

### Indentation as Syntax
Unlike languages that use curly braces `{}` to delimit code blocks, Python uses whitespace indentation. Consistent indentation (4 spaces per level) defines blocks of code.
""",
                        "syntax_code": "print(\"Hello, World!\")",
                        "code_examples": [
                            {
                                "title": "Hello SkilTrix Python",
                                "language": "python",
                                "code": "# Welcome to SkilTrix Python\ndef greet(name):\n    return f\"Hello, {name}! Welcome to SkilTrix.\"\n\nprint(greet(\"Dev\"))",
                                "explanation": "Defines a function with an f-string and prints output.",
                                "output": "Hello, Dev! Welcome to SkilTrix."
                            }
                        ],
                        "try_it_yourself": {
                            "task": "Print 'Python is fun with SkilTrix!' using print().",
                            "initial_code": "# Print message here\n",
                            "solution_code": "print('Python is fun with SkilTrix!')\n",
                            "expected_output": "Python is fun with SkilTrix!",
                            "hints": ["Use print('Python is fun with SkilTrix!')"],
                            "validation_type": "output_match"
                        },
                        "quiz": {
                            "question": "What character is used to indicate a single-line comment in Python?",
                            "options": [
                                "//",
                                "/*",
                                "#",
                                "--"
                            ],
                            "correct_index": 2,
                            "explanation": "In Python, the hash '#' symbol begins a single-line comment."
                        },
                        "challenge": {
                            "title": "Sum of Evens",
                            "difficulty": "Easy",
                            "description": "Calculate the sum of all even numbers from 1 to 20.",
                            "initial_code": "# Calculate sum of evens 1 to 20\n"
                        }
                    },
                    {
                        "slug": "data-structures",
                        "title": "Lists, Tuples, Dictionaries & Sets",
                        "reading_time_minutes": 7,
                        "order": 2,
                        "learning_objectives": [
                            "Master Python lists and indexing",
                            "Understand immutable tuples",
                            "Work with key-value dictionaries and hash sets"
                        ],
                        "explanation": """### Core Python Collections
Python includes four powerful built-in collection data types:

1. **List (`[]`)**: Ordered, mutable, allows duplicate items.
2. **Tuple (`()`)**: Ordered, **immutable**, allows duplicate items.
3. **Dictionary (`{}`)**: Key-value pairs, fast O(1) hash lookup, keys must be hashable.
4. **Set (`{}`)**: Unordered collection of unique items, performs fast membership testing.

```python
# List comprehension
squares = [x**2 for x in range(5)]  # [0, 1, 4, 9, 16]

# Dictionary
user = {"name": "Ashok", "role": "Architect", "active": True}
print(user.get("role"))
```
""",
                        "syntax_code": "my_list = [1, 2, 3]\nmy_dict = {\"key\": \"value\"}",
                        "code_examples": [
                            {
                                "title": "List and Dict Manipulation",
                                "language": "python",
                                "code": "frameworks = [\"Django\", \"FastAPI\", \"Flask\"]\nframeworks.append(\"Tornado\")\n\ninfo = {\"language\": \"Python\", \"tools\": frameworks}\nprint(f\"{info['language']} backend tools: {', '.join(info['tools'])}\")",
                                "explanation": "Demonstrates appending to a list and embedding within a dictionary.",
                                "output": "Python backend tools: Django, FastAPI, Flask, Tornado"
                            }
                        ],
                        "try_it_yourself": {
                            "task": "Create a list of 3 colors ['red', 'green', 'blue'] and print the second item.",
                            "initial_code": "# Create list and print second element\n",
                            "solution_code": "colors = ['red', 'green', 'blue']\nprint(colors[1])\n",
                            "expected_output": "green",
                            "hints": ["Remember Python uses 0-based indexing: colors[1] is the second element."],
                            "validation_type": "output_match"
                        },
                        "quiz": {
                            "question": "Which Python data structure is immutable once created?",
                            "options": [
                                "List",
                                "Dictionary",
                                "Tuple",
                                "Set"
                            ],
                            "correct_index": 2,
                            "explanation": "Tuples cannot be modified (added to, removed from, or changed) after instantiation."
                        },
                        "challenge": {
                            "title": "Word Frequency Counter",
                            "difficulty": "Medium",
                            "description": "Count the frequency of each word in a string using a dictionary.",
                            "initial_code": "text = 'apple banana apple orange banana apple'\n# Count word frequencies\n"
                        }
                    }
                ]
            }
        ]
    },
    {
        "track_id": "javascript",
        "title": "JavaScript (ES6+)",
        "category": "languages",
        "icon": "javascript",
        "description": "The language of the web. Learn modern asynchronous JavaScript, closures, DOM, promises, and modular development.",
        "is_featured": True,
        "order": 3,
        "modules": [
            {
                "module_id": "js-essentials",
                "title": "Modern JavaScript Essentials",
                "level": "beginner",
                "order": 1,
                "description": "ES6+ syntax, let/const, arrow functions, template literals, and destructuring.",
                "lessons": [
                    {
                        "slug": "variables-and-scope",
                        "title": "Variables, Scope & Arrow Functions",
                        "reading_time_minutes": 5,
                        "order": 1,
                        "learning_objectives": [
                            "Distinguish between let, const, and var",
                            "Understand block scope vs function scope",
                            "Write clean arrow functions and template literals"
                        ],
                        "explanation": """### Modern JavaScript Declarations
Before ES2015 (ES6), variables were declared solely with `var`, which has function scope and gets hoisted. In modern JavaScript:

- **`const`**: Block-scoped, cannot be reassigned. Use by default.
- **`let`**: Block-scoped, can be reassigned. Use when values change.
- Avoid `var` in modern development.

### Arrow Functions
Arrow functions provide a concise syntax and lexically bind the `this` value:

```javascript
// Traditional function
function add(a, b) {
    return a + b;
}

// Arrow function
const add = (a, b) => a + b;
```
""",
                        "syntax_code": "const name = 'SkilTrix';\nlet count = 0;",
                        "code_examples": [
                            {
                                "title": "ES6 Features Demo",
                                "language": "javascript",
                                "code": "const users = [\n  { name: 'Kiran', score: 92 },\n  { name: 'Pooja', score: 88 }\n];\n\nconst highScorers = users\n  .filter(u => u.score > 90)\n  .map(u => `${u.name} scored ${u.score}%`);\n\nconsole.log(highScorers.join(', '));",
                                "explanation": "Demonstrates filter, map, arrow functions, and template literals.",
                                "output": "Kiran scored 92%"
                            }
                        ],
                        "try_it_yourself": {
                            "task": "Create an arrow function `double` that multiplies a number by 2 and print `double(7)`.",
                            "initial_code": "// Define double arrow function and log double(7)\n",
                            "solution_code": "const double = n => n * 2;\nconsole.log(double(7));\n",
                            "expected_output": "14",
                            "hints": ["const double = (n) => n * 2;", "console.log(double(7));"],
                            "validation_type": "output_match"
                        },
                        "quiz": {
                            "question": "What is the scope of a variable declared with 'let' inside a for-loop?",
                            "options": [
                                "Global scope",
                                "The block scope of the loop body",
                                "Function scope only",
                                "Module root scope"
                            ],
                            "correct_index": 1,
                            "explanation": "let is block-scoped, so it exists only inside the enclosing curly braces { } of the loop."
                        },
                        "challenge": {
                            "title": "Array Flattening",
                            "difficulty": "Easy",
                            "description": "Flatten an array of nested arrays using array methods.",
                            "initial_code": "const nested = [[1, 2], [3, 4], [5]];\n// Log flattened array\n"
                        }
                    }
                ]
            }
        ]
    },
    {
        "track_id": "react",
        "title": "React 19 & Web Architecture",
        "category": "web",
        "icon": "react",
        "description": "Component architecture, hooks (useState, useEffect, useMemo), custom hooks, routing, and state management.",
        "is_featured": True,
        "order": 4,
        "modules": [
            {
                "module_id": "react-hooks",
                "title": "React Components & Hooks",
                "level": "intermediate",
                "order": 1,
                "description": "Functional components, JSX, hooks lifecycle, and component composition.",
                "lessons": [
                    {
                        "slug": "hooks-and-state",
                        "title": "React State & Lifecycle with Hooks",
                        "reading_time_minutes": 6,
                        "order": 1,
                        "learning_objectives": [
                            "Understand declarative UI rendering",
                            "Manage local component state with useState",
                            "Perform side-effects with useEffect"
                        ],
                        "explanation": """### The React Philosophy
React treats UI as a pure function of state: `UI = f(State)`. When state changes, React recalculates the virtual DOM and efficiently patches only the changed real DOM nodes.

### useState Hook
```jsx
import { useState } from 'react';

function Counter() {
    const [count, setCount] = useState(0);
    return (
        <button onClick={() => setCount(c => c + 1)}>
            Clicked {count} times
        </button>
    );
}
```
""",
                        "syntax_code": "const [state, setState] = useState(initialValue);",
                        "code_examples": [
                            {
                                "title": "React Component Concept",
                                "language": "javascript",
                                "code": "function createCounter(initial = 0) {\n  let count = initial;\n  return {\n    increment: () => ++count,\n    get: () => count\n  };\n}\nconst counter = createCounter(10);\nconsole.log('Count:', counter.increment());",
                                "explanation": "Demonstrates closure-based state encapsulation mirroring React hooks.",
                                "output": "Count: 11"
                            }
                        ],
                        "try_it_yourself": {
                            "task": "Create a function `formatBadge` that returns `[SkilTrix Certified]` and print it.",
                            "initial_code": "// Define formatBadge and print result\n",
                            "solution_code": "function formatBadge() {\n  return '[SkilTrix Certified]';\n}\nconsole.log(formatBadge());\n",
                            "expected_output": "[SkilTrix Certified]",
                            "hints": ["Return string '[SkilTrix Certified]'"],
                            "validation_type": "output_match"
                        },
                        "quiz": {
                            "question": "Why should you never mutate React state directly (e.g. state.count = 5)?",
                            "options": [
                                "JavaScript will throw a syntax error",
                                "React cannot detect mutations without setter functions, so it will not re-render",
                                "The browser memory leaks immediately",
                                "It converts state into a string"
                            ],
                            "correct_index": 1,
                            "explanation": "React relies on referential equality and setter functions to schedule reconciliation and re-render the view."
                        },
                        "challenge": {
                            "title": "Custom Toggle Hook Logic",
                            "difficulty": "Easy",
                            "description": "Implement a boolean toggle state machine function.",
                            "initial_code": "// Implement toggle logic\n"
                        }
                    }
                ]
            }
        ]
    },
    {
        "track_id": "sql",
        "title": "SQL & Relational Databases",
        "category": "databases",
        "icon": "sql",
        "description": "Querying, joins, indexing, normalization, transactions, window functions, and performance tuning.",
        "is_featured": True,
        "order": 5,
        "modules": [
            {
                "module_id": "sql-queries",
                "title": "SQL Queries & Aggregations",
                "level": "beginner",
                "order": 1,
                "description": "SELECT, WHERE, GROUP BY, HAVING, and JOIN queries.",
                "lessons": [
                    {
                        "slug": "select-and-joins",
                        "title": "SQL Queries & Relational Joins",
                        "reading_time_minutes": 6,
                        "order": 1,
                        "learning_objectives": [
                            "Filter data with SELECT and WHERE clauses",
                            "Perform INNER, LEFT, and RIGHT joins",
                            "Aggregate rows using COUNT, SUM, AVG and GROUP BY"
                        ],
                        "explanation": """### Relational Algebra in SQL
Structured Query Language (SQL) is a declarative language for managing structured relational data.

### Types of JOINs
- **INNER JOIN**: Returns rows where there is a match in both tables.
- **LEFT JOIN**: Returns all rows from the left table, and matching rows from the right table (with NULL for missing rows).
- **RIGHT JOIN**: Returns all rows from the right table.
- **FULL OUTER JOIN**: Returns rows when there is a match in either table.

```sql
SELECT 
    users.name,
    COUNT(orders.id) AS total_orders
FROM users
LEFT JOIN orders ON users.id = orders.user_id
GROUP BY users.id, users.name
HAVING COUNT(orders.id) > 2;
```
""",
                        "syntax_code": "SELECT col1, col2 FROM table_name WHERE condition;",
                        "code_examples": [
                            {
                                "title": "SQL Query Example",
                                "language": "sql",
                                "code": "SELECT 'SkilTrix' AS platform, 2026 AS current_year, 'Active' AS status;",
                                "explanation": "Basic relational row generation.",
                                "output": "+----------+--------------+--------+\n| platform | current_year | status |\n+----------+--------------+--------+\n| SkilTrix |         2026 | Active |\n+----------+--------------+--------+"
                            }
                        ],
                        "try_it_yourself": {
                            "task": "Write an SQL query that selects the text 'Hello SkilTrix SQL' as greeting.",
                            "initial_code": "-- Write query here\n",
                            "solution_code": "SELECT 'Hello SkilTrix SQL' AS greeting;\n",
                            "expected_output": "Hello SkilTrix SQL",
                            "hints": ["SELECT 'Hello SkilTrix SQL' AS greeting;"],
                            "validation_type": "output_match"
                        },
                        "quiz": {
                            "question": "Which SQL clause is used to filter aggregated grouped results?",
                            "options": [
                                "WHERE",
                                "HAVING",
                                "GROUP BY",
                                "ORDER BY"
                            ],
                            "correct_index": 1,
                            "explanation": "WHERE filters rows before grouping; HAVING filters the groups produced by GROUP BY."
                        },
                        "challenge": {
                            "title": "Find Top Spenders",
                            "difficulty": "Easy",
                            "description": "Write a query to list customers whose total spending exceeds $1000.",
                            "initial_code": "-- Write query\n"
                        }
                    }
                ]
            }
        ]
    }
]

