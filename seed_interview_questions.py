import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'apis.settings')
django.setup()

from skiltrix.models import InterviewCategories, InterviewQuestions

CATEGORIES_DATA = [
    {"category_id": "cat_python", "name": "Python", "icon": "python"},
    {"category_id": "cat_javascript", "name": "JavaScript", "icon": "javascript"},
    {"category_id": "cat_java", "name": "Java", "icon": "java"},
    {"category_id": "cat_sql", "name": "SQL", "icon": "sql"},
    {"category_id": "cat_dsa", "name": "DSA", "icon": "dsa"},
    {"category_id": "cat_html_css", "name": "HTML & CSS", "icon": "html"},
    {"category_id": "cat_react", "name": "React", "icon": "react"},
    {"category_id": "cat_django", "name": "Django", "icon": "django"},
    {"category_id": "cat_abap", "name": "SAP ABAP", "icon": "code"},
]

QUESTIONS_DATA = [
    # ── PYTHON ──────────────────────────────────────────────────────────
    {
        "interview_id": "iq_py_01",
        "category_id": "cat_python",
        "topic": "Python",
        "difficulty": "Common",
        "question": "What is the difference between a List and a Tuple in Python?",
        "short_answer": "Lists are mutable (modifiable after creation) and defined with square brackets `[]`, whereas Tuples are immutable (cannot be changed) and defined with parentheses `()`.",
        "explanation": "Because tuples are immutable, they are stored in a single contiguous memory block and consume less memory than lists. Tuples can also be used as dictionary keys if all their elements are hashable, whereas lists can never be dictionary keys.",
        "code": "# List (mutable)\nmy_list = [1, 2, 3]\nmy_list.append(4)\nmy_list[0] = 99\nprint('List:', my_list)  # [99, 2, 3, 4]\n\n# Tuple (immutable)\nmy_tuple = (1, 2, 3)\ntry:\n    my_tuple[0] = 99  # Raises TypeError\nexcept TypeError as e:\n    print('Tuple error:', e)\n",
        "language": "python",
        "tags": ["Python", "Lists", "Tuples", "Data Structures", "Basics"],
        "frequent_companies": ["TCS", "Infosys", "Wipro", "Amazon", "Cognizant"]
    },
    {
        "interview_id": "iq_py_02",
        "category_id": "cat_python",
        "topic": "Python",
        "difficulty": "Common",
        "question": "Explain mutable vs immutable data types in Python with examples.",
        "short_answer": "Mutable objects can have their values changed in place without changing their memory ID, while immutable objects cannot be modified after creation—modifying them creates a new object in memory.",
        "explanation": "Mutable types: list, dict, set, bytearray. Immutable types: int, float, str, tuple, frozenset, bool. When passing arguments to functions, Python uses 'pass by object reference', meaning mutating a mutable object impacts the caller, while reassigning an immutable object does not.",
        "code": "# Immutable example\ns = 'hello'\nprint(id(s))\ns += ' world'  # Creates new string in memory\nprint(id(s))   # Different ID\n\n# Mutable example\nlst = [1, 2]\nprint(id(lst))\nlst.append(3)  # Modified in place\nprint(id(lst)) # Same ID\n",
        "language": "python",
        "tags": ["Python", "Memory", "Immutability", "Basics"],
        "frequent_companies": ["Accenture", "Capgemini", "Google", "Microsoft"]
    },
    {
        "interview_id": "iq_py_03",
        "category_id": "cat_python",
        "topic": "Python",
        "difficulty": "Common",
        "question": "What is the difference between shallow copy and deep copy in Python?",
        "short_answer": "A shallow copy creates a new collection object, but inserts references into it to the objects in the original. A deep copy recursively duplicates both the collection and every object contained within it.",
        "explanation": "If a nested object inside a shallow copy is modified, that change reflects in the original object because both point to the same child memory address. The `copy` module provides `copy.copy()` for shallow copies and `copy.deepcopy()` for deep copies.",
        "code": "import copy\n\noriginal = [[1, 2, 3], [4, 5, 6]]\n\n# Shallow copy\nshallow = copy.copy(original)\nshallow[0][0] = 999\nprint('Original after shallow mutation:', original[0])  # [999, 2, 3]! Shared!\n\n# Deep copy\ndeep = copy.deepcopy(original)\ndeep[0][0] = 42\nprint('Original after deep mutation:', original[0])     # [999, 2, 3] Untouched!\n",
        "language": "python",
        "tags": ["Python", "Copy", "Memory", "Object References"],
        "frequent_companies": ["Amazon", "Flipkart", "Oracle", "Cisco"]
    },
    {
        "interview_id": "iq_py_04",
        "category_id": "cat_python",
        "topic": "Python",
        "difficulty": "Common",
        "question": "What are *args and **kwargs in Python function definitions?",
        "short_answer": "`*args` allows a function to accept any number of positional arguments as a tuple, while `**kwargs` allows passing any number of keyword (named) arguments as a dictionary.",
        "explanation": "The asterisk symbols `*` and `**` are the actual operators (unpacking syntax); the names `args` and `kwargs` are conventions. Positional arguments must appear before `*args`, which in turn must appear before `**kwargs` in standard function signatures.",
        "code": "def show_details(*args, **kwargs):\n    print('Positional args (tuple):', args)\n    print('Keyword args (dict):', kwargs)\n\nshow_details(10, 20, 30, name='Ashok', role='Architect')\n# Output:\n# Positional args (tuple): (10, 20, 30)\n# Keyword args (dict): {'name': 'Ashok', 'role': 'Architect'}\n",
        "language": "python",
        "tags": ["Python", "Functions", "Syntax", "Arguments"],
        "frequent_companies": ["TCS", "HCL", "IBM", "Zoho"]
    },
    {
        "interview_id": "iq_py_05",
        "category_id": "cat_python",
        "topic": "Python",
        "difficulty": "Intermediate",
        "question": "What are Generators and the `yield` keyword in Python?",
        "short_answer": "Generators are functions that return an iterator which generates values on-the-fly using `yield` instead of returning all elements in memory at once with `return`.",
        "explanation": "When a generator function calls `yield`, its execution state (variables and instruction pointer) is paused and saved. Subsequent calls to `next()` resume execution right after the yield statement. This allows processing massive datasets without running out of RAM (lazy evaluation).",
        "code": "def count_up_to(max_val):\n    count = 1\n    while count <= max_val:\n        yield count\n        count += 1\n\ncounter = count_up_to(3)\nprint(next(counter))  # 1\nprint(next(counter))  # 2\nprint(next(counter))  # 3\n",
        "language": "python",
        "tags": ["Python", "Generators", "Memory Optimization", "Yield"],
        "frequent_companies": ["Google", "Meta", "Adobe", "Uber"]
    },

    # ── JAVASCRIPT ──────────────────────────────────────────────────────
    {
        "interview_id": "iq_js_01",
        "category_id": "cat_javascript",
        "topic": "JavaScript",
        "difficulty": "Common",
        "question": "What is the difference between `var`, `let`, and `const`?",
        "short_answer": "`var` is function-scoped and hoisted with `undefined`. `let` and `const` are block-scoped and live in the Temporal Dead Zone (TDZ) before declaration; `const` cannot be reassigned.",
        "explanation": "`var` declarations leak outside if-statements and loops, often causing unexpected bugs. `let` and `const` respect block boundaries `{}`. Although `const` primitives cannot be reassigned, properties of a `const` object or elements of an array can still be mutated.",
        "code": "function scopeExample() {\n  if (true) {\n    var x = 'var visible outside block';\n    let y = 'let block scoped';\n    const z = 42;\n  }\n  console.log(x); // 'var visible outside block'\n  // console.log(y); // ReferenceError: y is not defined\n}\nscopeExample();\n",
        "language": "javascript",
        "tags": ["JavaScript", "Variables", "Scope", "ES6"],
        "frequent_companies": ["Microsoft", "Paytm", "Zoho", "Swiggy"]
    },
    {
        "interview_id": "iq_js_02",
        "category_id": "cat_javascript",
        "topic": "JavaScript",
        "difficulty": "Common",
        "question": "What is a Closure in JavaScript?",
        "short_answer": "A closure is a function bundled together with references to its surrounding lexical environment, allowing an inner function to access an outer function's scope even after the outer function has returned.",
        "explanation": "Closures enable data privacy (encapsulation), function factories, and memoization. JavaScript keeps the outer variables in memory because the inner function still maintains a reference to them in the heap.",
        "code": "function createCounter() {\n  let count = 0; // Private variable\n  return {\n    increment: () => ++count,\n    decrement: () => --count,\n    getCount: () => count,\n  };\n}\n\nconst counter = createCounter();\nconsole.log(counter.increment()); // 1\nconsole.log(counter.increment()); // 2\nconsole.log(counter.getCount());  // 2 (count cannot be altered directly)\n",
        "language": "javascript",
        "tags": ["JavaScript", "Closures", "Scope", "Functions"],
        "frequent_companies": ["Amazon", "Flipkart", "Atlassian", "Uber"]
    },
    {
        "interview_id": "iq_js_03",
        "category_id": "cat_javascript",
        "topic": "JavaScript",
        "difficulty": "Common",
        "question": "What is the difference between `==` and `===` in JavaScript?",
        "short_answer": "`==` (loose equality) compares two values after performing type coercion, while `===` (strict equality) compares both value and type without converting types.",
        "explanation": "Because `==` performs implicit type coercion according to complex ECMAScript rules (e.g. `0 == false` is true, and `'' == 0` is true), strict equality `===` should always be preferred to prevent subtle equality bugs.",
        "code": "console.log(5 == '5');   // true (string '5' coerced to number 5)\nconsole.log(5 === '5');  // false (number !== string)\n\nconsole.log(null == undefined);  // true\nconsole.log(null === undefined); // false\n",
        "language": "javascript",
        "tags": ["JavaScript", "Operators", "Coercion", "Basics"],
        "frequent_companies": ["TCS", "Infosys", "Wipro", "Tech Mahindra"]
    },
    {
        "interview_id": "iq_js_04",
        "category_id": "cat_javascript",
        "topic": "JavaScript",
        "difficulty": "Intermediate",
        "question": "How does the JavaScript Event Loop work?",
        "short_answer": "JavaScript is single-threaded; the Event Loop continuously monitors the Call Stack and moves callbacks from the Microtask Queue (Promises) and Macrotask Queue (setTimeout) onto the stack when it is empty.",
        "explanation": "Microtasks (Promises, `process.nextTick`, `queueMicrotask`) have higher priority and are completely drained before the next macrotask (`setTimeout`, `setInterval`, I/O events, DOM rendering) is executed from the task queue.",
        "code": "console.log('1: Sync');\n\nsetTimeout(() => {\n  console.log('2: Macrotask (setTimeout)');\n}, 0);\n\nPromise.resolve().then(() => {\n  console.log('3: Microtask (Promise)');\n});\n\nconsole.log('4: Sync');\n\n// Output order: 1 -> 4 -> 3 -> 2\n",
        "language": "javascript",
        "tags": ["JavaScript", "Event Loop", "Asynchronous", "Concurrency"],
        "frequent_companies": ["Google", "Meta", "Netflix", "Razorpay"]
    },
    {
        "interview_id": "iq_js_05",
        "category_id": "cat_javascript",
        "topic": "JavaScript",
        "difficulty": "Common",
        "question": "What is the difference between Promises and Async/Await?",
        "short_answer": "`async/await` is syntactic sugar built on top of Promises that allows writing asynchronous code in a clean, synchronous-looking style with standard `try/catch` error handling.",
        "explanation": "Under the hood, an `async` function always returns a Promise. The `await` keyword pauses execution inside the async function until the Promise resolves or rejects, eliminating deeply nested `.then()` and `.catch()` callback chains.",
        "code": "// Promise syntax\nfetch('/api/user')\n  .then(res => res.json())\n  .then(data => console.log(data))\n  .catch(err => console.error(err));\n\n// Async/Await syntax\nasync function getUser() {\n  try {\n    const res = await fetch('/api/user');\n    const data = await res.json();\n    console.log(data);\n  } catch (err) {\n    console.error(err);\n  }\n}\n",
        "language": "javascript",
        "tags": ["JavaScript", "Promises", "Async Await", "ES8"],
        "frequent_companies": ["Infosys", "Cognizant", "PayPal", "Intuit"]
    },

    # ── JAVA ────────────────────────────────────────────────────────────
    {
        "interview_id": "iq_java_01",
        "category_id": "cat_java",
        "topic": "Java",
        "difficulty": "Common",
        "question": "What are the four fundamental pillars of Object-Oriented Programming in Java?",
        "short_answer": "The four pillars are Encapsulation (data hiding), Inheritance (code reuse), Polymorphism (one interface, multiple forms), and Abstraction (hiding implementation complexity).",
        "explanation": "1. Encapsulation: achieved via private fields and public getters/setters. 2. Inheritance: `extends` keyword to inherit attributes and methods. 3. Polymorphism: compile-time (method overloading) and runtime (method overriding). 4. Abstraction: achieved via abstract classes and interfaces.",
        "code": "// Encapsulation & Abstraction\npublic class BankAccount {\n    private double balance; // Encapsulated\n\n    public BankAccount(double initial) {\n        this.balance = initial;\n    }\n\n    public void deposit(double amount) {\n        if (amount > 0) balance += amount;\n    }\n\n    public double getBalance() {\n        return balance;\n    }\n}\n",
        "language": "java",
        "tags": ["Java", "OOP", "Encapsulation", "Polymorphism", "Basics"],
        "frequent_companies": ["Oracle", "TCS", "Accenture", "JPMorgan", "Morgan Stanley"]
    },
    {
        "interview_id": "iq_java_02",
        "category_id": "cat_java",
        "topic": "Java",
        "difficulty": "Common",
        "question": "What is the difference between String, StringBuilder, and StringBuffer?",
        "short_answer": "`String` is immutable. `StringBuilder` is mutable and non-thread-safe (fastest). `StringBuffer` is mutable and thread-safe (synchronized methods).",
        "explanation": "Every concatenation on a `String` creates a new object in the String Constant Pool. In loops or heavy string modifications, use `StringBuilder` in single-threaded contexts and `StringBuffer` only when multi-thread synchronization across threads is required.",
        "code": "// String: creates multiple objects\nString s = \"Hello\";\ns += \" World\"; // New object in memory\n\n// StringBuilder: modified in place (fastest)\nStringBuilder sb = new StringBuilder(\"Hello\");\nsb.append(\" World\");\nSystem.out.println(sb.toString()); // \"Hello World\"\n",
        "language": "java",
        "tags": ["Java", "String", "Memory", "StringBuilder"],
        "frequent_companies": ["TCS", "Infosys", "Wipro", "Cognizant", "HCL"]
    },
    {
        "interview_id": "iq_java_03",
        "category_id": "cat_java",
        "topic": "Java",
        "difficulty": "Common",
        "question": "What is the difference between `==` and `.equals()` in Java?",
        "short_answer": "`==` compares memory references (addresses) of objects, while `.equals()` is a method meant to compare the actual values (state) of two objects.",
        "explanation": "By default in the `Object` class, `.equals()` uses `==`. Classes like `String`, `Integer`, and `Date` override `.equals()` to compare contents. When overriding `.equals()`, you must also override `.hashCode()` to satisfy the Java Hash contract for collections like `HashMap`.",
        "code": "String s1 = new String(\"test\");\nString s2 = new String(\"test\");\n\nSystem.out.println(s1 == s2);      // false (different heap addresses)\nSystem.out.println(s1.equals(s2)); // true (same character content)\n",
        "language": "java",
        "tags": ["Java", "Equals", "HashCode", "Object Comparison"],
        "frequent_companies": ["Amazon", "Goldman Sachs", "Cisco", "Walmart"]
    },
    {
        "interview_id": "iq_java_04",
        "category_id": "cat_java",
        "topic": "Java",
        "difficulty": "Intermediate",
        "question": "What is the difference between an Abstract Class and an Interface in Java?",
        "short_answer": "An abstract class can have instance fields, constructors, and non-abstract methods, while an interface primarily defines contract methods and constants. A class can implement multiple interfaces but extend only one class.",
        "explanation": "Since Java 8, interfaces can contain `default` and `static` methods with implementations, and Java 9 added `private` methods. Use abstract classes when classes share common code and identity ('is-a'); use interfaces to define a capability ('can-do').",
        "code": "interface Flyable {\n    void fly(); // Abstract\n    default void glide() {\n        System.out.println(\"Gliding through air\");\n    }\n}\n\nabstract class Animal {\n    protected String name;\n    public Animal(String name) { this.name = name; }\n    abstract void makeSound();\n}\n",
        "language": "java",
        "tags": ["Java", "Interfaces", "Abstract Classes", "Design"],
        "frequent_companies": ["Microsoft", "SAP", "Wells Fargo", "Target"]
    },
    {
        "interview_id": "iq_java_05",
        "category_id": "cat_java",
        "topic": "Java",
        "difficulty": "Intermediate",
        "question": "Explain JVM Memory Structure: Stack vs Heap Memory.",
        "short_answer": "Stack memory stores primitive values and references to objects, scoped to function execution threads. Heap memory stores all instantiated objects and JRE classes, shared across all threads.",
        "explanation": "Stack memory is fast, LIFO, and automatically deallocated when a method exits. Heap memory is managed by the Garbage Collector (GC); unreferenced objects in the heap are periodically collected. If heap is full, `OutOfMemoryError` occurs; if stack runs out, `StackOverflowError` occurs.",
        "code": "public void execute() {\n    // 'x' primitive value stored on STACK\n    int x = 10; \n    \n    // 'emp' reference stored on STACK\n    // 'new Employee()' object allocated on HEAP\n    Employee emp = new Employee(\"Ashok\"); \n}\n",
        "language": "java",
        "tags": ["Java", "JVM", "Memory Management", "Garbage Collection"],
        "frequent_companies": ["Amazon", "Oracle", "IBM", "Red Hat"]
    },

    # ── SQL ─────────────────────────────────────────────────────────────
    {
        "interview_id": "iq_sql_01",
        "category_id": "cat_sql",
        "topic": "SQL",
        "difficulty": "Common",
        "question": "What is the difference between WHERE and HAVING clauses in SQL?",
        "short_answer": "`WHERE` filters individual rows before any aggregations occur, whereas `HAVING` filters grouped rows after `GROUP BY` aggregation has been computed.",
        "explanation": "You cannot use aggregate functions (like `SUM()`, `AVG()`, `COUNT()`) inside a `WHERE` clause because aggregation has not taken place yet. `HAVING` was introduced specifically to filter aggregated records.",
        "code": "-- Filter rows before grouping (WHERE)\n-- and filter grouped groups (HAVING)\nSELECT department, COUNT(*) AS emp_count, AVG(salary) AS avg_sal\nFROM employees\nWHERE status = 'Active'\nGROUP BY department\nHAVING AVG(salary) > 60000;\n",
        "language": "sql",
        "tags": ["SQL", "WHERE", "HAVING", "GROUP BY", "Aggregates"],
        "frequent_companies": ["TCS", "Accenture", "Oracle", "Deloitte"]
    },
    {
        "interview_id": "iq_sql_02",
        "category_id": "cat_sql",
        "topic": "SQL",
        "difficulty": "Common",
        "question": "Explain the different types of SQL JOINs.",
        "short_answer": "INNER JOIN returns matching rows from both tables. LEFT JOIN returns all rows from left plus matches. RIGHT JOIN returns all rows from right. FULL JOIN returns all rows from both when there is a match in either.",
        "explanation": "1. `INNER JOIN`: Intersection of both tables. 2. `LEFT JOIN`: Left table + matching right table (NULL for non-matching). 3. `RIGHT JOIN`: Right table + matching left. 4. `FULL OUTER JOIN`: Union of left and right with NULLs where keys do not match.",
        "code": "-- LEFT JOIN example: All customers, with orders if they have any\nSELECT c.customer_name, o.order_id, o.amount\nFROM customers c\nLEFT JOIN orders o ON c.customer_id = o.customer_id;\n",
        "language": "sql",
        "tags": ["SQL", "JOIN", "Relational Database", "Queries"],
        "frequent_companies": ["Amazon", "Microsoft", "Flipkart", "Infosys"]
    },
    {
        "interview_id": "iq_sql_03",
        "category_id": "cat_sql",
        "topic": "SQL",
        "difficulty": "Common",
        "question": "What is Database Normalization (1NF, 2NF, 3NF)?",
        "short_answer": "Normalization is the process of organizing relational database tables to reduce data redundancy and eliminate insert, update, and delete anomalies.",
        "explanation": "1NF: Each column contains atomic (indivisible) values, no repeating groups. 2NF: In 1NF and no partial dependencies (every non-key attribute depends on the whole primary key). 3NF: In 2NF and no transitive dependencies (non-key attributes depend only on the primary key, not on other non-key columns).",
        "code": "-- 3NF Normalized Structure:\n-- Employees table\nCREATE TABLE employees (\n    emp_id INT PRIMARY KEY,\n    name VARCHAR(100),\n    dept_id INT REFERENCES departments(dept_id)\n);\n\n-- Separate Departments table eliminates department name redundancy\nCREATE TABLE departments (\n    dept_id INT PRIMARY KEY,\n    dept_name VARCHAR(100)\n);\n",
        "language": "sql",
        "tags": ["SQL", "Normalization", "Database Design", "RDBMS"],
        "frequent_companies": ["TCS", "Capgemini", "IBM", "Wipro"]
    },
    {
        "interview_id": "iq_sql_04",
        "category_id": "cat_sql",
        "topic": "SQL",
        "difficulty": "Common",
        "question": "What is the difference between Primary Key, Unique Key, and Foreign Key?",
        "short_answer": "A Primary Key uniquely identifies each row and does not accept NULLs. A Unique Key enforces uniqueness but allows one NULL. A Foreign Key references a primary or unique key in another table.",
        "explanation": "A table can have only one Primary Key (which can be composite). A table can have multiple Unique Keys. Foreign Keys maintain referential integrity between parent and child tables (e.g. cascading deletes or updates).",
        "code": "CREATE TABLE orders (\n    order_id INT PRIMARY KEY,               -- Primary Key (Not Null, Unique)\n    tracking_number VARCHAR(50) UNIQUE,     -- Unique Key (allows NULL once)\n    customer_id INT,                        -- Foreign Key column\n    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE\n);\n",
        "language": "sql",
        "tags": ["SQL", "Keys", "Constraints", "Integrity"],
        "frequent_companies": ["Oracle", "EY", "PwC", "KPMG"]
    },
    {
        "interview_id": "iq_sql_05",
        "category_id": "cat_sql",
        "topic": "SQL",
        "difficulty": "Intermediate",
        "question": "What are SQL Indexes and how do they improve query performance?",
        "short_answer": "An index is a B-Tree or Hash data structure that allows the database engine to locate records quickly without performing an expensive Full Table Scan.",
        "explanation": "Indexes dramatically speed up `SELECT`, `WHERE`, `ORDER BY`, and `JOIN` operations. However, each index incurs extra disk storage and slows down `INSERT`, `UPDATE`, and `DELETE` operations because the index trees must be recalculated on every write.",
        "code": "-- Create B-Tree index on frequently searched column\nCREATE INDEX idx_emp_email ON employees(email);\n\n-- Query uses index lookup in O(log N) instead of O(N) table scan\nSELECT * FROM employees WHERE email = 'dev@skiltrix.internal';\n",
        "language": "sql",
        "tags": ["SQL", "Indexes", "Performance", "Optimization"],
        "frequent_companies": ["Google", "Amazon", "Uber", "Swiggy"]
    },

    # ── DSA ─────────────────────────────────────────────────────────────
    {
        "interview_id": "iq_dsa_01",
        "category_id": "cat_dsa",
        "topic": "DSA",
        "difficulty": "Common",
        "question": "What is the difference between an Array and a Singly Linked List?",
        "short_answer": "Arrays store elements in contiguous memory allowing O(1) random access by index, whereas Linked Lists store elements in nodes with pointers allowing O(1) insertions at the head but O(N) traversal access.",
        "explanation": "Arrays have fixed size or reallocation overhead when resizing, but enjoy cache locality. Linked Lists allocate nodes dynamically in heap memory, using extra memory for pointer links and suffering from non-contiguous memory access.",
        "code": "class Node:\n    def __init__(self, val):\n        self.val = val\n        self.next = None\n\n# Linked list insertion at head: O(1)\nhead = Node(10)\nnew_node = Node(5)\nnew_node.next = head\nhead = new_node\n\n# Array index lookup: O(1)\narr = [5, 10, 15]\nprint('Array access:', arr[1]) # Direct index offset calculation\n",
        "language": "python",
        "tags": ["DSA", "Arrays", "LinkedList", "Data Structures", "Big-O"],
        "frequent_companies": ["Amazon", "Microsoft", "Google", "TCS"]
    },
    {
        "interview_id": "iq_dsa_02",
        "category_id": "cat_dsa",
        "topic": "DSA",
        "difficulty": "Common",
        "question": "Explain the difference between Breadth-First Search (BFS) and Depth-First Search (DFS).",
        "short_answer": "BFS traverses level-by-level using a Queue (FIFO), ideal for finding the shortest path in unweighted graphs. DFS explores as deep as possible along each branch before backtracking using a Stack or recursion (LIFO).",
        "explanation": "BFS space complexity is proportional to the maximum breadth of the graph ($O(W)$). DFS space complexity is proportional to the maximum depth of the graph ($O(D)$). Both have time complexity $O(V + E)$ where $V$ is vertices and $E$ is edges.",
        "code": "from collections import deque\n\ndef bfs(graph, start):\n    visited = set([start])\n    queue = deque([start])\n    while queue:\n        vertex = queue.popleft()\n        print(vertex, end=' ')\n        for neighbor in graph[vertex]:\n            if neighbor not in visited:\n                visited.add(neighbor)\n                queue.append(neighbor)\n",
        "language": "python",
        "tags": ["DSA", "BFS", "DFS", "Graphs", "Trees"],
        "frequent_companies": ["Google", "Meta", "Adobe", "Flipkart"]
    },
    {
        "interview_id": "iq_dsa_03",
        "category_id": "cat_dsa",
        "topic": "DSA",
        "difficulty": "Common",
        "question": "What is the time complexity of QuickSort vs MergeSort?",
        "short_answer": "MergeSort has guaranteed O(N log N) time complexity in all cases but requires O(N) auxiliary space. QuickSort is O(N log N) on average and in-place O(1) space, but O(N^2) in the worst case.",
        "explanation": "QuickSort's worst case occurs when the selected pivot is always the smallest or largest element (e.g. sorted array with first element as pivot). Randomized pivots or Median-of-Three pivot selection mitigates this in production standard libraries.",
        "code": "# MergeSort guarantee: O(N log N) in all cases\n# QuickSort average: O(N log N), in-place partitioning\ndef quick_sort(arr):\n    if len(arr) <= 1:\n        return arr\n    pivot = arr[len(arr) // 2]\n    left = [x for x in arr if x < pivot]\n    mid = [x for x in arr if x == pivot]\n    right = [x for x in arr if x > pivot]\n    return quick_sort(left) + mid + quick_sort(right)\n",
        "language": "python",
        "tags": ["DSA", "Sorting", "QuickSort", "MergeSort", "Time Complexity"],
        "frequent_companies": ["Microsoft", "Goldman Sachs", "Morgan Stanley"]
    },
    {
        "interview_id": "iq_dsa_04",
        "category_id": "cat_dsa",
        "topic": "DSA",
        "difficulty": "Common",
        "question": "How does a Hash Table achieve O(1) average lookup and handle collisions?",
        "short_answer": "A hash function maps keys to array bucket indices in O(1). Collisions (different keys yielding the same hash) are typically resolved using Separate Chaining (linked lists/trees at each bucket) or Open Addressing (probing).",
        "explanation": "When the load factor (elements / bucket capacity) exceeds a threshold (typically 0.75), the hash table dynamically resizes (doubles) and rehashes elements to prevent degradation to $O(N)$ lookup.",
        "code": "# Conceptual Separate Chaining in Python\nclass SimpleHashTable:\n    def __init__(self, size=10):\n        self.size = size\n        self.buckets = [[] for _ in range(size)]\n\n    def put(self, key, value):\n        index = hash(key) % self.size\n        for item in self.buckets[index]:\n            if item[0] == key:\n                item[1] = value\n                return\n        self.buckets[index].append([key, value])\n",
        "language": "python",
        "tags": ["DSA", "HashTable", "Hashing", "Collision Resolution"],
        "frequent_companies": ["Amazon", "Apple", "Oracle", "Uber"]
    },
    {
        "interview_id": "iq_dsa_05",
        "category_id": "cat_dsa",
        "topic": "DSA",
        "difficulty": "Intermediate",
        "question": "What is Dynamic Programming and how does Memoization differ from Tabulation?",
        "short_answer": "Dynamic Programming solves complex problems by breaking them into overlapping subproblems and optimal substructures. Memoization is top-down with recursion and caching; Tabulation is bottom-up with iteration.",
        "explanation": "Memoization computes solutions as needed and stores them in a hash map or array. Tabulation pre-fills an array starting from base cases up to the desired target, avoiding recursive call stack overhead and preventing stack overflow.",
        "code": "# Top-Down (Memoization)\ndef fib_memo(n, memo={}):\n    if n in memo: return memo[n]\n    if n <= 1: return n\n    memo[n] = fib_memo(n - 1, memo) + fib_memo(n - 2, memo)\n    return memo[n]\n\n# Bottom-Up (Tabulation)\ndef fib_tab(n):\n    if n <= 1: return n\n    dp = [0] * (n + 1)\n    dp[1] = 1\n    for i in range(2, n + 1):\n        dp[i] = dp[i-1] + dp[i-2]\n    return dp[n]\n",
        "language": "python",
        "tags": ["DSA", "Dynamic Programming", "Memoization", "Recursion"],
        "frequent_companies": ["Google", "Meta", "Amazon", "Directi"]
    },

    # ── HTML & CSS ──────────────────────────────────────────────────────
    {
        "interview_id": "iq_html_01",
        "category_id": "cat_html_css",
        "topic": "HTML & CSS",
        "difficulty": "Common",
        "question": "What is the CSS Box Model?",
        "short_answer": "The CSS Box Model is the container structure wrapping every HTML element, composed from inside out of Content, Padding, Border, and Margin.",
        "explanation": "By default (`box-sizing: content-box`), width specifies only the content width, causing padding and borders to expand total element width. With `box-sizing: border-box`, padding and border are included inside the specified width, making responsive sizing intuitive.",
        "code": "/* Recommended modern CSS reset */\n*,\n*::before,\n*::after {\n  box-sizing: border-box;\n  margin: 0;\n  padding: 0;\n}\n\n.card {\n  width: 300px;      /* Total rendered width is strictly 300px */\n  padding: 20px;     /* Included inside 300px */\n  border: 2px solid #6366f1; /* Included inside 300px */\n  margin: 16px;      /* Exterior spacing */\n}\n",
        "language": "html",
        "tags": ["HTML", "CSS", "Box Model", "Styling", "Basics"],
        "frequent_companies": ["TCS", "Infosys", "Cognizant", "Mindtree"]
    },
    {
        "interview_id": "iq_html_02",
        "category_id": "cat_html_css",
        "topic": "HTML & CSS",
        "difficulty": "Common",
        "question": "What is the difference between `display: none` and `visibility: hidden`?",
        "short_answer": "`display: none` removes the element completely from document flow taking up 0 space, while `visibility: hidden` hides the element visually but preserves its original space and dimensions on the page.",
        "explanation": "`display: none` triggers a reflow (layout recalculation) and repaint, and child elements cannot be made visible. `visibility: hidden` triggers only a repaint, and a child can be made visible with `visibility: visible`.",
        "code": "/* Hidden and collapses layout */\n.hidden-collapse {\n  display: none;\n}\n\n/* Invisible but keeps its width & height */\n.hidden-keep-space {\n  visibility: hidden;\n}\n",
        "language": "html",
        "tags": ["CSS", "Display", "Visibility", "Layout"],
        "frequent_companies": ["Wipro", "Accenture", "Zoho", "LTI"]
    },
    {
        "interview_id": "iq_html_03",
        "category_id": "cat_html_css",
        "topic": "HTML & CSS",
        "difficulty": "Common",
        "question": "What is the difference between Flexbox and CSS Grid?",
        "short_answer": "Flexbox is designed for one-dimensional layouts (a single row or single column), while CSS Grid is designed for two-dimensional layouts (simultaneous rows AND columns).",
        "explanation": "Flexbox distributes space along one main axis (content-first). CSS Grid divides a container into rows and columns with gap specifications, placing items inside template areas or explicit grid cells (layout-first).",
        "code": "/* Flexbox: 1D navbar or item list */\n.nav-bar {\n  display: flex;\n  justify-content: space-between;\n  align-items: center;\n}\n\n/* Grid: 2D dashboard or product matrix */\n.dashboard-grid {\n  display: grid;\n  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));\n  gap: 1.5rem;\n}\n",
        "language": "html",
        "tags": ["CSS", "Flexbox", "Grid", "Responsive Design"],
        "frequent_companies": ["Swiggy", "Zomato", "Myntra", "Flipkart"]
    },

    # ── REACT ───────────────────────────────────────────────────────────
    {
        "interview_id": "iq_react_01",
        "category_id": "cat_react",
        "topic": "React",
        "difficulty": "Common",
        "question": "What is the difference between State and Props in React?",
        "short_answer": "`props` (properties) are read-only inputs passed from a parent component to a child, whereas `state` is internal data managed and mutable by the component itself via `useState`.",
        "explanation": "When `state` or `props` change, React re-renders the component. Props flow downwards (unidirectional data flow); state is private to the component unless explicitly lifted up or distributed through Context.",
        "code": "function UserCard({ name, role }) { // Props (read-only)\n  const [isFollowing, setIsFollowing] = React.useState(false); // State (internal)\n\n  return (\n    <div>\n      <h3>{name} - {role}</h3>\n      <button onClick={() => setIsFollowing(!isFollowing)}>\n        {isFollowing ? 'Following' : 'Follow'}\n      </button>\n    </div>\n  );\n}\n",
        "language": "javascript",
        "tags": ["React", "State", "Props", "Components", "Basics"],
        "frequent_companies": ["Meta", "Amazon", "Microsoft", "Paytm"]
    },
    {
        "interview_id": "iq_react_02",
        "category_id": "cat_react",
        "topic": "React",
        "difficulty": "Common",
        "question": "What is the Virtual DOM and how does React Reconciliation work?",
        "short_answer": "The Virtual DOM is an in-memory lightweight representation of the real DOM. React computes differences between new and old Virtual DOM trees (diffing) and applies only the minimum necessary changes to the real DOM (reconciliation).",
        "explanation": "Direct DOM manipulation is computationally expensive because it causes layout recalculations and repaints. React's diffing algorithm runs in $O(N)$ by assuming different element types produce different trees and using stable `key` attributes on lists.",
        "code": "// Keys are essential for React diffing:\nfunction TodoList({ items }) {\n  return (\n    <ul>\n      {items.map(item => (\n        <li key={item.id}>{item.text}</li> // Stable key for reconciliation\n      ))}\n    </ul>\n  );\n}\n",
        "language": "javascript",
        "tags": ["React", "Virtual DOM", "Reconciliation", "Diffing"],
        "frequent_companies": ["Meta", "Uber", "Airbnb", "Netflix"]
    },
    {
        "interview_id": "iq_react_03",
        "category_id": "cat_react",
        "topic": "React",
        "difficulty": "Common",
        "question": "What are the rules of React Hooks and how does `useEffect` work?",
        "short_answer": "Hooks must only be called at the top level (never in loops or conditions) and only inside React function components. `useEffect` performs side-effects (data fetching, subscriptions) after rendering.",
        "explanation": "The dependency array in `useEffect`: 1. No array: runs after every render. 2. Empty array `[]`: runs once on mount. 3. Array `[a, b]`: runs when `a` or `b` change. The cleanup function returned from `useEffect` runs before unmount or next effect execution.",
        "code": "React.useEffect(() => {\n  const handler = () => console.log('Window resized');\n  window.addEventListener('resize', handler);\n\n  // Cleanup function prevents memory leaks\n  return () => window.removeEventListener('resize', handler);\n}, []); // Empty dependency array = mount & unmount only\n",
        "language": "javascript",
        "tags": ["React", "Hooks", "useEffect", "Lifecycle"],
        "frequent_companies": ["Razorpay", "CRED", "Intuit", "Postman"]
    },

    # ── DJANGO ──────────────────────────────────────────────────────────
    {
        "interview_id": "iq_dj_01",
        "category_id": "cat_django",
        "topic": "Django",
        "difficulty": "Common",
        "question": "Explain the MTV (Model-Template-View) architectural pattern in Django.",
        "short_answer": "Django uses MTV: Model handles the database schema and ORM; Template handles HTML rendering/UI; View handles business logic, querying models, and returning HTTP responses.",
        "explanation": "MTV maps to MVC: Django's Model is Model, Template is View, and View acts as the Controller orchestrating URLs, database queries, and response payloads.",
        "code": "# views.py: Business logic\nfrom django.shortcuts import render\nfrom .models import Course\n\ndef course_list(request):\n    courses = Course.objects.filter(is_active=True)\n    return render(request, 'courses/list.html', {'courses': courses})\n",
        "language": "python",
        "tags": ["Django", "MTV", "Architecture", "MVC"],
        "frequent_companies": ["Instagram", "Pinterest", "Infosys", "TCS"]
    },
    {
        "interview_id": "iq_dj_02",
        "category_id": "cat_django",
        "topic": "Django",
        "difficulty": "Intermediate",
        "question": "What is the difference between `select_related` and `prefetch_related` in Django ORM?",
        "short_answer": "`select_related` uses SQL JOINs in a single query for single-valued relationships (ForeignKey, OneToOne). `prefetch_related` executes separate SQL queries and performs in-memory Python joining for multi-valued relationships (ManyToMany, reverse ForeignKeys).",
        "explanation": "Both solve the N+1 database query problem. Using `select_related` on ManyToMany relationships is invalid because a SQL JOIN would duplicate table rows exponentially.",
        "code": "# ForeignKey: Single SQL query with JOIN\nposts = Post.objects.select_related('author').all()\n\n# ManyToMany: 2 SQL queries joined in Python memory\narticles = Article.objects.prefetch_related('tags').all()\n",
        "language": "python",
        "tags": ["Django", "ORM", "select_related", "prefetch_related", "N+1"],
        "frequent_companies": ["Swiggy", "Zomato", "RedBus", "Ola"]
    },

    # ── SAP ABAP ────────────────────────────────────────────────────────
    {
        "interview_id": "iq_abap_01",
        "category_id": "cat_abap",
        "topic": "SAP ABAP",
        "difficulty": "Common",
        "question": "What is the difference between an Internal Table and a Work Area in ABAP?",
        "short_answer": "An Internal Table is a dynamic temporary table holding multiple records in memory at runtime, while a Work Area is a single-line data structure used to process one record from the internal table at a time.",
        "explanation": "To loop over or insert records into an internal table, developers move records into or out of a Work Area (or field-symbol in modern ABAP). Standard, Sorted, and Hashed tables provide linear, binary, and hash lookups respectively.",
        "code": "* Declare work area and internal table\nDATA: wa_flight TYPE sflight,\n      it_flight TYPE STANDARD TABLE OF sflight.\n\nSELECT * FROM sflight INTO TABLE it_flight UP TO 10 ROWS.\n\nLOOP AT it_flight INTO wa_flight.\n  WRITE: / wa_flight-carrid, wa_flight-connid, wa_flight-price.\nENDLOOP.\n",
        "language": "python",
        "tags": ["SAP ABAP", "Internal Tables", "Work Area", "Basics"],
        "frequent_companies": ["SAP", "Accenture", "TCS", "Capgemini", "Deloitte"]
    },
    {
        "interview_id": "iq_abap_02",
        "category_id": "cat_abap",
        "topic": "SAP ABAP",
        "difficulty": "Common",
        "question": "What is SY-SUBRC and what do its return values mean?",
        "short_answer": "`SY-SUBRC` is a built-in ABAP system field that stores the return code of the most recently executed ABAP statement; a value of 0 means successful execution.",
        "explanation": "Common return codes: 0 = Success (e.g. `SELECT` or `READ TABLE` found a record). 4 = Record not found or condition not met. 8 = End of table or key error. Always check `SY-SUBRC = 0` before processing data after `SELECT` or `READ TABLE`.",
        "code": "READ TABLE it_flight INTO wa_flight WITH KEY carrid = 'AA'.\nIF sy-subrc = 0.\n  WRITE: / 'Record found:', wa_flight-connid.\nELSE.\n  WRITE: / 'No flight record found with carrier AA'.\nENDIF.\n",
        "language": "python",
        "tags": ["SAP ABAP", "SY-SUBRC", "System Fields", "Error Handling"],
        "frequent_companies": ["IBM", "Infosys", "PwC", "EY"]
    }
]

