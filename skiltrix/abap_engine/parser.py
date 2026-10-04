"""
SkilTrix SAP ABAP Lab - AST Parser
Parses preprocessed statements into a typed Abstract Syntax Tree (AST)
supporting the documented educational ABAP language subset.
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from .lexer import Statement, Token, TokenType


class ASTNode:
    def __init__(self, line: int):
        self.line = line


class ReportNode(ASTNode):
    def __init__(self, name: str, line: int):
        super().__init__(line)
        self.name = name


class DataDeclNode(ASTNode):
    def __init__(
        self,
        var_name: str,
        var_type: str,
        initial_value: Optional[Any] = None,
        is_table: bool = False,
        table_type: str = "standard",  # standard, sorted, hashed
        line_type: Optional[str] = None,
        like_var: Optional[str] = None,
        key_def: Optional[Dict[str, Any]] = None,
        line: int = 1,
    ):
        super().__init__(line)
        self.var_name = var_name.upper()
        self.var_type = var_type.upper()
        self.initial_value = initial_value
        self.is_table = is_table
        self.table_type = table_type.lower()
        self.line_type = line_type.upper() if line_type else self.var_type
        self.like_var = like_var.upper() if like_var else None
        self.key_def = key_def or {}


class TypesDeclNode(ASTNode):
    def __init__(self, type_name: str, fields: List[Dict[str, str]], line: int):
        super().__init__(line)
        self.type_name = type_name.upper()
        self.fields = fields


class ConstantsDeclNode(ASTNode):
    def __init__(self, const_name: str, const_type: str, value: Any, line: int):
        super().__init__(line)
        self.const_name = const_name.upper()
        self.const_type = const_type.upper()
        self.value = value


class AssignNode(ASTNode):
    def __init__(self, target: str, expr_tokens: List[Token], line: int):
        super().__init__(line)
        self.target = target.upper()
        self.expr_tokens = expr_tokens


class WriteItem:
    def __init__(self, value_token: Token, is_slash: bool = False):
        self.value_token = value_token
        self.is_slash = is_slash


class WriteNode(ASTNode):
    def __init__(self, items: List[WriteItem], line: int):
        super().__init__(line)
        self.items = items


class UlineNode(ASTNode):
    def __init__(self, line: int):
        super().__init__(line)


class SkipNode(ASTNode):
    def __init__(self, count: int, line: int):
        super().__init__(line)
        self.count = count


class IfNode(ASTNode):
    def __init__(
        self,
        cond_tokens: List[Token],
        then_body: List[ASTNode],
        elseif_branches: List[Dict[str, Any]],
        else_body: List[ASTNode],
        line: int,
    ):
        super().__init__(line)
        self.cond_tokens = cond_tokens
        self.then_body = then_body
        self.elseif_branches = elseif_branches
        self.else_body = else_body


class CaseNode(ASTNode):
    def __init__(
        self,
        expr_tokens: List[Token],
        when_branches: List[Dict[str, Any]],
        others_body: List[ASTNode],
        line: int,
    ):
        super().__init__(line)
        self.expr_tokens = expr_tokens
        self.when_branches = when_branches
        self.others_body = others_body


class DoNode(ASTNode):
    def __init__(self, times_expr: Optional[List[Token]], body: List[ASTNode], line: int):
        super().__init__(line)
        self.times_expr = times_expr
        self.body = body


class WhileNode(ASTNode):
    def __init__(self, cond_tokens: List[Token], body: List[ASTNode], line: int):
        super().__init__(line)
        self.cond_tokens = cond_tokens
        self.body = body


class LoopNode(ASTNode):
    def __init__(
        self,
        table_name: str,
        target_var: Optional[str],
        assigning_fs: Optional[str],
        where_tokens: Optional[List[Token]],
        body: List[ASTNode],
        line: int,
    ):
        super().__init__(line)
        self.table_name = table_name.upper()
        self.target_var = target_var.upper() if target_var else None
        self.assigning_fs = assigning_fs.upper() if assigning_fs else None
        self.where_tokens = where_tokens
        self.body = body


class ReadTableNode(ASTNode):
    def __init__(
        self,
        table_name: str,
        target_var: Optional[str],
        assigning_fs: Optional[str],
        key_field: Optional[str],
        key_val_tokens: Optional[List[Token]],
        index_expr: Optional[List[Token]],
        line: int,
    ):
        super().__init__(line)
        self.table_name = table_name.upper()
        self.target_var = target_var.upper() if target_var else None
        self.assigning_fs = assigning_fs.upper() if assigning_fs else None
        self.key_field = key_field.upper() if key_field else None
        self.key_val_tokens = key_val_tokens
        self.index_expr = index_expr


class AppendNode(ASTNode):
    def __init__(
        self,
        source_var: Optional[str],
        target_table: str,
        initial_line: bool = False,
        assigning_fs: Optional[str] = None,
        source_tokens: Optional[List[Token]] = None,
        line: int = 1,
    ):
        super().__init__(line)
        self.source_var = source_var.upper() if source_var else None
        self.target_table = target_table.upper()
        self.initial_line = initial_line
        self.assigning_fs = assigning_fs.upper() if assigning_fs else None
        self.source_tokens = source_tokens


class InsertNode(ASTNode):
    def __init__(
        self,
        target_table: str,
        from_table: Optional[str] = None,
        from_wa: Optional[str] = None,
        values: Optional[List[Token]] = None,
        is_internal_table: bool = False,
        wa_var: Optional[str] = None,
        itab_var: Optional[str] = None,
        index_expr: Optional[List[Token]] = None,
        line: int = 1,
    ):
        super().__init__(line)
        self.target_table = target_table.upper()
        self.from_table = from_table.upper() if from_table else None
        self.from_wa = from_wa.upper() if from_wa else None
        self.values = values
        self.is_internal_table = is_internal_table
        self.wa_var = wa_var.upper() if wa_var else None
        self.itab_var = itab_var.upper() if itab_var else None
        self.index_expr = index_expr


class UpdateNode(ASTNode):
    def __init__(
        self,
        target_table: str,
        from_table: Optional[str] = None,
        from_wa: Optional[str] = None,
        set_assignments: Optional[Dict[str, List[Token]]] = None,
        where_tokens: Optional[List[Token]] = None,
        line: int = 1,
    ):
        super().__init__(line)
        self.target_table = target_table.upper()
        self.from_table = from_table.upper() if from_table else None
        self.from_wa = from_wa.upper() if from_wa else None
        self.set_assignments = set_assignments or {}
        self.where_tokens = where_tokens


class ModifyNode(ASTNode):
    def __init__(
        self,
        target_table: str,
        source_var: Optional[str] = None,
        index_expr: Optional[List[Token]] = None,
        from_table: Optional[str] = None,
        is_dbtab: bool = False,
        line: int = 1,
    ):
        super().__init__(line)
        self.target_table = target_table.upper()
        self.source_var = source_var.upper() if source_var else None
        self.index_expr = index_expr
        self.from_table = from_table.upper() if from_table else None
        self.is_dbtab = is_dbtab


class DeleteNode(ASTNode):
    def __init__(
        self,
        target_table: str,
        index_expr: Optional[List[Token]] = None,
        where_tokens: Optional[List[Token]] = None,
        is_dbtab: bool = False,
        from_table: Optional[str] = None,
        from_wa: Optional[str] = None,
        line: int = 1,
    ):
        super().__init__(line)
        self.target_table = target_table.upper()
        self.index_expr = index_expr
        self.where_tokens = where_tokens
        self.is_dbtab = is_dbtab
        self.from_table = from_table.upper() if from_table else None
        self.from_wa = from_wa.upper() if from_wa else None


class CommitWorkNode(ASTNode):
    def __init__(self, and_wait: bool = False, line: int = 1):
        super().__init__(line)
        self.and_wait = and_wait


class RollbackWorkNode(ASTNode):
    def __init__(self, line: int = 1):
        super().__init__(line)


class SortNode(ASTNode):
    def __init__(self, table_name: str, field_names: List[str], descending: bool, line: int):
        super().__init__(line)
        self.table_name = table_name.upper()
        self.field_names = [f.upper() for f in field_names]
        self.descending = descending


class ClearNode(ASTNode):
    def __init__(self, target_name: str, line: int):
        super().__init__(line)
        self.target_name = target_name.upper()


class SelectNode(ASTNode):
    def __init__(
        self,
        fields: List[str],
        from_table: str,
        from_alias: Optional[str] = None,
        joins: Optional[List[Dict[str, Any]]] = None,
        into_table: Optional[str] = None,
        into_wa: Optional[str] = None,
        into_corresponding: bool = False,
        where_tokens: Optional[List[Token]] = None,
        order_by: Optional[str] = None,
        descending: bool = False,
        up_to_rows: Optional[int] = None,
        line: int = 1,
    ):
        super().__init__(line)
        self.fields = [f.upper() for f in fields]
        self.from_table = from_table.upper()
        self.from_alias = from_alias.upper() if from_alias else None
        self.joins = joins or []
        self.into_table = into_table.upper() if into_table else None
        self.into_wa = into_wa.upper() if into_wa else None
        self.into_corresponding = into_corresponding
        self.where_tokens = where_tokens
        self.order_by = order_by.upper() if order_by else None
        self.descending = descending
        self.up_to_rows = up_to_rows


class FormNode(ASTNode):
    def __init__(self, name: str, params: List[str], body: List[ASTNode], line: int):
        super().__init__(line)
        self.name = name.upper()
        self.params = [p.upper() for p in params]
        self.body = body


class PerformNode(ASTNode):
    def __init__(self, name: str, actual_params: List[List[Token]], line: int):
        super().__init__(line)
        self.name = name.upper()
        self.actual_params = actual_params


class ExitNode(ASTNode):
    pass


class ContinueNode(ASTNode):
    pass


class InterfaceDefNode(ASTNode):
    def __init__(self, name: str, methods: List[Dict[str, Any]], attributes: List[Any], interfaces: Optional[List[str]] = None, line: int = 1):
        super().__init__(line)
        self.name = name.upper()
        self.methods = methods
        self.attributes = attributes
        self.interfaces = [i.upper() for i in (interfaces or [])]


class ClassDefNode(ASTNode):
    def __init__(
        self,
        name: str,
        methods: List[Dict[str, Any]],
        attributes: List[Any],
        superclass: Optional[str] = None,
        is_abstract: bool = False,
        is_final: bool = False,
        interfaces: Optional[List[str]] = None,
        create_visibility: str = "PUBLIC",
        line: int = 1,
    ):
        super().__init__(line)
        self.name = name.upper()
        self.methods = methods
        self.attributes = attributes
        self.superclass = superclass.upper() if superclass else None
        self.is_abstract = is_abstract
        self.is_final = is_final
        self.interfaces = [i.upper() for i in (interfaces or [])]
        self.create_visibility = create_visibility.upper()


class ClassImplNode(ASTNode):
    def __init__(self, name: str, methods: Dict[str, Any], line: int):
        super().__init__(line)
        self.name = name.upper()
        self.methods = methods


class MethodImplNode(ASTNode):
    def __init__(self, class_name: str, method_name: str, body: List[ASTNode], line: int):
        super().__init__(line)
        self.class_name = class_name.upper()
        self.method_name = method_name.upper()
        self.body = body


class CreateObjectNode(ASTNode):
    def __init__(self, target_var: str, class_name: Optional[str] = None, exporting: Optional[Dict[str, List[Token]]] = None, line: int = 1):
        super().__init__(line)
        self.target_var = target_var.upper()
        self.class_name = class_name.upper() if class_name else None
        self.exporting = exporting or {}


class CallMethodNode(ASTNode):
    def __init__(self, target_obj: str, method_name: str, is_static: bool = False,
                 exporting: Optional[Dict[str, List[Token]]] = None,
                 receiving: Optional[str] = None,
                 assign_to: Optional[str] = None, line: int = 1):
        super().__init__(line)
        self.target_obj = target_obj.upper()
        self.method_name = method_name.upper()
        self.is_static = is_static
        self.exporting = exporting or {}
        self.receiving = receiving.upper() if receiving else None
        self.assign_to = assign_to.upper() if assign_to else None


class TryNode(ASTNode):
    def __init__(
        self,
        try_body: List[ASTNode],
        catch_branches: List[Dict[str, Any]],
        cleanup_body: Optional[List[ASTNode]] = None,
        line: int = 1,
    ):
        super().__init__(line)
        self.try_body = try_body
        self.catch_branches = catch_branches
        self.cleanup_body = cleanup_body or []


class RaiseExceptionNode(ASTNode):
    def __init__(self, exc_class: str, message: str = "", line: int = 1):
        super().__init__(line)
        self.exc_class = exc_class.upper()
        self.message = message


class ParserDiagnostic:
    def __init__(self, line: int, severity: str, message: str, column: Optional[int] = None, code: str = "ABAP_SYNTAX_ERROR"):
        self.line = line
        self.severity = severity  # 'error', 'warning', 'info'
        self.message = message
        self.column = column
        self.code = code


class ABAPParser:
    BUILTIN_NAMES = {
        "ABAP_TRUE", "ABAP_FALSE", "SPACE", "INITIAL", "NEW", "CONV", "VALUE",
        "AND", "OR", "NOT", "IS", "EQ", "NE", "LT", "LE", "GT", "GE",
        "IN", "BETWEEN", "CP", "NP", "CO", "CA", "CS", "NS", "NA", "BYTE-ORDER",
        "ME", "SUPER", "TO", "UNDER", "AT", "AS", "CURRENCY", "DECIMALS",
        "UNIT", "CHECKBOX", "HOTSPOT", "COLOR", "INTENSIFIED", "INVERSE",
        "QUICKINFO", "EXPONENT", "USING", "MASK", "NO", "GAP", "EDIT",
        "LEFT-JUSTIFIED", "RIGHT-JUSTIFIED", "CENTERED", "NO-GAP", "NO-SIGN",
        "NO-ZERO", "NO-HEADING", "NO-TITLE", "DD/MM/YYYY", "MM/DD/YYYY",
        "COMMIT", "ROLLBACK", "WORK", "WAIT", "TABLE", "INTO", "FROM", "SET", "VALUES",
        "ACCEPTING", "DUPLICATE", "KEYS",
        "BOUND", "INSTANCE", "OF", "ASSIGNED", "SUPPLIED", "REQUESTED",
    }

    def __init__(self, statements: List[Statement]):
        self.statements = statements
        self.pos = 0
        self.diagnostics: List[ParserDiagnostic] = []
        self.declared_names = {"SY-SUBRC", "SY-DATUM", "SY-UZEIT", "SY-INDEX", "SY-TABIX", "SY-DBCNT", "SY-MANDT", "SY-UNAME", "SY-TITLE", "SY-PAGNO", "SY-LINNO"}
        self.symbol_types: Dict[str, Dict[str, Any]] = {}

    def _resolve_like_line_type(self, target_name: str) -> str:
        clean = target_name.upper().strip()
        if clean in self.symbol_types:
            sym = self.symbol_types[clean]
            if sym.get("is_table"):
                return sym.get("line_type") or sym.get("type") or clean
            return sym.get("type") or clean
        return clean

    def parse(self) -> List[ASTNode]:
        nodes = []
        while not self.is_at_end():
            node = self.parse_statement()
            if node:
                nodes.append(node)
        return nodes

    def current_statement(self) -> Optional[Statement]:
        if self.pos < len(self.statements):
            return self.statements[self.pos]
        return None

    def is_at_end(self) -> bool:
        return self.pos >= len(self.statements)

    def _check_variable_refs(self, tokens: List[Token]):
        """Report unresolved simple variable names in expressions we understand."""
        for index, token in enumerate(tokens):
            if token.type != TokenType.IDENTIFIER:
                continue
            name = token.value.upper()
            if name in ("ME", "SUPER"):
                continue
            if name in self.declared_names or name in self.BUILTIN_NAMES or name.startswith("SY-"):
                continue
            if index >= 2 and tokens[index - 1].value.upper() == "OF" and tokens[index - 2].value.upper() == "INSTANCE":
                continue
            if index and tokens[index - 1].value.upper() in ("TYPE", "LIKE"):
                continue
            if "~" in name:
                continue
            if name.startswith(("LINES(", "STRLEN(", "TRIM(", "TO_UPPER(", "TO_LOWER(")):
                continue
            if any(operator in name for operator in ("->", "=>", "-")):
                root = re.split(r"->|=>|-", name, maxsplit=1)[0]
                if root in self.declared_names or root.startswith("SY-"):
                    continue
            if index and tokens[index - 1].value in ("->", "=>", "~"):
                continue
            if index + 1 < len(tokens) and tokens[index + 1].value in ("=>", "~"):
                continue
            if index + 1 < len(tokens) and tokens[index + 1].value == "(":
                continue
            self.diagnostics.append(ParserDiagnostic(
                line=token.line,
                column=token.column,
                severity="error",
                message=f"'{token.value}' is not declared in this program.",
                code="ABAP_UNDEFINED_NAME",
            ))

    def advance(self) -> Optional[Statement]:
        if not self.is_at_end():
            stmt = self.statements[self.pos]
            self.pos += 1
            return stmt
        return None

    def parse_statement(self) -> Optional[ASTNode]:
        stmt = self.advance()
        if not stmt or not stmt.tokens:
            return None

        first_tok = stmt.tokens[0]
        first_word = first_tok.value.upper()
        line = stmt.line

        if not stmt.terminated:
            last_tok = stmt.tokens[-1]
            self.diagnostics.append(ParserDiagnostic(
                line=last_tok.line,
                # A missing character has no source range. Anchor the marker to
                # the final token so editors can render a visible squiggle.
                column=last_tok.column,
                severity="error",
                message="Missing period at the end of the ABAP statement.",
                code="ABAP_MISSING_PERIOD",
            ))

        # 1. REPORT
        if first_word in ("REPORT", "PROGRAM"):
            name = stmt.tokens[1].value if len(stmt.tokens) > 1 else "Z_REPORT"
            return ReportNode(name, line)

        # 2. Section Headers (pass-through / informational)
        if first_word in ("START-OF-SELECTION", "INITIALIZATION", "TOP-OF-PAGE", "END-OF-SELECTION"):
            return None

        # 3. Inline DATA(var) = ...
        if first_word == "DATA" and len(stmt.tokens) > 4 and stmt.tokens[1].value == "(" and stmt.tokens[3].value == ")" and any(t.value == "=" for t in stmt.tokens):
            target_var = stmt.tokens[2].value
            self.declared_names.add(target_var.upper())
            eq_idx = next(i for i, t in enumerate(stmt.tokens) if t.value == "=")
            expr = stmt.tokens[eq_idx + 1 :]
            if expr and expr[0].value.upper() == "NEW":
                cls_name = None
                if len(expr) > 1 and expr[1].value not in ("#", "("):
                    cls_name = expr[1].value.upper()
                return CreateObjectNode(target_var, cls_name, {}, line)
            if any(t.value in ("->", "=>") for t in expr):
                return self._parse_inline_method_call(Statement(raw_text=stmt.raw_text, tokens=expr, line=line), assign_to=target_var)
            return AssignNode(target_var, expr, line)

        # 3b. DATA
        if first_word == "DATA":
            return self._parse_data_statement(stmt)

        # 4. CONSTANTS
        if first_word == "CONSTANTS":
            return self._parse_constants_statement(stmt)

        # 5. TYPES
        if first_word == "TYPES":
            return self._parse_types_statement(stmt)

        # 6. WRITE
        if first_word == "WRITE":
            return self._parse_write_statement(stmt)

        # 7. ULINE
        if first_word == "ULINE":
            return UlineNode(line)

        # 8. SKIP
        if first_word == "SKIP":
            count = 1
            if len(stmt.tokens) > 1 and stmt.tokens[1].type == TokenType.NUMBER:
                try:
                    count = int(stmt.tokens[1].value)
                except ValueError:
                    count = 1
            return SkipNode(count, line)

        # 9. CLEAR
        if first_word in ("CLEAR", "REFRESH", "FREE"):
            target = stmt.tokens[1].value if len(stmt.tokens) > 1 else ""
            return ClearNode(target, line)

        # 9b. TRY / CATCH / ENDTRY
        if first_word == "TRY":
            return self._parse_try_block(stmt)

        if first_word in ("CATCH", "CLEANUP", "ENDTRY"):
            self.diagnostics.append(
                ParserDiagnostic(
                    line=line,
                    severity="error",
                    message=f"ABAP statement '{first_word}' must be enclosed within a TRY ... ENDTRY block.",
                )
            )
            return None

        # 10. IF
        if first_word == "IF":
            return self._parse_if_block(stmt)

        # 11. CASE
        if first_word == "CASE":
            return self._parse_case_block(stmt)

        # 12. DO
        if first_word == "DO":
            return self._parse_do_block(stmt)

        # 13. WHILE
        if first_word == "WHILE":
            return self._parse_while_block(stmt)

        # 14. LOOP
        if first_word == "LOOP":
            return self._parse_loop_block(stmt)

        # 15. READ TABLE
        if first_word == "READ" and len(stmt.tokens) > 1 and stmt.tokens[1].value.upper() == "TABLE":
            return self._parse_read_table(stmt)

        # 16. APPEND
        if first_word == "APPEND":
            return self._parse_append(stmt)

        # 16b. INSERT (Open SQL or internal table)
        if first_word == "INSERT":
            return self._parse_insert(stmt)

        # 16c. UPDATE (Open SQL)
        if first_word == "UPDATE":
            return self._parse_update(stmt)

        # 17. MODIFY
        if first_word == "MODIFY":
            return self._parse_modify(stmt)

        # 18. DELETE
        if first_word == "DELETE":
            return self._parse_delete(stmt)

        # 19. SORT
        if first_word == "SORT":
            return self._parse_sort(stmt)

        # 20. SELECT
        if first_word == "SELECT":
            return self._parse_select(stmt)

        # 20b. COMMIT WORK
        if first_word == "COMMIT":
            and_wait = any(t.value.upper() == "WAIT" for t in stmt.tokens)
            return CommitWorkNode(and_wait=and_wait, line=line)

        # 20c. ROLLBACK WORK
        if first_word == "ROLLBACK":
            return RollbackWorkNode(line=line)

        # 21. FORM / ENDFORM
        if first_word == "FORM":
            return self._parse_form_block(stmt)

        # 22. PERFORM
        if first_word == "PERFORM":
            return self._parse_perform(stmt)

        # 22b. OOP: INTERFACE DEFINITION
        if first_word == "INTERFACE":
            return self._parse_interface_block(stmt)

        # 23. OOP: CLASS DEFINITION / IMPLEMENTATION
        if first_word == "CLASS":
            return self._parse_class_block(stmt)

        # 24. OOP: CREATE OBJECT
        if first_word == "CREATE" and len(stmt.tokens) > 1 and stmt.tokens[1].value.upper() == "OBJECT":
            return self._parse_create_object(stmt)

        # 25. OOP: CALL METHOD
        if first_word == "CALL" and len(stmt.tokens) > 1 and stmt.tokens[1].value.upper() == "METHOD":
            return self._parse_call_method(stmt)

        # 25b. OOP: RAISE EXCEPTION
        if first_word == "RAISE" and len(stmt.tokens) > 1 and stmt.tokens[1].value.upper() == "EXCEPTION":
            return self._parse_raise_exception(stmt)

        # 26. Control statements
        if first_word == "EXIT":
            return ExitNode(line)
        if first_word == "CONTINUE":
            return ContinueNode(line)

        # 27. Determine if statement is an assignment (top-level '=') or a direct method call
        top_level_eq_idx = -1
        bracket_depth = 0
        for idx, t in enumerate(stmt.tokens):
            if t.value in ("(", "["):
                bracket_depth += 1
            elif t.value in (")", "]"):
                bracket_depth -= 1
            elif t.value == "=" and bracket_depth == 0:
                top_level_eq_idx = idx
                break

        # If it has -> or => and no top-level '=', it is a direct method call statement!
        if top_level_eq_idx == -1 and any(t.value in ("->", "=>") for t in stmt.tokens):
            return self._parse_inline_method_call(stmt)

        # 28. Assignment (target = expr)
        if top_level_eq_idx != -1:
            target_tokens = stmt.tokens[:top_level_eq_idx]
            target = "".join(t.value for t in target_tokens)
            expr = stmt.tokens[top_level_eq_idx + 1 :]
            # Check for NEW #( ) or NEW class( )
            if expr and expr[0].value.upper() == "NEW":
                cls_name = None
                if len(expr) > 1 and expr[1].value not in ("#", "("):
                    cls_name = expr[1].value.upper()
                return CreateObjectNode(target, cls_name, {}, line)
            # Check for method call return assignment: target = lo_obj->calc( ... )
            if any(t.value in ("->", "=>") for t in expr) and "(" in [t.value for t in expr]:
                return self._parse_inline_method_call(Statement(raw_text=stmt.raw_text, tokens=expr, line=line), assign_to=target)
            self._check_variable_refs(target_tokens)
            self._check_variable_refs(expr)
            return AssignNode(target, expr, line)

        # Check if first word is a known unsupported statement keyword (pass-through / informational)
        UNSUPPORTED_KEYWORDS = {
            "AUTHORITY-CHECK", "CALL", "SUBMIT", "LEAVE", "MESSAGE", "GET", "SET",
            "PARAMETERS", "SELECT-OPTIONS", "SELECTION-SCREEN", "INCLUDE", "TYPE-POOLS",
            "TABLES", "STATICS", "FIELD-SYMBOLS", "ASSIGN", "UNASSIGN",
        }
        col = stmt.tokens[0].column if stmt.tokens else 1
        if first_word in UNSUPPORTED_KEYWORDS:
            self.diagnostics.append(
                ParserDiagnostic(
                    line=line,
                    column=col,
                    severity="info",
                    message=f"ABAP statement starting with '{first_word}' recognized by simulator.",
                )
            )
            return None

        # Unknown or invalid statement
        self.diagnostics.append(
            ParserDiagnostic(
                line=line,
                column=col,
                severity="error",
                message=f"Statement '{first_word}' is not valid ABAP syntax.",
                code="ABAP_UNSUPPORTED_STATEMENT",
            )
        )
        return None

    def _parse_data_statement(self, stmt: Statement) -> DataDeclNode:
        # DATA var_name TYPE type [VALUE val]
        # DATA var_name LIKE other_var [VALUE val]
        # DATA table_name TYPE [STANDARD|SORTED|HASHED] TABLE OF struc_type [WITH [EMPTY|DEFAULT|UNIQUE|NON-UNIQUE] KEY [fields...]]
        # DATA table_name LIKE [STANDARD|SORTED|HASHED] TABLE OF wa [WITH ...]
        tokens = stmt.tokens[1:]  # skip DATA
        if not tokens:
            self.diagnostics.append(ParserDiagnostic(stmt.line, "error", "DATA declaration is missing a variable name."))
            return DataDeclNode("", "STRING", line=stmt.line)

        # Check for DATA: BEGIN OF struc_name ... END OF struc_name
        if len(tokens) >= 3 and tokens[0].value.upper() == "BEGIN" and tokens[1].value.upper() == "OF":
            struc_name = tokens[2].value.upper()
            self.declared_names.add(struc_name)
            fields: List[Dict[str, str]] = []

            while not self.is_at_end():
                next_stmt = self.current_statement()
                if not next_stmt or not next_stmt.tokens:
                    self.advance()
                    continue

                f_first = next_stmt.tokens[0].value.upper()
                f_tokens = next_stmt.tokens[1:] if f_first == "DATA" else next_stmt.tokens

                # Check for END OF struc_name
                if len(f_tokens) >= 3 and f_tokens[0].value.upper() == "END" and f_tokens[1].value.upper() == "OF":
                    self.advance()
                    break

                self.advance()
                if f_tokens:
                    fld_name = f_tokens[0].value.upper()
                    fld_type = "STRING"
                    if len(f_tokens) >= 3 and f_tokens[1].value.upper() in ("TYPE", "LIKE"):
                        fld_type = f_tokens[2].value.upper()
                    fields.append({"name": fld_name, "type": fld_type, "field": fld_name})

            self.symbol_types[struc_name] = {
                "is_structure": True,
                "fields": [f["name"] for f in fields],
                "fields_detail": fields,
                "type": struc_name,
            }
            node = DataDeclNode(struc_name, struc_name, line=stmt.line)
            node.structure_fields = fields
            return node

        var_name = tokens[0].value.upper()
        i = 1
        # Handle length specification like DATA lv_str(10) TYPE c
        if i + 2 < len(tokens) and tokens[i].value == "(" and tokens[i + 2].value == ")":
            i += 3

        self.declared_names.add(var_name)
        var_type = "STRING"
        line_type = "STRING"
        initial_val = None
        is_table = False
        table_type = "standard"
        like_var = None
        key_def: Optional[Dict[str, Any]] = None

        while i < len(tokens):
            tok_val = tokens[i].value.upper()
            if tok_val in ("TYPE", "LIKE"):
                is_like = (tok_val == "LIKE")
                i += 1
                if i >= len(tokens):
                    self.diagnostics.append(
                        ParserDiagnostic(stmt.line, "error", f"Expected type or data object name after {tok_val}.")
                    )
                    break

                next_tok = tokens[i].value.upper()
                if next_tok in ("STANDARD", "SORTED", "HASHED") and i + 3 < len(tokens) and tokens[i + 1].value.upper() == "TABLE" and tokens[i + 2].value.upper() == "OF":
                    is_table = True
                    table_type = next_tok.lower()
                    target_name = tokens[i + 3].value.upper()
                    i += 4
                    if is_like:
                        like_var = target_name
                        line_type = self._resolve_like_line_type(target_name)
                        var_type = line_type
                    else:
                        line_type = target_name
                        var_type = target_name
                    continue
                elif next_tok == "TABLE" and i + 2 < len(tokens) and tokens[i + 1].value.upper() == "OF":
                    is_table = True
                    table_type = "standard"
                    target_name = tokens[i + 2].value.upper()
                    i += 3
                    if is_like:
                        like_var = target_name
                        line_type = self._resolve_like_line_type(target_name)
                        var_type = line_type
                    else:
                        line_type = target_name
                        var_type = target_name
                    continue
                elif next_tok == "REF" and i + 2 < len(tokens) and tokens[i + 1].value.upper() == "TO":
                    var_type = f"REF_TO_{tokens[i + 2].value.upper()}"
                    line_type = var_type
                    i += 3
                    continue
                else:
                    if is_like:
                        like_var = next_tok
                        var_type = self._resolve_like_line_type(next_tok)
                        line_type = var_type
                    else:
                        var_type = next_tok
                        line_type = next_tok
                    i += 1
                    continue

            elif tok_val == "WITH":
                # Parse WITH [EMPTY|DEFAULT|UNIQUE|NON-UNIQUE] KEY [fields...]
                i += 1
                key_kind = "DEFAULT"
                key_fields: List[str] = []
                if i < len(tokens):
                    sub_tok = tokens[i].value.upper()
                    if sub_tok == "EMPTY" and i + 1 < len(tokens) and tokens[i + 1].value.upper() == "KEY":
                        key_kind = "EMPTY"
                        i += 2
                    elif sub_tok == "DEFAULT" and i + 1 < len(tokens) and tokens[i + 1].value.upper() == "KEY":
                        key_kind = "DEFAULT"
                        i += 2
                    elif sub_tok in ("UNIQUE", "NON-UNIQUE") and i + 1 < len(tokens) and tokens[i + 1].value.upper() == "KEY":
                        key_kind = sub_tok
                        i += 2
                        while i < len(tokens) and tokens[i].value.upper() not in ("INITIAL", "VALUE", "WITH"):
                            key_fields.append(tokens[i].value.upper())
                            i += 1
                    elif sub_tok == "NON" and i + 2 < len(tokens) and tokens[i + 1].value.upper() == "UNIQUE" and tokens[i + 2].value.upper() == "KEY":
                        key_kind = "NON-UNIQUE"
                        i += 3
                        while i < len(tokens) and tokens[i].value.upper() not in ("INITIAL", "VALUE", "WITH"):
                            key_fields.append(tokens[i].value.upper())
                            i += 1
                    elif sub_tok == "KEY":
                        key_kind = "DEFAULT"
                        i += 1
                        while i < len(tokens) and tokens[i].value.upper() not in ("INITIAL", "VALUE", "WITH"):
                            key_fields.append(tokens[i].value.upper())
                            i += 1
                key_def = {"kind": key_kind, "fields": key_fields}
                continue

            elif tok_val == "INITIAL" and i + 1 < len(tokens) and tokens[i + 1].value.upper() == "SIZE":
                i += 3  # skip INITIAL SIZE <n>
                continue

            elif tok_val == "VALUE":
                if i + 1 < len(tokens):
                    initial_val = tokens[i + 1].value
                    i += 2
                else:
                    i += 1
                continue

            i += 1

        # Check LIKE variable existence
        if like_var and like_var not in self.declared_names and like_var not in self.BUILTIN_NAMES and not like_var.startswith("SY-"):
            self.diagnostics.append(
                ParserDiagnostic(stmt.line, "error", f"Field '{like_var}' is unknown.", code="ABAP_UNDEFINED_NAME")
            )

        # Validate table key rules
        if is_table:
            if table_type == "hashed":
                if not key_def:
                    self.diagnostics.append(
                        ParserDiagnostic(
                            stmt.line,
                            "error",
                            f"For hashed table '{var_name}', a unique key must be specified (WITH UNIQUE KEY ...).",
                            code="ABAP_HASHED_TABLE_KEY",
                        )
                    )
                else:
                    if key_def.get("kind") != "UNIQUE":
                        self.diagnostics.append(
                            ParserDiagnostic(
                                stmt.line,
                                "error",
                                f"Hashed table '{var_name}' must have a UNIQUE KEY.",
                                code="ABAP_HASHED_TABLE_KEY",
                            )
                        )
                    if not key_def.get("fields"):
                        self.diagnostics.append(
                            ParserDiagnostic(
                                stmt.line,
                                "error",
                                f"Hashed table '{var_name}' key specification must contain at least one key field.",
                                code="ABAP_HASHED_TABLE_KEY",
                            )
                        )
            elif table_type == "sorted":
                if not key_def:
                    self.diagnostics.append(
                        ParserDiagnostic(
                            stmt.line,
                            "error",
                            f"For sorted table '{var_name}', a key specification (WITH UNIQUE KEY or WITH NON-UNIQUE KEY) is required.",
                            code="ABAP_SORTED_TABLE_KEY",
                        )
                    )
                else:
                    if key_def.get("kind") in ("EMPTY", "DEFAULT"):
                        self.diagnostics.append(
                            ParserDiagnostic(
                                stmt.line,
                                "error",
                                f"Sorted table '{var_name}' does not allow EMPTY KEY or DEFAULT KEY. Specify UNIQUE KEY or NON-UNIQUE KEY.",
                                code="ABAP_SORTED_TABLE_KEY",
                            )
                        )
                    elif not key_def.get("fields"):
                        self.diagnostics.append(
                            ParserDiagnostic(
                                stmt.line,
                                "error",
                                f"Sorted table '{var_name}' key specification must contain at least one key field.",
                                code="ABAP_SORTED_TABLE_KEY",
                            )
                        )
            elif table_type == "standard":
                if key_def and key_def.get("kind") == "UNIQUE":
                    self.diagnostics.append(
                        ParserDiagnostic(
                            stmt.line,
                            "error",
                            f"Standard table '{var_name}' cannot have a UNIQUE KEY. Use NON-UNIQUE KEY, EMPTY KEY, or DEFAULT KEY.",
                            code="ABAP_STANDARD_TABLE_KEY",
                        )
                    )
                elif not key_def:
                    key_def = {"kind": "DEFAULT", "fields": []}

        self.symbol_types[var_name] = {
            "is_table": is_table,
            "table_type": table_type,
            "line_type": line_type,
            "type": var_type,
            "like_var": like_var,
            "key_def": key_def or {},
        }

        return DataDeclNode(
            var_name=var_name,
            var_type=var_type,
            initial_value=initial_val,
            is_table=is_table,
            table_type=table_type,
            line_type=line_type,
            like_var=like_var,
            key_def=key_def,
            line=stmt.line,
        )

    def _parse_constants_statement(self, stmt: Statement) -> ConstantsDeclNode:
        tokens = stmt.tokens[1:]
        if not tokens:
            self.diagnostics.append(ParserDiagnostic(stmt.line, "error", "CONSTANTS declaration is missing a name."))
            return ConstantsDeclNode("C_VALUE", "STRING", None, stmt.line)
        const_name = tokens[0].value.upper()
        self.declared_names.add(const_name)
        const_type = "STRING"
        value = None

        i = 1
        while i < len(tokens):
            tok_val = tokens[i].value.upper()
            if tok_val == "TYPE" and i + 1 < len(tokens):
                const_type = tokens[i + 1].value.upper()
                i += 2
                continue
            elif tok_val == "VALUE" and i + 1 < len(tokens):
                value = tokens[i + 1].value
                i += 2
                continue
            i += 1

        return ConstantsDeclNode(const_name, const_type, value, stmt.line)

    def _parse_types_statement(self, stmt: Statement) -> TypesDeclNode:
        tokens = stmt.tokens[1:]  # skip TYPES
        if not tokens:
            return TypesDeclNode("TY_DATA", [], stmt.line)

        # Check for TYPES BEGIN OF ty_name
        if len(tokens) >= 3 and tokens[0].value.upper() == "BEGIN" and tokens[1].value.upper() == "OF":
            type_name = tokens[2].value.upper()
            self.declared_names.add(type_name)
            fields: List[Dict[str, str]] = []

            while not self.is_at_end():
                next_stmt = self.current_statement()
                if not next_stmt or not next_stmt.tokens:
                    self.advance()
                    continue

                f_first = next_stmt.tokens[0].value.upper()
                f_tokens = next_stmt.tokens[1:] if f_first == "TYPES" else next_stmt.tokens

                # Check for END OF ty_name
                if len(f_tokens) >= 3 and f_tokens[0].value.upper() == "END" and f_tokens[1].value.upper() == "OF":
                    self.advance()
                    break

                self.advance()
                if f_tokens:
                    fld_name = f_tokens[0].value.upper()
                    fld_type = "STRING"
                    if len(f_tokens) >= 3 and f_tokens[1].value.upper() in ("TYPE", "LIKE"):
                        fld_type = f_tokens[2].value.upper()
                    fields.append({"name": fld_name, "type": fld_type, "field": fld_name})

            self.symbol_types[type_name] = {
                "is_structure": True,
                "fields": [f["name"] for f in fields],
                "fields_detail": fields,
                "type": type_name,
            }
            return TypesDeclNode(type_name, fields, stmt.line)

        type_name = tokens[0].value.upper()
        self.declared_names.add(type_name)
        return TypesDeclNode(type_name, [], stmt.line)

    def _parse_write_statement(self, stmt: Statement) -> WriteNode:
        items: List[WriteItem] = []
        tokens = stmt.tokens[1:]  # skip WRITE

        # Coalesce compound tokens like lo_car->mv_speed or lo_car->get_info() or ls_emp-name
        coalesced: List[Token] = []
        k = 0
        while k < len(tokens):
            if tokens[k].type == TokenType.IDENTIFIER and k + 2 < len(tokens) and tokens[k + 1].value in ("->", "=>") and tokens[k + 2].type == TokenType.IDENTIFIER:
                # Check if followed by parentheses (method call like lo_car->get_info( ))
                if k + 3 < len(tokens) and tokens[k + 3].value == "(":
                    p_end = -1
                    depth = 0
                    for m_idx in range(k + 3, len(tokens)):
                        if tokens[m_idx].value == "(":
                            depth += 1
                        elif tokens[m_idx].value == ")":
                            depth -= 1
                            if depth == 0:
                                p_end = m_idx
                                break
                    if p_end != -1:
                        c_call = "".join(t.value for t in tokens[k : p_end + 1])
                        coalesced.append(Token(TokenType.IDENTIFIER, c_call, tokens[k].line, tokens[k].column))
                        k = p_end + 1
                        continue

                c_val = f"{tokens[k].value}{tokens[k+1].value}{tokens[k+2].value}"
                k_adv = 3
                while k + k_adv + 1 < len(tokens) and tokens[k + k_adv].value in ("->", "=>", "-") and tokens[k + k_adv + 1].type == TokenType.IDENTIFIER:
                    c_val += f"{tokens[k+k_adv].value}{tokens[k+k_adv+1].value}"
                    k_adv += 2
                coalesced.append(Token(TokenType.IDENTIFIER, c_val, tokens[k].line, tokens[k].column))
                k += k_adv
            elif tokens[k].type == TokenType.IDENTIFIER and k + 2 < len(tokens) and tokens[k + 1].value == "-" and tokens[k + 2].type == TokenType.IDENTIFIER:
                c_val = f"{tokens[k].value}-{tokens[k+2].value}"
                coalesced.append(Token(TokenType.IDENTIFIER, c_val, tokens[k].line, tokens[k].column))
                k += 3
            elif tokens[k].type == TokenType.IDENTIFIER and k + 1 < len(tokens) and tokens[k + 1].value == "(":
                p_end = -1
                depth = 0
                for m_idx in range(k + 1, len(tokens)):
                    if tokens[m_idx].value == "(":
                        depth += 1
                    elif tokens[m_idx].value == ")":
                        depth -= 1
                        if depth == 0:
                            p_end = m_idx
                            break
                if p_end != -1:
                    inner_content = "".join(t.value for t in tokens[k + 2 : p_end])
                    c_call = f"{tokens[k].value}({inner_content})"
                    coalesced.append(Token(TokenType.IDENTIFIER, c_call, tokens[k].line, tokens[k].column))
                    k = p_end + 1
                else:
                    coalesced.append(tokens[k])
                    k += 1
            else:
                coalesced.append(tokens[k])
                k += 1

        tokens = coalesced
        self._check_variable_refs(tokens)
        i = 0
        while i < len(tokens):
            tok = tokens[i]
            if tok.value == "/":
                # Slash indicates new line before next output
                if i + 1 < len(tokens):
                    items.append(WriteItem(tokens[i + 1], is_slash=True))
                    i += 2
                else:
                    items.append(WriteItem(Token(TokenType.STRING, "", tok.line, tok.column), is_slash=True))
                    i += 1
            else:
                items.append(WriteItem(tok, is_slash=False))
                i += 1

        return WriteNode(items, stmt.line)

    def _parse_if_block(self, start_stmt: Statement) -> IfNode:
        cond_tokens = start_stmt.tokens[1:]
        self._check_variable_refs(cond_tokens)
        then_body: List[ASTNode] = []
        elseif_branches: List[Dict[str, Any]] = []
        else_body: List[ASTNode] = []

        current_target = then_body
        closed = False

        while not self.is_at_end():
            stmt = self.current_statement()
            if not stmt or not stmt.tokens:
                self.advance()
                continue

            first_word = stmt.tokens[0].value.upper()
            if first_word == "ENDIF":
                self.advance()
                closed = True
                break
            elif first_word == "ELSEIF":
                self.advance()
                elseif_cond = stmt.tokens[1:]
                self._check_variable_refs(elseif_cond)
                elseif_body: List[ASTNode] = []
                elseif_branches.append({"cond": elseif_cond, "body": elseif_body, "line": stmt.line})
                current_target = elseif_body
            elif first_word == "ELSE":
                self.advance()
                current_target = else_body
            else:
                node = self.parse_statement()
                if node:
                    current_target.append(node)

        if not closed:
            self.diagnostics.append(ParserDiagnostic(start_stmt.line, "error", "Missing ENDIF for IF block."))
        return IfNode(cond_tokens, then_body, elseif_branches, else_body, start_stmt.line)

    def _parse_case_block(self, start_stmt: Statement) -> CaseNode:
        expr_tokens = start_stmt.tokens[1:]
        self._check_variable_refs(expr_tokens)
        when_branches: List[Dict[str, Any]] = []
        others_body: List[ASTNode] = []

        current_target = None
        closed = False

        while not self.is_at_end():
            stmt = self.current_statement()
            if not stmt or not stmt.tokens:
                self.advance()
                continue

            first_word = stmt.tokens[0].value.upper()
            if first_word == "ENDCASE":
                self.advance()
                closed = True
                break
            elif first_word == "WHEN":
                self.advance()
                if len(stmt.tokens) > 1 and stmt.tokens[1].value.upper() == "OTHERS":
                    current_target = others_body
                else:
                    when_val = stmt.tokens[1:]
                    when_body: List[ASTNode] = []
                    when_branches.append({"val": when_val, "body": when_body, "line": stmt.line})
                    current_target = when_body
            else:
                node = self.parse_statement()
                if node and current_target is not None:
                    current_target.append(node)

        if not closed:
            self.diagnostics.append(ParserDiagnostic(start_stmt.line, "error", "Missing ENDCASE for CASE block."))
        return CaseNode(expr_tokens, when_branches, others_body, start_stmt.line)

    def _parse_try_block(self, start_stmt: Statement) -> TryNode:
        try_body: List[ASTNode] = []
        catch_branches: List[Dict[str, Any]] = []
        cleanup_body: List[ASTNode] = []
        current_target = try_body
        closed = False

        while not self.is_at_end():
            stmt = self.current_statement()
            if not stmt or not stmt.tokens:
                self.advance()
                continue

            first_word = stmt.tokens[0].value.upper()
            if first_word == "ENDTRY":
                self.advance()
                closed = True
                break
            elif first_word == "CATCH":
                self.advance()
                # CATCH cx_sql_exception [cx_other ...] [INTO lx_sql | INTO DATA(lx_sql)]
                classes: List[str] = []
                target_var = None
                is_inline = False

                tokens = stmt.tokens[1:]
                i = 0
                while i < len(tokens):
                    tk = tokens[i].value.upper()
                    if tk == "INTO":
                        if i + 1 < len(tokens):
                            next_tok = tokens[i + 1].value.upper()
                            if next_tok.startswith("DATA(") or (next_tok == "DATA" and i + 2 < len(tokens) and tokens[i + 2].value == "("):
                                is_inline = True
                                if next_tok.startswith("DATA("):
                                    target_var = next_tok[5:].rstrip(")")
                                    i += 2
                                else:
                                    target_var = tokens[i + 3].value.upper() if i + 3 < len(tokens) else "LX_EXC"
                                    i += 5
                            else:
                                target_var = tokens[i + 1].value.upper()
                                i += 2
                        break
                    else:
                        classes.append(tk)
                        i += 1

                branch_body: List[ASTNode] = []
                if is_inline and target_var:
                    self.declared_names.add(target_var.upper())
                catch_branches.append({
                    "classes": classes if classes else ["CX_ROOT"],
                    "target_var": target_var,
                    "is_inline_decl": is_inline,
                    "body": branch_body,
                    "line": stmt.line,
                })
                current_target = branch_body
            elif first_word == "CLEANUP":
                self.advance()
                current_target = cleanup_body
            else:
                node = self.parse_statement()
                if node:
                    current_target.append(node)

        if not closed:
            self.diagnostics.append(ParserDiagnostic(start_stmt.line, "error", "Missing ENDTRY for TRY block."))
        return TryNode(try_body, catch_branches, cleanup_body, start_stmt.line)

    def _parse_do_block(self, start_stmt: Statement) -> DoNode:
        times_expr = None
        tokens = start_stmt.tokens[1:]
        if len(tokens) >= 2 and tokens[-1].value.upper() == "TIMES":
            times_expr = tokens[:-1]
            self._check_variable_refs(times_expr)

        body: List[ASTNode] = []
        closed = False
        while not self.is_at_end():
            stmt = self.current_statement()
            if not stmt or not stmt.tokens:
                self.advance()
                continue
            if stmt.tokens[0].value.upper() == "ENDDO":
                self.advance()
                closed = True
                break
            node = self.parse_statement()
            if node:
                body.append(node)

        if not closed:
            self.diagnostics.append(ParserDiagnostic(start_stmt.line, "error", "Missing ENDDO for DO block."))
        return DoNode(times_expr, body, start_stmt.line)

    def _parse_while_block(self, start_stmt: Statement) -> WhileNode:
        cond_tokens = start_stmt.tokens[1:]
        self._check_variable_refs(cond_tokens)
        body: List[ASTNode] = []
        closed = False
        while not self.is_at_end():
            stmt = self.current_statement()
            if not stmt or not stmt.tokens:
                self.advance()
                continue
            if stmt.tokens[0].value.upper() == "ENDWHILE":
                self.advance()
                closed = True
                break
            node = self.parse_statement()
            if node:
                body.append(node)

        if not closed:
            self.diagnostics.append(ParserDiagnostic(start_stmt.line, "error", "Missing ENDWHILE for WHILE block."))
        return WhileNode(cond_tokens, body, start_stmt.line)

    def _parse_loop_block(self, start_stmt: Statement) -> LoopNode:
        # LOOP AT itab INTO wa [WHERE ...]
        # LOOP AT itab ASSIGNING <fs>
        tokens = start_stmt.tokens[1:]  # skip LOOP
        table_name = ""
        target_var = None
        assigning_fs = None
        where_tokens = None

        i = 0
        if i < len(tokens) and tokens[i].value.upper() == "AT":
            table_name = tokens[i + 1].value.upper()
            i += 2

        while i < len(tokens):
            w = tokens[i].value.upper()
            if w == "INTO" and i + 1 < len(tokens):
                target_var = tokens[i + 1].value.upper()
                i += 2
            elif w == "ASSIGNING" and i + 1 < len(tokens):
                assigning_fs = tokens[i + 1].value.upper()
                i += 2
            elif w == "WHERE":
                where_tokens = tokens[i + 1 :]
                break
            else:
                i += 1

        body: List[ASTNode] = []
        closed = False
        while not self.is_at_end():
            stmt = self.current_statement()
            if not stmt or not stmt.tokens:
                self.advance()
                continue
            if stmt.tokens[0].value.upper() == "ENDLOOP":
                self.advance()
                closed = True
                break
            node = self.parse_statement()
            if node:
                body.append(node)

        if not closed:
            self.diagnostics.append(ParserDiagnostic(start_stmt.line, "error", "Missing ENDLOOP for LOOP block."))
        return LoopNode(table_name, target_var, assigning_fs, where_tokens, body, start_stmt.line)

    def _parse_read_table(self, stmt: Statement) -> ReadTableNode:
        # READ TABLE itab INTO wa [WITH KEY field = val] [INDEX idx]
        tokens = stmt.tokens[2:]  # skip READ TABLE
        table_name = tokens[0].value.upper()
        target_var = None
        assigning_fs = None
        key_field = None
        key_val_tokens = None
        index_expr = None

        i = 1
        while i < len(tokens):
            w = tokens[i].value.upper()
            if w == "INTO" and i + 1 < len(tokens):
                target_var = tokens[i + 1].value.upper()
                i += 2
            elif w == "ASSIGNING" and i + 1 < len(tokens):
                assigning_fs = tokens[i + 1].value.upper()
                i += 2
            elif w == "INDEX" and i + 1 < len(tokens):
                index_expr = [tokens[i + 1]]
                i += 2
            elif w == "WITH" and i + 3 < len(tokens) and tokens[i + 1].value.upper() == "KEY":
                key_field = tokens[i + 2].value.upper()
                # usually key_field = val
                if tokens[i + 3].value == "=" and i + 4 < len(tokens):
                    key_val_tokens = [tokens[i + 4]]
                    i += 5
                else:
                    key_val_tokens = [tokens[i + 3]]
                    i += 4
            else:
                i += 1

        return ReadTableNode(table_name, target_var, assigning_fs, key_field, key_val_tokens, index_expr, stmt.line)

    def _parse_append(self, stmt: Statement) -> AppendNode:
        # APPEND wa TO itab
        # APPEND INITIAL LINE TO itab ASSIGNING <fs>
        tokens = stmt.tokens[1:]
        source_var = None
        target_table = ""
        initial_line = False
        assigning_fs = None

        source_tokens = None
        if len(tokens) >= 2 and tokens[0].value.upper() == "INITIAL" and tokens[1].value.upper() == "LINE":
            initial_line = True
            tokens = tokens[2:]
        else:
            source_var = tokens[0].value.upper()
            source_tokens = [tokens[0]]
            tokens = tokens[1:]

        i = 0
        while i < len(tokens):
            w = tokens[i].value.upper()
            if w == "TO" and i + 1 < len(tokens):
                target_table = tokens[i + 1].value.upper()
                i += 2
            elif w == "ASSIGNING" and i + 1 < len(tokens):
                assigning_fs = tokens[i + 1].value.upper()
                i += 2
            else:
                i += 1

        # Check target table validity
        if target_table in self.symbol_types:
            target_meta = self.symbol_types[target_table]
            if not target_meta.get("is_table", True):
                self.diagnostics.append(
                    ParserDiagnostic(
                        stmt.line,
                        "error",
                        f"Target '{target_table}' for APPEND must be an internal table.",
                        code="ABAP_NOT_AN_ITAB",
                    )
                )
            elif target_meta.get("table_type") == "hashed":
                self.diagnostics.append(
                    ParserDiagnostic(
                        stmt.line,
                        "error",
                        f"In 'APPEND itab', '{target_table}' must be an index table. Hashed tables cannot be accessed with APPEND.",
                        code="ABAP_APPEND_HASHED_TABLE",
                    )
                )

        # Check source and target compatibility if both are known
        if source_var and source_var in self.symbol_types and target_table in self.symbol_types:
            src_meta = self.symbol_types[source_var]
            tgt_meta = self.symbol_types[target_table]
            if src_meta.get("is_table") and not tgt_meta.get("is_table_of_tables", False):
                self.diagnostics.append(
                    ParserDiagnostic(
                        stmt.line,
                        "error",
                        f"Type conflict in APPEND: source '{source_var}' is an internal table, but '{target_table}' has line type '{tgt_meta.get('line_type')}'.",
                        code="ABAP_TYPE_CONFLICT",
                    )
                )

        return AppendNode(
            source_var=source_var,
            target_table=target_table,
            initial_line=initial_line,
            assigning_fs=assigning_fs,
            source_tokens=source_tokens,
            line=stmt.line,
        )

    def _read_identifier_token(self, tokens: List[Token], start: int) -> Tuple[str, int]:
        """Reads an identifier, host variable (@name), or inline declaration (@DATA(var)), returning (name_upper, next_index)."""
        idx = start
        if idx < len(tokens) and tokens[idx].value == "@":
            idx += 1
        if idx < len(tokens):
            val = tokens[idx].value.upper()
            if val == "DATA" and idx + 3 < len(tokens) and tokens[idx + 1].value == "(" and tokens[idx + 3].value == ")":
                target_var = tokens[idx + 2].value.upper()
                self.declared_names.add(target_var)
                return (target_var, idx + 4)
            if val.startswith("DATA(") and val.endswith(")"):
                target_var = val[5:-1].upper()
                self.declared_names.add(target_var)
                return (target_var, idx + 1)
            clean_name = tokens[idx].value.lstrip("@").upper()
            self.declared_names.add(clean_name)
            return (clean_name, idx + 1)
        return ("", start)

    def _parse_insert(self, stmt: Statement) -> InsertNode:
        # DB:
        # INSERT INTO dbtab FROM TABLE itab
        # INSERT dbtab FROM TABLE itab
        # INSERT INTO dbtab FROM wa
        # INSERT dbtab FROM wa
        # INSERT INTO dbtab VALUES (...)
        # Internal table:
        # INSERT wa INTO TABLE itab
        # INSERT wa INTO itab [INDEX idx]
        tokens = stmt.tokens[1:]
        if not tokens:
            return InsertNode(target_table="", line=stmt.line)

        # Check if first token is INTO
        if tokens[0].value.upper() == "INTO" and len(tokens) > 1:
            target_table, i = self._read_identifier_token(tokens, 1)
            from_table = None
            from_wa = None
            values = None
            while i < len(tokens):
                w = tokens[i].value.upper()
                if w == "FROM" and i + 1 < len(tokens):
                    if tokens[i + 1].value.upper() == "TABLE" and i + 2 < len(tokens):
                        from_table, i = self._read_identifier_token(tokens, i + 2)
                        continue
                    else:
                        from_wa, i = self._read_identifier_token(tokens, i + 1)
                        continue
                elif w == "VALUES" and i + 1 < len(tokens):
                    values = tokens[i + 1 :]
                    break
                i += 1
            return InsertNode(target_table=target_table, from_table=from_table, from_wa=from_wa, values=values, line=stmt.line)

        # First token is not INTO. Check if INTO occurs anywhere in tokens
        into_idx = next((idx for idx, t in enumerate(tokens) if t.value.upper() == "INTO"), -1)
        if into_idx != -1:
            wa_var, _ = self._read_identifier_token(tokens, 0)
            target_table = ""
            index_expr = None
            rest = tokens[into_idx + 1 :]
            if rest and rest[0].value.upper() == "TABLE":
                target_table, _ = self._read_identifier_token(rest, 1)
                idx_pos = next((idx for idx, t in enumerate(rest) if t.value.upper() == "INDEX"), -1)
                if idx_pos != -1 and idx_pos + 1 < len(rest):
                    index_expr = [rest[idx_pos + 1]]
            elif rest:
                target_table, _ = self._read_identifier_token(rest, 0)
                idx_pos = next((idx for idx, t in enumerate(rest) if t.value.upper() == "INDEX"), -1)
                if idx_pos != -1 and idx_pos + 1 < len(rest):
                    index_expr = [rest[idx_pos + 1]]
            return InsertNode(target_table=target_table, is_internal_table=True, wa_var=wa_var, itab_var=target_table, index_expr=index_expr, line=stmt.line)

        # Check if FROM occurs: INSERT dbtab FROM TABLE itab OR INSERT dbtab FROM wa OR INSERT dbtab FROM @wa
        from_idx = next((idx for idx, t in enumerate(tokens) if t.value.upper() == "FROM"), -1)
        if from_idx != -1:
            target_table, _ = self._read_identifier_token(tokens, 0)
            from_table = None
            from_wa = None
            if from_idx + 1 < len(tokens):
                if tokens[from_idx + 1].value.upper() == "TABLE" and from_idx + 2 < len(tokens):
                    from_table, _ = self._read_identifier_token(tokens, from_idx + 2)
                else:
                    from_wa, _ = self._read_identifier_token(tokens, from_idx + 1)
            return InsertNode(target_table=target_table, from_table=from_table, from_wa=from_wa, line=stmt.line)

        target_table, _ = self._read_identifier_token(tokens, 0)
        return InsertNode(target_table=target_table, line=stmt.line)

    def _parse_update(self, stmt: Statement) -> UpdateNode:
        # UPDATE dbtab SET f1 = val1, f2 = val2 ... [WHERE cond]
        # UPDATE dbtab FROM TABLE itab
        # UPDATE dbtab FROM wa
        tokens = stmt.tokens[1:]
        if not tokens:
            return UpdateNode(target_table="", line=stmt.line)
        target_table, _ = self._read_identifier_token(tokens, 0)

        if len(tokens) > 1 and tokens[1].value.upper() == "FROM":
            if len(tokens) > 2 and tokens[2].value.upper() == "TABLE":
                from_table, _ = self._read_identifier_token(tokens, 3)
                return UpdateNode(target_table=target_table, from_table=from_table, line=stmt.line)
            else:
                from_wa, _ = self._read_identifier_token(tokens, 2)
                return UpdateNode(target_table=target_table, from_wa=from_wa, line=stmt.line)

        set_idx = next((idx for idx, t in enumerate(tokens) if t.value.upper() == "SET"), -1)
        if set_idx != -1:
            where_idx = next((idx for idx, t in enumerate(tokens) if t.value.upper() == "WHERE"), -1)
            set_tokens = tokens[set_idx + 1 : where_idx] if where_idx != -1 else tokens[set_idx + 1 :]
            where_tokens = tokens[where_idx + 1 :] if where_idx != -1 else None

            set_assignments: Dict[str, List[Token]] = {}
            chunks: List[List[Token]] = []
            cur_chunk: List[Token] = []
            for t in set_tokens:
                if t.value == ",":
                    if cur_chunk:
                        chunks.append(cur_chunk)
                        cur_chunk = []
                else:
                    cur_chunk.append(t)
            if cur_chunk:
                chunks.append(cur_chunk)

            for chunk in chunks:
                if len(chunk) >= 3 and chunk[1].value == "=":
                    field_name = chunk[0].value.upper()
                    val_tokens = chunk[2:]
                    set_assignments[field_name] = val_tokens

            return UpdateNode(target_table=target_table, set_assignments=set_assignments, where_tokens=where_tokens, line=stmt.line)

        return UpdateNode(target_table=target_table, line=stmt.line)

    def _parse_modify(self, stmt: Statement) -> ModifyNode:
        # MODIFY itab FROM wa INDEX idx
        # MODIFY dbtab FROM TABLE itab
        # MODIFY dbtab FROM wa
        tokens = stmt.tokens[1:]
        target_table, _ = self._read_identifier_token(tokens, 0)
        source_var = None
        from_table = None
        index_expr = None
        is_dbtab = False

        i = 1
        while i < len(tokens):
            w = tokens[i].value.upper()
            if w == "FROM" and i + 1 < len(tokens):
                if tokens[i + 1].value.upper() == "TABLE" and i + 2 < len(tokens):
                    from_table, i = self._read_identifier_token(tokens, i + 2)
                    is_dbtab = True
                    continue
                else:
                    source_var, i = self._read_identifier_token(tokens, i + 1)
                    continue
            elif w == "INDEX" and i + 1 < len(tokens):
                index_expr = [tokens[i + 1]]
                i += 2
                continue
            i += 1

        if from_table:
            is_dbtab = True
        elif source_var and not index_expr and target_table not in self.declared_names:
            is_dbtab = True

        return ModifyNode(
            target_table=target_table,
            source_var=source_var,
            index_expr=index_expr,
            from_table=from_table,
            is_dbtab=is_dbtab,
            line=stmt.line,
        )

    def _parse_delete(self, stmt: Statement) -> DeleteNode:
        # DELETE itab INDEX idx
        # DELETE itab WHERE cond
        # DELETE FROM dbtab [WHERE cond]
        # DELETE dbtab FROM TABLE itab
        # DELETE dbtab FROM wa
        tokens = stmt.tokens[1:]
        if not tokens:
            return DeleteNode(target_table="", line=stmt.line)

        if tokens[0].value.upper() == "FROM" and len(tokens) > 1:
            target_table, _ = self._read_identifier_token(tokens, 1)
            where_tokens = None
            where_idx = next((idx for idx, t in enumerate(tokens) if t.value.upper() == "WHERE"), -1)
            if where_idx != -1:
                where_tokens = tokens[where_idx + 1 :]
            return DeleteNode(target_table=target_table, is_dbtab=True, where_tokens=where_tokens, line=stmt.line)

        target_table, _ = self._read_identifier_token(tokens, 0)
        if len(tokens) > 1 and tokens[1].value.upper() == "FROM":
            if len(tokens) > 2 and tokens[2].value.upper() == "TABLE":
                from_table, _ = self._read_identifier_token(tokens, 3)
                return DeleteNode(target_table=target_table, is_dbtab=True, from_table=from_table, line=stmt.line)
            else:
                from_wa, _ = self._read_identifier_token(tokens, 2)
                return DeleteNode(target_table=target_table, is_dbtab=True, from_wa=from_wa, line=stmt.line)

        index_expr = None
        where_tokens = None
        i = 1
        while i < len(tokens):
            w = tokens[i].value.upper()
            if w == "INDEX" and i + 1 < len(tokens):
                index_expr = [tokens[i + 1]]
                i += 2
            elif w == "WHERE":
                where_tokens = tokens[i + 1 :]
                break
            else:
                i += 1

        is_dbtab = (target_table not in self.declared_names and index_expr is None)
        return DeleteNode(target_table=target_table, index_expr=index_expr, where_tokens=where_tokens, is_dbtab=is_dbtab, line=stmt.line)

    def _parse_sort(self, stmt: Statement) -> SortNode:
        # SORT itab [BY field1 [DESCENDING]]
        tokens = stmt.tokens[1:]
        table_name = tokens[0].value.upper()
        field_names = []
        descending = False

        i = 1
        if i < len(tokens) and tokens[i].value.upper() == "BY":
            i += 1
            while i < len(tokens):
                w = tokens[i].value.upper()
                if w == "DESCENDING":
                    descending = True
                elif w == "ASCENDING":
                    descending = False
                else:
                    field_names.append(w)
                i += 1

        return SortNode(table_name, field_names, descending, stmt.line)

    def _parse_select(self, stmt: Statement) -> SelectNode:
        # SELECT f1, f2 FROM table [AS alias] [JOIN ...] [INTO ...] [WHERE ...] [ORDER BY ...] [UP TO n ROWS]
        tokens = stmt.tokens[1:]
        fields: List[str] = []
        from_table = ""
        from_alias = None
        joins: List[Dict[str, Any]] = []
        into_table = None
        into_wa = None
        into_corresponding = False
        where_tokens = None
        order_by = None
        descending = False
        up_to_rows = None

        i = 0
        # 1. Parse fields (and handle INTO before FROM)
        while i < len(tokens):
            w = tokens[i].value.upper()
            if w == "FROM":
                i += 1
                break
            elif w == "INTO":
                i += 1
                if i < len(tokens) and tokens[i].value.upper() == "CORRESPONDING":
                    i += 1
                    if i < len(tokens) and tokens[i].value.upper() == "FIELDS":
                        i += 1
                    if i < len(tokens) and tokens[i].value.upper() == "OF":
                        i += 1
                    into_corresponding = True

                if i < len(tokens) and tokens[i].value.upper() == "TABLE":
                    i += 1
                    target_name, i = self._read_identifier_token(tokens, i)
                    if target_name.startswith("DATA(") and target_name.endswith(")"):
                        target_name = target_name[5:-1].upper()
                    into_table = target_name
                else:
                    target_name, i = self._read_identifier_token(tokens, i)
                    if target_name.startswith("DATA(") and target_name.endswith(")"):
                        target_name = target_name[5:-1].upper()
                    into_wa = target_name
                continue
            elif w != ",":
                # Handle possible spaced tilde: a ~ col
                if i + 2 < len(tokens) and tokens[i + 1].value == "~":
                    fld_val = f"{tokens[i].value.upper()}~{tokens[i + 2].value.upper()}"
                    fields.append(fld_val)
                    i += 3
                    continue
                else:
                    fields.append(w)
            i += 1

        # 2. Parse from_table and optional alias
        if i < len(tokens):
            from_table = tokens[i].value.upper()
            i += 1
            if i < len(tokens) and tokens[i].value.upper() == "AS":
                i += 1
                if i < len(tokens):
                    from_alias = tokens[i].value.upper()
                    i += 1
            elif i < len(tokens) and tokens[i].value.upper() not in (
                "INNER", "LEFT", "RIGHT", "FULL", "CROSS", "JOIN",
                "WHERE", "ORDER", "GROUP", "INTO", "UP",
            ):
                from_alias = tokens[i].value.upper()
                i += 1

        # 3. Parse zero or more JOIN clauses
        CLAUSE_KEYWORDS = {"WHERE", "ORDER", "GROUP", "INTO", "UP", "INNER", "LEFT", "RIGHT", "FULL", "CROSS", "JOIN"}
        while i < len(tokens) and tokens[i].value.upper() in ("INNER", "LEFT", "RIGHT", "FULL", "CROSS", "JOIN"):
            j_tok = tokens[i].value.upper()
            join_type = "INNER"
            if j_tok == "INNER":
                i += 1
                if i < len(tokens) and tokens[i].value.upper() == "JOIN":
                    i += 1
            elif j_tok in ("LEFT", "RIGHT", "FULL"):
                i += 1
                if i < len(tokens) and tokens[i].value.upper() == "OUTER":
                    i += 1
                if i < len(tokens) and tokens[i].value.upper() == "JOIN":
                    i += 1
                join_type = f"{j_tok} OUTER"
            elif j_tok == "CROSS":
                i += 1
                if i < len(tokens) and tokens[i].value.upper() == "JOIN":
                    i += 1
                join_type = "CROSS"
            elif j_tok == "JOIN":
                i += 1

            if i >= len(tokens):
                break

            j_table = tokens[i].value.upper()
            i += 1
            j_alias = None
            if i < len(tokens) and tokens[i].value.upper() == "AS":
                i += 1
                if i < len(tokens):
                    j_alias = tokens[i].value.upper()
                    i += 1
            elif i < len(tokens) and tokens[i].value.upper() not in ("ON", *CLAUSE_KEYWORDS):
                j_alias = tokens[i].value.upper()
                i += 1

            # Parse ON condition
            on_tokens: List[Token] = []
            if i < len(tokens) and tokens[i].value.upper() == "ON":
                i += 1
                while i < len(tokens) and tokens[i].value.upper() not in ("INNER", "LEFT", "RIGHT", "FULL", "CROSS", "JOIN", "WHERE", "ORDER", "GROUP", "INTO", "UP"):
                    on_tokens.append(tokens[i])
                    i += 1

            joins.append({
                "type": join_type,
                "table": j_table,
                "alias": j_alias,
                "on_tokens": on_tokens,
            })

        # 4. Parse remaining clauses in any order (INTO, WHERE, ORDER BY, UP TO)
        while i < len(tokens):
            w = tokens[i].value.upper()
            if w == "INTO":
                i += 1
                # Check for CORRESPONDING FIELDS OF
                if i < len(tokens) and tokens[i].value.upper() == "CORRESPONDING":
                    i += 1
                    if i < len(tokens) and tokens[i].value.upper() == "FIELDS":
                        i += 1
                    if i < len(tokens) and tokens[i].value.upper() == "OF":
                        i += 1
                    into_corresponding = True

                if i < len(tokens) and tokens[i].value.upper() == "TABLE":
                    i += 1
                    target_name, i = self._read_identifier_token(tokens, i)
                    if target_name.startswith("DATA(") and target_name.endswith(")"):
                        target_name = target_name[5:-1].upper()
                    into_table = target_name
                else:
                    target_name, i = self._read_identifier_token(tokens, i)
                    if target_name.startswith("DATA(") and target_name.endswith(")"):
                        target_name = target_name[5:-1].upper()
                    into_wa = target_name

            elif w == "WHERE":
                i += 1
                w_tokens: List[Token] = []
                while i < len(tokens) and tokens[i].value.upper() not in ("ORDER", "GROUP", "INTO", "UP"):
                    w_tokens.append(tokens[i])
                    i += 1
                where_tokens = w_tokens

            elif w == "ORDER" and i + 1 < len(tokens) and tokens[i + 1].value.upper() == "BY":
                i += 2
                ob_parts: List[str] = []
                while i < len(tokens) and tokens[i].value.upper() not in ("INTO", "WHERE", "UP", "GROUP", "DESCENDING", "DESC", "ASCENDING", "ASC"):
                    if tokens[i].value != ",":
                        ob_parts.append(tokens[i].value.upper())
                    i += 1
                order_by = " ".join(ob_parts) if ob_parts else None
                if i < len(tokens) and tokens[i].value.upper() in ("DESCENDING", "DESC"):
                    descending = True
                    i += 1
                elif i < len(tokens) and tokens[i].value.upper() in ("ASCENDING", "ASC"):
                    descending = False
                    i += 1

            elif w == "UP" and i + 3 < len(tokens) and tokens[i + 1].value.upper() == "TO" and tokens[i + 3].value.upper() == "ROWS":
                try:
                    up_to_rows = int(tokens[i + 2].value)
                except ValueError:
                    up_to_rows = None
                i += 4

            else:
                i += 1

        return SelectNode(
            fields=fields if fields else ["*"],
            from_table=from_table,
            from_alias=from_alias,
            joins=joins,
            into_table=into_table,
            into_wa=into_wa,
            into_corresponding=into_corresponding,
            where_tokens=where_tokens,
            order_by=order_by,
            descending=descending,
            up_to_rows=up_to_rows,
            line=stmt.line,
        )

    def _parse_form_block(self, start_stmt: Statement) -> FormNode:
        name = start_stmt.tokens[1].value.upper() if len(start_stmt.tokens) > 1 else "ROUTINE"
        params = []
        body: List[ASTNode] = []
        closed = False

        while not self.is_at_end():
            stmt = self.current_statement()
            if not stmt or not stmt.tokens:
                self.advance()
                continue
            if stmt.tokens[0].value.upper() == "ENDFORM":
                self.advance()
                closed = True
                break
            node = self.parse_statement()
            if node:
                body.append(node)

        if not closed:
            self.diagnostics.append(ParserDiagnostic(start_stmt.line, "error", "Missing ENDFORM for FORM block."))
        return FormNode(name, params, body, start_stmt.line)

    def _parse_perform(self, stmt: Statement) -> PerformNode:
        name = stmt.tokens[1].value.upper() if len(stmt.tokens) > 1 else "ROUTINE"
        return PerformNode(name, [], stmt.line)

    def _parse_method_signature(self, stmt: Statement, is_static: bool, visibility: str) -> Optional[Dict[str, Any]]:
        tokens = stmt.tokens
        if len(tokens) < 2:
            return None

        # Method name: could be simple (SPEAK) or qualified (ZIF_PRINTABLE~PRINT)
        if len(tokens) > 3 and tokens[2].value == "~":
            m_name = f"{tokens[1].value.upper()}~{tokens[3].value.upper()}"
            i = 4
        else:
            m_name = tokens[1].value.upper()
            i = 2

        is_abstract = False
        is_redefinition = False
        importing: Dict[str, str] = {}
        exporting: Dict[str, str] = {}
        changing: Dict[str, str] = {}
        returning: Optional[Tuple[str, str]] = None
        raising: List[str] = []

        while i < len(tokens):
            tk = tokens[i].value.upper()
            if tk == "ABSTRACT":
                is_abstract = True
                i += 1
            elif tk == "REDEFINITION":
                is_redefinition = True
                i += 1
            elif tk == "IMPORTING":
                i += 1
                params, i = self._parse_param_decl(tokens, i)
                importing.update(params)
            elif tk == "EXPORTING":
                i += 1
                params, i = self._parse_param_decl(tokens, i)
                exporting.update(params)
            elif tk == "CHANGING":
                i += 1
                params, i = self._parse_param_decl(tokens, i)
                changing.update(params)
            elif tk == "RETURNING":
                i += 1
                r_name = "RESULT"
                r_type = "STRING"
                while i < len(tokens) and tokens[i].value.upper() not in ("RAISING", "ABSTRACT", "REDEFINITION", "FOR"):
                    sub = tokens[i].value.upper()
                    if "VALUE(" in sub:
                        r_name = sub[sub.find("(") + 1 : sub.find(")")].strip().upper()
                    elif sub == "VALUE" and i + 2 < len(tokens) and tokens[i + 1].value == "(":
                        r_name = tokens[i + 2].value.upper()
                        i += 2
                    elif sub == "TYPE" and i + 1 < len(tokens):
                        r_type = tokens[i + 1].value.upper()
                        i += 1
                    i += 1
                returning = (r_name, r_type)
                self.declared_names.add(r_name)
            elif tk == "RAISING":
                i += 1
                while i < len(tokens) and tokens[i].value.upper() not in ("ABSTRACT", "REDEFINITION"):
                    val = tokens[i].value.upper()
                    if val not in (",", ":"):
                        raising.append(val)
                    i += 1
            else:
                i += 1

        self.declared_names.update(importing.keys())
        self.declared_names.update(exporting.keys())
        self.declared_names.update(changing.keys())

        return {
            "name": m_name,
            "is_static": is_static,
            "visibility": visibility,
            "is_abstract": is_abstract,
            "is_redefinition": is_redefinition,
            "importing": importing,
            "exporting": exporting,
            "changing": changing,
            "returning": returning,
            "raising": raising,
        }

    def _parse_param_decl(self, tokens: List[Token], start_idx: int) -> Tuple[Dict[str, str], int]:
        params: Dict[str, str] = {}
        i = start_idx
        while i < len(tokens) and tokens[i].value.upper() not in (
            "EXPORTING", "IMPORTING", "CHANGING", "RETURNING", "RAISING", "ABSTRACT", "REDEFINITION", "FOR"
        ):
            tok_val = tokens[i].value.upper()
            if tok_val in (",", ":"):
                i += 1
                continue
            if "VALUE(" in tok_val:
                p_name = tok_val[tok_val.find("(") + 1 : tok_val.find(")")].strip().upper()
            elif tok_val == "VALUE" and i + 2 < len(tokens) and tokens[i + 1].value == "(":
                p_name = tokens[i + 2].value.upper()
                i += 3
            else:
                p_name = tok_val

            p_type = "STRING"
            i += 1
            if i < len(tokens) and tokens[i].value.upper() == "TYPE":
                i += 1
                if i < len(tokens):
                    p_type = tokens[i].value.upper()
                    i += 1
            if i < len(tokens) and tokens[i].value.upper() == "DEFAULT":
                i += 2
            params[p_name] = p_type
            self.declared_names.add(p_name)
        return params, i

    def _parse_class_block(self, start_stmt: Statement) -> Optional[ASTNode]:
        tokens = start_stmt.tokens
        if len(tokens) < 3:
            return None
        class_name = tokens[1].value.upper()
        mode = tokens[2].value.upper()
        self.declared_names.add(class_name)

        if mode == "DEFINITION":
            superclass = None
            is_abstract = False
            is_final = False
            create_visibility = "PUBLIC"

            idx = 3
            while idx < len(tokens):
                tok_upper = tokens[idx].value.upper()
                if tok_upper == "INHERITING" and idx + 2 < len(tokens) and tokens[idx + 1].value.upper() == "FROM":
                    superclass = tokens[idx + 2].value.upper()
                    idx += 3
                elif tok_upper == "ABSTRACT":
                    is_abstract = True
                    idx += 1
                elif tok_upper == "FINAL":
                    is_final = True
                    idx += 1
                elif tok_upper == "CREATE" and idx + 1 < len(tokens) and tokens[idx + 1].value.upper() in ("PUBLIC", "PROTECTED", "PRIVATE"):
                    create_visibility = tokens[idx + 1].value.upper()
                    idx += 2
                else:
                    idx += 1

            methods: List[Dict[str, Any]] = []
            attributes: List[Any] = []
            interfaces: List[str] = []
            current_section = "PUBLIC"

            while not self.is_at_end():
                stmt = self.current_statement()
                if not stmt or not stmt.tokens:
                    self.advance()
                    continue
                first = stmt.tokens[0].value.upper()
                if first == "ENDCLASS":
                    self.advance()
                    break
                self.advance()

                if first in ("PUBLIC", "PROTECTED", "PRIVATE"):
                    current_section = first
                    continue

                if first == "INTERFACES":
                    for t in stmt.tokens[1:]:
                        val = t.value.upper()
                        if val not in (",", ":"):
                            interfaces.append(val)
                    continue

                if first in ("DATA", "CLASS-DATA", "CONSTANTS"):
                    is_static = (first in ("CLASS-DATA", "CONSTANTS"))
                    node = self._parse_data_statement(stmt)
                    if node:
                        setattr(node, "visibility", current_section)
                        setattr(node, "is_static", is_static)
                        attributes.append(node)
                        self.declared_names.add(node.var_name.upper())
                    continue

                if first in ("METHODS", "CLASS-METHODS"):
                    is_static = (first == "CLASS-METHODS")
                    m_info = self._parse_method_signature(stmt, is_static, current_section)
                    if m_info:
                        methods.append(m_info)
                        self.declared_names.add(m_info["name"].upper())
                    continue

            return ClassDefNode(
                name=class_name,
                methods=methods,
                attributes=attributes,
                superclass=superclass,
                is_abstract=is_abstract,
                is_final=is_final,
                interfaces=interfaces,
                create_visibility=create_visibility,
                line=start_stmt.line,
            )

        elif mode == "IMPLEMENTATION":
            methods_dict: Dict[str, Any] = {}
            while not self.is_at_end():
                stmt = self.current_statement()
                if not stmt or not stmt.tokens:
                    self.advance()
                    continue
                first = stmt.tokens[0].value.upper()
                if first == "ENDCLASS":
                    self.advance()
                    break
                self.advance()
                if first == "METHOD":
                    tokens = stmt.tokens
                    if len(tokens) > 3 and tokens[2].value == "~":
                        m_name = f"{tokens[1].value.upper()}~{tokens[3].value.upper()}"
                    elif len(tokens) > 1:
                        m_name = tokens[1].value.upper()
                    else:
                        m_name = "METHOD"

                    body: List[ASTNode] = []
                    while not self.is_at_end():
                        m_stmt = self.current_statement()
                        if not m_stmt or not m_stmt.tokens:
                            self.advance()
                            continue
                        if m_stmt.tokens[0].value.upper() == "ENDMETHOD":
                            self.advance()
                            break
                        node = self.parse_statement()
                        if node:
                            body.append(node)
                    methods_dict[m_name] = MethodImplNode(class_name, m_name, body, stmt.line)
            return ClassImplNode(class_name, methods_dict, start_stmt.line)

        return None

    def _parse_interface_block(self, start_stmt: Statement) -> Optional[InterfaceDefNode]:
        tokens = start_stmt.tokens
        if len(tokens) < 2:
            return None
        intf_name = tokens[1].value.upper()
        self.declared_names.add(intf_name)
        methods: List[Dict[str, Any]] = []
        attributes: List[Any] = []
        interfaces: List[str] = []

        while not self.is_at_end():
            stmt = self.current_statement()
            if not stmt or not stmt.tokens:
                self.advance()
                continue
            first = stmt.tokens[0].value.upper()
            if first == "ENDINTERFACE":
                self.advance()
                break
            self.advance()

            if first == "INTERFACES":
                for t in stmt.tokens[1:]:
                    val = t.value.upper()
                    if val not in (",", ":"):
                        interfaces.append(val)
                continue

            if first in ("DATA", "CLASS-DATA", "CONSTANTS"):
                is_static = (first in ("CLASS-DATA", "CONSTANTS"))
                node = self._parse_data_statement(stmt)
                if node:
                    setattr(node, "visibility", "PUBLIC")
                    setattr(node, "is_static", is_static)
                    attributes.append(node)
                    self.declared_names.add(node.var_name.upper())
                continue

            if first in ("METHODS", "CLASS-METHODS"):
                is_static = (first == "CLASS-METHODS")
                m_info = self._parse_method_signature(stmt, is_static, "PUBLIC")
                if m_info:
                    methods.append(m_info)
                    self.declared_names.add(m_info["name"].upper())
                continue

        return InterfaceDefNode(intf_name, methods, attributes, interfaces, start_stmt.line)

    def _parse_raise_exception(self, stmt: Statement) -> RaiseExceptionNode:
        tokens = stmt.tokens
        exc_class = "CX_ROOT"
        msg = ""
        i = 2
        if i < len(tokens) and tokens[i].value.upper() == "TYPE":
            if i + 1 < len(tokens):
                exc_class = tokens[i + 1].value.upper()
            i += 2
        while i < len(tokens):
            if tokens[i].value.upper() in ("MESSAGE", "TEXT") and i + 2 < len(tokens) and tokens[i + 1].value == "=":
                msg = tokens[i + 2].value
                break
            elif tokens[i].value.upper() == "EXPORTING":
                i += 1
                continue
            i += 1
        return RaiseExceptionNode(exc_class, msg, stmt.line)

    def _parse_create_object(self, stmt: Statement) -> CreateObjectNode:
        tokens = stmt.tokens[2:]
        if not tokens:
            return CreateObjectNode("", None, {}, stmt.line)
        target = tokens[0].value.upper()
        class_name = None
        exporting: Dict[str, List[Token]] = {}
        i = 1
        if i < len(tokens) and tokens[i].value.upper() == "TYPE":
            if i + 1 < len(tokens):
                class_name = tokens[i + 1].value.upper()
            i += 2
        if i < len(tokens) and tokens[i].value.upper() == "EXPORTING":
            i += 1
            exporting = self._parse_method_arguments(tokens[i:])
        return CreateObjectNode(target, class_name, exporting, stmt.line)

    def _parse_call_method(self, stmt: Statement) -> Optional[CallMethodNode]:
        tokens = stmt.tokens[2:]
        if not tokens:
            return None
        target_obj = ""
        method_name = ""
        is_static = False
        full_call = "".join(t.value for t in tokens[:3])

        if "->" in full_call:
            parts = full_call.split("->", 1)
            target_obj = parts[0].upper()
            method_name = parts[1].split("(")[0].upper()
            i = 3 if len(tokens) >= 3 and tokens[1].value == "->" else 1
        elif "=>" in full_call:
            parts = full_call.split("=>", 1)
            target_obj = parts[0].upper()
            method_name = parts[1].split("(")[0].upper()
            is_static = True
            i = 3 if len(tokens) >= 3 and tokens[1].value == "=>" else 1
        else:
            target_obj = tokens[0].value.upper()
            method_name = tokens[1].value.upper() if len(tokens) > 1 else ""
            i = 2

        exporting: Dict[str, List[Token]] = {}
        receiving = None
        while i < len(tokens):
            tk = tokens[i].value.upper()
            if tk == "EXPORTING":
                i += 1
                param_tokens: List[Token] = []
                while i < len(tokens) and tokens[i].value.upper() not in ("RECEIVING", "IMPORTING", "CHANGING"):
                    param_tokens.append(tokens[i])
                    i += 1
                exporting = self._parse_method_arguments(param_tokens)
                continue
            elif tk == "RECEIVING":
                i += 1
                while i < len(tokens):
                    if tokens[i].value not in ("=",):
                        if i + 2 < len(tokens) and tokens[i + 1].value == "=":
                            receiving = tokens[i + 2].value.upper()
                            i += 3
                        else:
                            receiving = tokens[i].value.upper()
                            i += 1
                        break
                    i += 1
            i += 1

        return CallMethodNode(target_obj, method_name, is_static, exporting, receiving, None, stmt.line)

    def _parse_method_arguments(self, param_tokens: List[Token]) -> Dict[str, List[Token]]:
        args: Dict[str, List[Token]] = {}
        if not param_tokens:
            return args

        if param_tokens and param_tokens[0].value.upper() == "EXPORTING":
            param_tokens = param_tokens[1:]

        # Check if there are named parameters: look for top-level '='
        has_named = False
        depth = 0
        for t in param_tokens:
            if t.value in ("(", "["):
                depth += 1
            elif t.value in (")", "]"):
                depth -= 1
            elif t.value == "=" and depth == 0:
                has_named = True
                break

        if not has_named:
            # Positional arguments split by top-level ','
            current_arg: List[Token] = []
            depth = 0
            arg_num = 1
            for t in param_tokens:
                if t.value in ("(", "["):
                    depth += 1
                    current_arg.append(t)
                elif t.value in (")", "]"):
                    depth -= 1
                    current_arg.append(t)
                elif t.value == "," and depth == 0:
                    if current_arg:
                        args[f"PARAM_{arg_num}"] = current_arg
                        arg_num += 1
                        current_arg = []
                else:
                    current_arg.append(t)
            if current_arg:
                args[f"PARAM_{arg_num}"] = current_arg
            return args

        # Named arguments: p_name = expr [,] p_name2 = expr2
        k = 0
        while k < len(param_tokens):
            if param_tokens[k].value in (",", "IMPORTING", "EXPORTING", "CHANGING", "RECEIVING"):
                k += 1
                continue
            p_name = param_tokens[k].value.upper()
            if k + 1 < len(param_tokens) and param_tokens[k + 1].value == "=":
                expr_tokens: List[Token] = []
                k += 2
                depth = 0
                while k < len(param_tokens):
                    t = param_tokens[k]
                    if t.value in ("(", "["):
                        depth += 1
                        expr_tokens.append(t)
                        k += 1
                    elif t.value in (")", "]"):
                        depth -= 1
                        expr_tokens.append(t)
                        k += 1
                    elif depth == 0 and t.value == ",":
                        k += 1
                        break
                    elif depth == 0 and k + 1 < len(param_tokens) and param_tokens[k + 1].value == "=":
                        break
                    elif depth == 0 and t.value.upper() in ("IMPORTING", "EXPORTING", "CHANGING", "RECEIVING"):
                        break
                    else:
                        expr_tokens.append(t)
                        k += 1
                args[p_name] = expr_tokens
            else:
                k += 1
        return args

    def _parse_inline_method_call(self, stmt: Statement, assign_to: Optional[str] = None) -> Optional[CallMethodNode]:
        tokens = stmt.tokens
        delim_idx = next((i for i, t in enumerate(tokens) if t.value in ("->", "=>")), None)
        if delim_idx is None or delim_idx == 0 or delim_idx + 1 >= len(tokens):
            return None

        target_obj = tokens[delim_idx - 1].value.upper()
        is_static = (tokens[delim_idx].value == "=>")

        # Check for interface qualification: obj->intf~method( )
        if delim_idx + 3 < len(tokens) and tokens[delim_idx + 2].value == "~":
            method_name = f"{tokens[delim_idx + 1].value.upper()}~{tokens[delim_idx + 3].value.upper()}"
        else:
            method_name = tokens[delim_idx + 1].value.upper()

        exporting: Dict[str, List[Token]] = {}
        if "(" in [t.value for t in tokens]:
            p_start = next(i for i, t in enumerate(tokens) if t.value == "(")
            p_end = len(tokens)
            b_depth = 0
            for idx in range(p_start, len(tokens)):
                if tokens[idx].value == "(":
                    b_depth += 1
                elif tokens[idx].value == ")":
                    b_depth -= 1
                    if b_depth == 0:
                        p_end = idx
                        break

            param_tokens = tokens[p_start + 1 : p_end]
            exporting = self._parse_method_arguments(param_tokens)

        return CallMethodNode(target_obj, method_name, is_static, exporting, None, assign_to, stmt.line)

