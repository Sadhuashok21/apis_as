"""
SkilTrix SAP ABAP Lab - Curriculum Seed Data
Populates foundational exercises and test cases across Beginner, Intermediate, and Advanced tiers.
"""

from .abap_models import ABAPExercise, ABAPTestCase


SEED_EXERCISES = [
    {
        "exercise_id": "abap_beg_01",
        "title": "Hello SAP ABAP World",
        "slug": "hello-sap-abap-world",
        "category": "Beginner",
        "difficulty": "Easy",
        "topic": "Basic Syntax & Reports",
        "points": 10,
        "order": 1,
        "problem_statement": (
            "Write an executable ABAP report named `ZHELLO_WORLD` that outputs:\n"
            "`Hello, SAP ABAP World!`\n"
            "followed by a horizontal underline using the `ULINE` statement, and on the next line output:\n"
            "`Welcome to SkilTrix ABAP Studio.`\n\n"
            "Constraints:\n"
            "- Use the standard `REPORT` declaration.\n"
            "- Use the `WRITE:` statement with a chain colon or individual `WRITE` statements.\n"
            "- Ensure exact string matching."
        ),
        "starter_code": (
            "*&---------------------------------------------------------------------*\n"
            "*& Report ZHELLO_WORLD\n"
            "*&---------------------------------------------------------------------*\n"
            "REPORT zhello_world.\n\n"
            "* Write your code below\n"
            "WRITE: / 'Hello, SAP ABAP World!'.\n"
            "ULINE.\n"
            "WRITE: / 'Welcome to SkilTrix ABAP Studio.'.\n"
        ),
        "solution_hint": "Use WRITE: / 'text'. to start output on a new line.",
        "sample_output": "Hello, SAP ABAP World!\n--------------------------------------------------\nWelcome to SkilTrix ABAP Studio.",
        "tests": [
            {
                "input_data": "",
                "expected_output": "Hello, SAP ABAP World!\nWelcome to SkilTrix ABAP Studio.",
                "is_sample": True,
                "is_hidden": False,
                "order": 1,
            },
            {
                "input_data": "",
                "expected_output": "Hello, SAP ABAP World!\nWelcome to SkilTrix ABAP Studio.",
                "is_sample": False,
                "is_hidden": True,
                "order": 2,
            }
        ]
    },
    {
        "exercise_id": "abap_beg_02",
        "title": "Elementary Data Types & Calculations",
        "slug": "elementary-data-types-calculations",
        "category": "Beginner",
        "difficulty": "Easy",
        "topic": "DATA Declarations & Arithmetic",
        "points": 15,
        "order": 2,
        "problem_statement": (
            "Declare two integer variables `lv_qty` (type I) and `lv_unit_price` (type P DECIMALS 2).\n"
            "Set `lv_qty = 12` and `lv_unit_price = '45.50'`.\n"
            "Calculate the total amount into `lv_total` (type P DECIMALS 2).\n"
            "Output the results formatted as:\n"
            "`Quantity: 12`\n"
            "`Price: 45.50`\n"
            "`Total: 546.00`"
        ),
        "starter_code": (
            "REPORT zdata_types_demo.\n\n"
            "DATA: lv_qty        TYPE i VALUE 12,\n"
            "      lv_unit_price TYPE p DECIMALS 2 VALUE '45.50',\n"
            "      lv_total      TYPE p DECIMALS 2.\n\n"
            "* Compute total and display\n"
            "lv_total = lv_qty * lv_unit_price.\n\n"
            "WRITE: / 'Quantity:', lv_qty,\n"
            "       / 'Price:', lv_unit_price,\n"
            "       / 'Total:', lv_total.\n"
        ),
        "solution_hint": "Compute with lv_total = lv_qty * lv_unit_price.",
        "sample_output": "Quantity: 12\nPrice: 45.50\nTotal: 546.00",
        "tests": [
            {
                "input_data": "",
                "expected_output": "Quantity: 12\nPrice: 45.50\nTotal: 546.00",
                "is_sample": True,
                "is_hidden": False,
                "order": 1,
            }
        ]
    },
    {
        "exercise_id": "abap_int_01",
        "title": "Internal Tables: Population & Iteration",
        "slug": "internal-tables-population-iteration",
        "category": "Intermediate",
        "difficulty": "Medium",
        "topic": "Internal Tables & Work Areas",
        "points": 25,
        "order": 3,
        "problem_statement": (
            "Define a structure `ty_employee` with fields `emp_id` (TYPE I), `name` (TYPE STRING), "
            "and `department` (TYPE STRING).\n"
            "Declare a standard internal table `lt_employees` and a work area `ls_employee`.\n"
            "Append 3 employees:\n"
            "1, 'Alice Smith', 'Finance'\n"
            "2, 'Bob Jones', 'Engineering'\n"
            "3, 'Carol White', 'Marketing'\n\n"
            "Iterate through `lt_employees` using `LOOP AT ... INTO ...` and print each record in the format:\n"
            "`[ID] Name - Department`"
        ),
        "starter_code": (
            "REPORT zinternal_tables_demo.\n\n"
            "TYPES: BEGIN OF ty_employee,\n"
            "         emp_id     TYPE i,\n"
            "         name       TYPE string,\n"
            "         department TYPE string,\n"
            "       END OF ty_employee.\n\n"
            "DATA: lt_employees TYPE STANDARD TABLE OF ty_employee,\n"
            "      ls_employee  TYPE ty_employee.\n\n"
            "* Add employee 1\n"
            "ls_employee-emp_id = 1.\n"
            "ls_employee-name = 'Alice Smith'.\n"
            "ls_employee-department = 'Finance'.\n"
            "APPEND ls_employee TO lt_employees.\n\n"
            "* Add employee 2\n"
            "ls_employee-emp_id = 2.\n"
            "ls_employee-name = 'Bob Jones'.\n"
            "ls_employee-department = 'Engineering'.\n"
            "APPEND ls_employee TO lt_employees.\n\n"
            "* Add employee 3\n"
            "ls_employee-emp_id = 3.\n"
            "ls_employee-name = 'Carol White'.\n"
            "ls_employee-department = 'Marketing'.\n"
            "APPEND ls_employee TO lt_employees.\n\n"
            "* Loop and display\n"
            "LOOP AT lt_employees INTO ls_employee.\n"
            "  WRITE: / '[' , ls_employee-emp_id , ']' , ls_employee-name , '-' , ls_employee-department.\n"
            "ENDLOOP.\n"
        ),
        "solution_hint": "Use APPEND ls_employee TO lt_employees and LOOP AT lt_employees INTO ls_employee.",
        "sample_output": "[ 1 ] Alice Smith - Finance\n[ 2 ] Bob Jones - Engineering\n[ 3 ] Carol White - Marketing",
        "tests": [
            {
                "input_data": "",
                "expected_output": "[ 1 ] Alice Smith - Finance\n[ 2 ] Bob Jones - Engineering\n[ 3 ] Carol White - Marketing",
                "is_sample": True,
                "is_hidden": False,
                "order": 1,
            }
        ]
    },
    {
        "exercise_id": "abap_int_02",
        "title": "Open SQL Query on SAP Customers (KNA1)",
        "slug": "open-sql-query-sap-customers-kna1",
        "category": "Intermediate",
        "difficulty": "Medium",
        "topic": "Open SQL & Database Access",
        "points": 30,
        "order": 4,
        "problem_statement": (
            "Using Open SQL, select the fields `kunnr` (Customer Number), `name1` (Customer Name), "
            "and `land1` (Country Key) from the customer table `KNA1` for customers located in Germany (`land1 = 'DE'`).\n"
            "Order results by `kunnr` ascending.\n"
            "Output each customer as: `KUNNR: <kunnr> | NAME: <name1>`."
        ),
        "starter_code": (
            "REPORT zopen_sql_kna1.\n\n"
            "TYPES: BEGIN OF ty_customer,\n"
            "         kunnr TYPE string,\n"
            "         name1 TYPE string,\n"
            "         land1 TYPE string,\n"
            "       END OF ty_customer.\n\n"
            "DATA: lt_customers TYPE STANDARD TABLE OF ty_customer,\n"
            "      ls_customer  TYPE ty_customer.\n\n"
            "SELECT kunnr, name1, land1\n"
            "  FROM kna1\n"
            "  WHERE land1 = 'DE'\n"
            "  ORDER BY kunnr\n"
            "  INTO TABLE @lt_customers.\n\n"
            "LOOP AT lt_customers INTO ls_customer.\n"
            "  WRITE: / 'KUNNR:', ls_customer-kunnr, '| NAME:', ls_customer-name1.\n"
            "ENDLOOP.\n"
        ),
        "solution_hint": "Use SELECT ... FROM kna1 WHERE land1 = 'DE' INTO TABLE @lt_customers.",
        "sample_output": "KUNNR: 100001 | NAME: Siemens AG\nKUNNR: 100003 | NAME: BMW Group",
        "tests": [
            {
                "input_data": "",
                "expected_output": "KUNNR: 100001 | NAME: Siemens AG\nKUNNR: 100003 | NAME: BMW Group",
                "is_sample": True,
                "is_hidden": False,
                "order": 1,
            }
        ]
    },
    {
        "exercise_id": "abap_adv_01",
        "title": "Object-Oriented ABAP: Classes & Methods",
        "slug": "oo-abap-classes-methods",
        "category": "Advanced",
        "difficulty": "Hard",
        "topic": "Object-Oriented ABAP",
        "points": 40,
        "order": 5,
        "problem_statement": (
            "Create a local ABAP class `lcl_calculator` with:\n"
            "- A public method `calculate_tax` accepting importing parameter `iv_amount` (TYPE P DECIMALS 2) "
            "and `iv_rate` (TYPE P DECIMALS 2, default 0.18), returning parameter `rv_tax` (TYPE P DECIMALS 2).\n"
            "- Instantiate the class and call `calculate_tax` with amount = 1000.00.\n"
            "- Output: `Calculated Tax: 180.00`."
        ),
        "starter_code": (
            "REPORT zoo_abap_demo.\n\n"
            "CLASS lcl_calculator DEFINITION.\n"
            "  PUBLIC SECTION.\n"
            "    METHODS calculate_tax\n"
            "      IMPORTING\n"
            "        iv_amount     TYPE p\n"
            "        iv_rate       TYPE p DEFAULT '0.18'\n"
            "      RETURNING\n"
            "        VALUE(rv_tax) TYPE p.\n"
            "ENDCLASS.\n\n"
            "CLASS lcl_calculator IMPLEMENTATION.\n"
            "  METHOD calculate_tax.\n"
            "    rv_tax = iv_amount * iv_rate.\n"
            "  ENDMETHOD.\n"
            "ENDCLASS.\n\n"
            "START-OF-SELECTION.\n"
            "  DATA(lo_calc) = NEW lcl_calculator( ).\n"
            "  DATA(lv_tax) = lo_calc->calculate_tax( iv_amount = '1000.00' ).\n"
            "  WRITE: / 'Calculated Tax:', lv_tax.\n"
        ),
        "solution_hint": "Define calculate_tax in PUBLIC SECTION with RETURNING VALUE(rv_tax).",
        "sample_output": "Calculated Tax: 180.00",
        "tests": [
            {
                "input_data": "",
                "expected_output": "Calculated Tax: 180.00",
                "is_sample": True,
                "is_hidden": False,
                "order": 1,
            }
        ]
    }
]


def seed_abap_curriculum():
    """Idempotently seeds foundational ABAP curriculum questions."""
    for item in SEED_EXERCISES:
        ex, created = ABAPExercise.objects.update_or_create(
            exercise_id=item["exercise_id"],
            defaults={
                "title": item["title"],
                "slug": item["slug"],
                "category": item["category"],
                "difficulty": item["difficulty"],
                "topic": item["topic"],
                "points": item["points"],
                "order": item["order"],
                "problem_statement": item["problem_statement"],
                "starter_code": item["starter_code"],
                "solution_hint": item.get("solution_hint", ""),
                "supported_mode": "both",
                "is_active": True,
            }
        )
        for t in item.get("tests", []):
            ABAPTestCase.objects.update_or_create(
                exercise=ex,
                order=t["order"],
                defaults={
                    "test_case_id": f"tc_{ex.exercise_id}_{t['order']}",
                    "input_data": t.get("input_data", ""),
                    "expected_output": t["expected_output"],
                    "is_sample": t.get("is_sample", True),
                    "is_hidden": t.get("is_hidden", False),
                }
            )
    return len(SEED_EXERCISES)

