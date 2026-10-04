"""
SkilTrix SAP ABAP Lab - Lexer & Preprocessor
Tokenizes ABAP source code and normalizes chained statements (e.g., DATA:, WRITE:)
"""

import re
from typing import List, NamedTuple, Optional


class TokenType:
    KEYWORD = "KEYWORD"
    IDENTIFIER = "IDENTIFIER"
    STRING = "STRING"
    NUMBER = "NUMBER"
    DELIMITER = "DELIMITER"
    OPERATOR = "OPERATOR"
    NEWLINE = "NEWLINE"
    EOF = "EOF"


class Token(NamedTuple):
    type: str
    value: str
    line: int
    column: int


class Statement(NamedTuple):
    raw_text: str
    tokens: List[Token]
    line: int
    terminated: bool = True


def preprocess_abap(source_code: str) -> List[Statement]:
    """
    Cleans comments, normalizes chained statements with colons (':'),
    and splits code into discrete ABAP statements ending with a period ('.').
    """
    lines = source_code.splitlines()
    cleaned_tokens_stream = []

    # Regex patterns
    token_spec = [
        ("STRING_TICK", r"'([^'\\]|\\.)*'"),       # 'standard text field'
        ("STRING_BACKTICK", r"`([^`\\]|\\.)*`"),   # `string type`
        ("STRING_TEMPLATE", r"\|([^\|\\]|\\.)*\|"), # |template { var }|
        ("NUMBER", r"\b\d+(\.\d+)?\b"),
        ("DELIMITER", r"(\->|=>|&&|<=|>=|<>|\.|\,|:|\(|\)|\[|\]|@|/|\+|-|\*|<|>|=|~)"),
        ("IDENTIFIER", r"[a-zA-Z0-9_#]+(~[a-zA-Z0-9_#]+)*(-(?!>)[a-zA-Z0-9_#]+)*"),
        ("WHITESPACE", r"[ \t]+"),
    ]
    tok_regex = re.compile("|".join(f"(?P<{pair[0]}>{pair[1]})" for pair in token_spec))

    all_raw_tokens: List[Token] = []

    for line_idx, line in enumerate(lines, start=1):
        # 1. Line comment starting with * at column 0
        if line.startswith("*"):
            continue

        # 2. Inline comments starting with "
        # We must be careful not to strip " inside string literals
        in_str = None
        clean_chars = []
        for ch in line:
            if ch in ("'", "`", "|") and in_str is None:
                in_str = ch
                clean_chars.append(ch)
            elif ch == in_str:
                in_str = None
                clean_chars.append(ch)
            elif ch == '"' and in_str is None:
                # Comment starts here to end of line
                break
            else:
                clean_chars.append(ch)

        clean_line = "".join(clean_chars)

        for match in tok_regex.finditer(clean_line):
            kind = match.lastgroup
            val = match.group()
            col = match.start() + 1

            if kind == "WHITESPACE":
                continue
            elif kind in ("STRING_TICK", "STRING_BACKTICK", "STRING_TEMPLATE"):
                # Strip quotes for string content
                content = val[1:-1]
                all_raw_tokens.append(Token(TokenType.STRING, content, line_idx, col))
            elif kind == "NUMBER":
                all_raw_tokens.append(Token(TokenType.NUMBER, val, line_idx, col))
            elif kind == "DELIMITER":
                all_raw_tokens.append(Token(TokenType.DELIMITER, val, line_idx, col))
            elif kind == "IDENTIFIER":
                all_raw_tokens.append(Token(TokenType.IDENTIFIER, val, line_idx, col))

    # Split into statements ending with period '.'
    statements: List[Statement] = []
    current_tokens: List[Token] = []
    start_line = 1
    statement_starters = {
        "REPORT", "PROGRAM", "DATA", "CONSTANTS", "TYPES", "WRITE", "ULINE", "SKIP",
        "CLEAR", "REFRESH", "FREE", "IF", "ELSEIF", "ELSE", "ENDIF", "CASE", "WHEN",
        "ENDCASE", "DO", "ENDDO", "WHILE", "ENDWHILE", "LOOP", "ENDLOOP", "SELECT",
        "INSERT", "UPDATE", "DELETE", "MODIFY", "APPEND", "READ", "SORT", "FORM",
        "COMMIT", "ROLLBACK",
        "ENDFORM", "PERFORM", "CLASS", "ENDCLASS", "METHOD", "METHODS", "CLASS-METHODS",
        "INTERFACE", "ENDINTERFACE", "INTERFACES", "PUBLIC", "PROTECTED", "PRIVATE",
        "CLASS-DATA", "RAISE", "TRY", "CATCH",
        "CLEANUP", "ENDTRY", "CREATE", "CALL", "EXIT", "CONTINUE", "START-OF-SELECTION",
        "INITIALIZATION", "END-OF-SELECTION", "TOP-OF-PAGE",
    }

    for token_index, tok in enumerate(all_raw_tokens):
        # ABAP statements can span lines, but a new statement keyword at the
        # start of a later line is strong evidence that the previous statement
        # lost its required period. Split there so the parser can underline it.
        next_tok = all_raw_tokens[token_index + 1] if token_index + 1 < len(all_raw_tokens) else None
        assignment_start = (
            tok.type == TokenType.IDENTIFIER and next_tok is not None
            and next_tok.value == "=" and next_tok.line == tok.line
        )
        previous_looks_complete = bool(current_tokens) and current_tokens[-1].value not in {",", ":", "=", "+", "-", "*", "/", "&&", "->", "=>"}
        if current_tokens and tok.line > current_tokens[-1].line and previous_looks_complete and (tok.value.upper() in statement_starters or assignment_start):
            statements.extend(expand_chained_statement(current_tokens, start_line, terminated=False))
            current_tokens = []
        if not current_tokens:
            start_line = tok.line

        if tok.type == TokenType.DELIMITER and tok.value == ".":
            if current_tokens:
                # Check for chained statement (contains colon ':')
                expanded = expand_chained_statement(current_tokens, start_line, terminated=True)
                statements.extend(expanded)
                current_tokens = []
        else:
            current_tokens.append(tok)

    # Unclosed trailing statement if any
    if current_tokens:
        expanded = expand_chained_statement(current_tokens, start_line, terminated=False)
        statements.extend(expanded)

    return statements