def seed_interviews():
    print("Seeding Interview Categories...")
    category_map = {}
    for cat in CATEGORIES_DATA:
        obj, created = InterviewCategories.objects.update_or_create(
            category_id=cat["category_id"],
            defaults={
                "name": cat["name"],
                "icon": cat["icon"],
                "status": "active",
            }
        )
        category_map[cat["category_id"]] = obj
        print(f"  {'Created' if created else 'Updated'} Category: {cat['name']}")

    print("\nSeeding Interview Questions...")
    for q in QUESTIONS_DATA:
        cat_obj = category_map.get(q["category_id"])
        obj, created = InterviewQuestions.objects.update_or_create(
            interview_id=q["interview_id"],
            defaults={
                "category": cat_obj,
                "topic": q["topic"],
                "difficulty": q["difficulty"],
                "question": q["question"],
                "short_answer": q["short_answer"],
                "explanation": q["explanation"],
                "code": q.get("code", ""),
                "language": q.get("language", "python"),
                "tags": q.get("tags", []),
                "frequent_companies": q.get("frequent_companies", []),
                "status": "active",
            }
        )
        print(f"  {'Created' if created else 'Updated'} Question: [{q['topic']}] {q['question'][:45]}...")

    # Update category counts
    for cat_id, cat_obj in category_map.items():
        q_count = InterviewQuestions.objects.filter(category=cat_obj, status="active").count()
        cat_obj.count = q_count
        cat_obj.save(update_fields=["count"])
        print(f"  Category '{cat_obj.name}' has {q_count} questions.")

    total_q = InterviewQuestions.objects.filter(status="active").count()
    print(f"\nDone! Successfully seeded {total_q} active interview questions.")

if __name__ == "__main__":
    seed_interviews()