def expand_chained_statement(tokens: List[Token], line: int, terminated: bool = True) -> List[Statement]:
    """
    Expands chained statements:
    WRITE: / 'A', / 'B' -> WRITE / 'A'. WRITE / 'B'.
    DATA: a TYPE i, b TYPE i -> DATA a TYPE i. DATA b TYPE i.
    """
    # Find colon
    colon_idx = -1
    for i, t in enumerate(tokens):
        if t.type == TokenType.DELIMITER and t.value == ":":
            colon_idx = i
            break

    if colon_idx == -1:
        # Normal statement without colon
        raw_text = " ".join(t.value for t in tokens)
        return [Statement(raw_text, tokens, line, terminated)]

    prefix_tokens = tokens[:colon_idx]
    remainder_tokens = tokens[colon_idx + 1 :]

    # Split remainder by commas ','
    clauses: List[List[Token]] = []
    current_clause: List[Token] = []

    for t in remainder_tokens:
        if t.type == TokenType.DELIMITER and t.value == ",":
            if current_clause:
                clauses.append(current_clause)
                current_clause = []
        else:
            current_clause.append(t)

    if current_clause:
        clauses.append(current_clause)

    expanded_stmts = []
    for clause in clauses:
        combined = prefix_tokens + clause
        raw_text = " ".join(t.value for t in combined)
        expanded_stmts.append(Statement(raw_text, combined, clause[0].line if clause else line, terminated))

    return expanded_stmts

