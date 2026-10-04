"""
SkilTrix SAP ABAP Lab - AST Runtime Interpreter
Executes parsed ABAP AST nodes in an isolated sandbox with state management,
system fields (SY-*), internal table handling, and Open SQL synthetic database queries.
"""

import copy
import datetime
import re
from typing import Dict, List, Any, Optional, Tuple
from .parser import (
    ASTNode,
    ReportNode,
    DataDeclNode,
    TypesDeclNode,
    ConstantsDeclNode,
    AssignNode,
    WriteNode,
    UlineNode,
    SkipNode,
    IfNode,
    CaseNode,
    DoNode,
    WhileNode,
    LoopNode,
    ReadTableNode,
    AppendNode,
    InsertNode,
    UpdateNode,
    ModifyNode,
    DeleteNode,
    CommitWorkNode,
    RollbackWorkNode,
    SortNode,
    ClearNode,
    SelectNode,
    FormNode,
    PerformNode,
    ExitNode,
    ContinueNode,
    ClassDefNode,
    ClassImplNode,
    MethodImplNode,
    InterfaceDefNode,
    RaiseExceptionNode,
    CreateObjectNode,
    CallMethodNode,
    TryNode,
)
from .lexer import Token, TokenType
from .datasets import (
    query_synthetic_table,
    get_standard_table,
    register_custom_synthetic_table,
    SYNTHETIC_CUSTOM_TABLES,
    STANDARD_DATASETS,
)


class ABAPException(Exception):
    """Represents a simulated ABAP OO exception instance (CX_ROOT descendant)."""
    def __init__(self, exc_class: str, message: str, line: int = 1):
        super().__init__(message)
        self.exc_class = exc_class.upper().strip()
        self.message = message
        self.line = line

    def __str__(self):
        return f"{self.exc_class}: {self.message}"


EXCEPTION_HIERARCHY = {
    "CX_SQL_EXCEPTION": ["CX_SQL_EXCEPTION", "CX_DYNAMIC_CHECK", "CX_ROOT"],
    "CX_SY_OPEN_SQL_ERROR": ["CX_SY_OPEN_SQL_ERROR", "CX_DYNAMIC_CHECK", "CX_ROOT"],
    "CX_SY_ZERODIVIDE": ["CX_SY_ZERODIVIDE", "CX_NO_CHECK", "CX_ROOT"],
    "CX_SY_REF_IS_INITIAL": ["CX_SY_REF_IS_INITIAL", "CX_NO_CHECK", "CX_ROOT"],
    "CX_STATIC_CHECK": ["CX_STATIC_CHECK", "CX_ROOT"],
    "CX_DYNAMIC_CHECK": ["CX_DYNAMIC_CHECK", "CX_ROOT"],
    "CX_NO_CHECK": ["CX_NO_CHECK", "CX_ROOT"],
    "CX_ROOT": ["CX_ROOT"],
}


class ABAPInterface:
    def __init__(self, name: str, def_node: Optional[InterfaceDefNode] = None):
        self.name = name.upper()
        self.def_node = def_node
        self.methods_def: Dict[str, Dict[str, Any]] = {}
        self.attributes_def: List[Any] = []
        self.interfaces: List[str] = list(def_node.interfaces) if (def_node and def_node.interfaces) else []
        if def_node:
            for m in def_node.methods:
                self.methods_def[m["name"].upper()] = m
            for a in def_node.attributes:
                self.attributes_def.append(a)


class ABAPClass:
    def __init__(self, name: str, def_node: Optional[ClassDefNode] = None):
        self.name = name.upper()
        self.def_node = def_node
        self.superclass: Optional[str] = def_node.superclass if def_node else None
        self.is_abstract: bool = def_node.is_abstract if def_node else False
        self.is_final: bool = def_node.is_final if def_node else False
        self.interfaces: List[str] = list(def_node.interfaces) if (def_node and def_node.interfaces) else []
        self.create_visibility: str = def_node.create_visibility if def_node else "PUBLIC"
        self.methods_def: Dict[str, Dict[str, Any]] = {}
        self.methods_impl: Dict[str, Any] = {}
        self.attributes_def: List[Any] = []
        self.class_data: Dict[str, Any] = {}
        self.class_constructor_ran: bool = False
        if def_node:
            for m in def_node.methods:
                self.methods_def[m["name"].upper()] = m
            for a in def_node.attributes:
                self.attributes_def.append(a)
                is_static = getattr(a, "is_static", False) or (a.get("is_static", False) if isinstance(a, dict) else False)
                attr_name = getattr(a, "var_name", None) or (a.get("name") if isinstance(a, dict) else "")
                if is_static and attr_name:
                    init_val = getattr(a, "initial_value", "")
                    self.class_data[attr_name.upper()] = init_val or ""

    def find_method_impl(self, method_name: str, classes: Dict[str, "ABAPClass"]) -> Optional[Tuple["ABAPClass", Any]]:
        m_upper = method_name.upper()
        if m_upper in self.methods_impl:
            return (self, self.methods_impl[m_upper])
        # Check interface qualified names
        for intf in self.interfaces:
            qual = f"{intf}~{m_upper}"
            if qual in self.methods_impl:
                return (self, self.methods_impl[qual])
        # Walk up superclass hierarchy
        if self.superclass and self.superclass in classes:
            return classes[self.superclass].find_method_impl(method_name, classes)
        return None

    def find_method_def(self, method_name: str, classes: Dict[str, "ABAPClass"], interfaces: Dict[str, "ABAPInterface"]) -> Optional[Tuple[str, Dict[str, Any]]]:
        m_upper = method_name.upper()
        if m_upper in self.methods_def:
            return (self.name, self.methods_def[m_upper])
        for intf_name in self.interfaces:
            qual = f"{intf_name}~{m_upper}"
            if qual in self.methods_def:
                return (self.name, self.methods_def[qual])
            if intf_name in interfaces:
                intf = interfaces[intf_name]
                if m_upper in intf.methods_def:
                    return (intf_name, intf.methods_def[m_upper])
        if self.superclass and self.superclass in classes:
            return classes[self.superclass].find_method_def(method_name, classes, interfaces)
        return None

    def find_attribute_def(self, attr_name: str, classes: Dict[str, "ABAPClass"]) -> Optional[Tuple["ABAPClass", Any]]:
        a_upper = attr_name.upper()
        for a in self.attributes_def:
            var_name = getattr(a, "var_name", None) or (a.get("name") if isinstance(a, dict) else "")
            if var_name.upper() == a_upper:
                return (self, a)
        if self.superclass and self.superclass in classes:
            return classes[self.superclass].find_attribute_def(attr_name, classes)
        return None


class ABAPInstance:
    def __init__(self, abap_class: ABAPClass, classes: Optional[Dict[str, ABAPClass]] = None):
        self.abap_class = abap_class
        self.attributes: Dict[str, Any] = {}
        classes = classes or {}
        # Collect inheritance chain from base class down to derived class
        chain = []
        curr = abap_class
        visited = set()
        while curr and curr.name not in visited:
            visited.add(curr.name)
            chain.append(curr)
            curr = classes.get(curr.superclass) if curr.superclass else None
        chain.reverse()

        for c in chain:
            for attr in c.attributes_def:
                is_static = getattr(attr, "is_static", False) or (attr.get("is_static", False) if isinstance(attr, dict) else False)
                attr_name = getattr(attr, "var_name", None) or (attr.get("name") if isinstance(attr, dict) else "")
                attr_name = attr_name.upper()
                if not attr_name:
                    continue
                init_val = getattr(attr, "initial_value", None)
                if init_val is None and isinstance(attr, dict):
                    init_val = attr.get("initial_value")
                var_type = getattr(attr, "var_type", "STRING") if hasattr(attr, "var_type") else "STRING"
                if init_val is None:
                    t = var_type.upper()
                    if t in ("I", "INT", "INT4", "INT2", "INT1", "INT8"):
                        init_val = 0
                    elif t in ("F", "DEC", "CURR", "P"):
                        init_val = 0.0
                    elif "TABLE" in t:
                        init_val = []
                    elif "REF_TO" in t or "REF TO" in t:
                        init_val = None
                    else:
                        init_val = ""

                if is_static:
                    if attr_name not in c.class_data:
                        c.class_data[attr_name] = copy.deepcopy(init_val)
                else:
                    self.attributes[attr_name] = copy.deepcopy(init_val)

    def __str__(self):
        return f"<Object of class {self.abap_class.name}>"


class ABAPRuntimeError(Exception):
    def __init__(self, message: str, line: int = 1):
        super().__init__(message)
        self.message = message
        self.line = line


class ExecutionSignal:
    NONE = 0
    EXIT = 1
    CONTINUE = 2


class ABAPInterpreter:
    def __init__(self, max_steps: int = 15000, user_id: Optional[str] = None, project_id: Optional[str] = None):
        self.max_steps = max_steps
        self.user_id = str(user_id) if user_id is not None else None
        self.project_id = project_id
        self.step_count = 0

        # Memory Spaces
        self.variables: Dict[str, Any] = {}
        self.field_symbols: Dict[str, Any] = {}
        self.constants: Dict[str, Any] = {}
        self.forms: Dict[str, FormNode] = {}

        # Classes & OOP State
        self.classes: Dict[str, ABAPClass] = {}
        self.interfaces: Dict[str, ABAPInterface] = {}
        self.current_instance: Optional[ABAPInstance] = None
        self.current_class: Optional[str] = None
        self._register_builtin_classes()

        # Output Spool
        self.output_lines: List[str] = []
        self.current_line: str = ""

        # Diagnostics & Results
        self.diagnostics: List[Dict[str, Any]] = []

        # System Fields (SY-*)
        now = datetime.datetime.now()
        self.system_fields: Dict[str, Any] = {
            "SY-SUBRC": 0,
            "SY-DATUM": now.strftime("%Y%m%d"),
            "SY-UZEIT": now.strftime("%H%M%S"),
            "SY-INDEX": 0,
            "SY-TABIX": 0,
            "SY-DBCNT": 0,
            "SY-MANDT": "100",
            "SY-UNAME": "DEVELOPER",
            "SY-TITLE": "ABAP_REPORT",
            "SY-PAGNO": 1,
            "SY-LINNO": 1,
        }
        self.last_db_failed = False

    def execute(self, ast_nodes: List[ASTNode]) -> Dict[str, Any]:
        """Executes a list of top-level AST nodes and returns execution telemetry."""
        # 1. First pass: Register subroutines (FORM), Interfaces, and Classes
        for node in ast_nodes:
            if isinstance(node, FormNode):
                self.forms[node.name] = node
            elif isinstance(node, InterfaceDefNode):
                if node.name not in self.interfaces:
                    self.interfaces[node.name] = ABAPInterface(node.name, node)
                else:
                    self.interfaces[node.name].def_node = node
                    self.interfaces[node.name].interfaces = list(node.interfaces)
                    for m in node.methods:
                        self.interfaces[node.name].methods_def[m["name"].upper()] = m
                    self.interfaces[node.name].attributes_def = node.attributes
            elif isinstance(node, ClassDefNode):
                if node.name not in self.classes:
                    self.classes[node.name] = ABAPClass(node.name, node)
                else:
                    self.classes[node.name].def_node = node
                    self.classes[node.name].superclass = node.superclass
                    self.classes[node.name].is_abstract = node.is_abstract
                    self.classes[node.name].is_final = node.is_final
                    self.classes[node.name].interfaces = list(node.interfaces)
                    self.classes[node.name].create_visibility = node.create_visibility
                    self.classes[node.name].attributes_def = node.attributes
                    for a in node.attributes:
                        is_static = getattr(a, "is_static", False) or (a.get("is_static", False) if isinstance(a, dict) else False)
                        attr_name = getattr(a, "var_name", None) or (a.get("name") if isinstance(a, dict) else "")
                        if is_static and attr_name and attr_name.upper() not in self.classes[node.name].class_data:
                            init_val = getattr(a, "initial_value", "")
                            self.classes[node.name].class_data[attr_name.upper()] = init_val or ""
            elif isinstance(node, ClassImplNode):
                if node.name not in self.classes:
                    self.classes[node.name] = ABAPClass(node.name)
                for m_name, m_impl in node.methods.items():
                    self.classes[node.name].methods_impl[m_name.upper()] = m_impl

        # Run semantic validation pass
        self._run_semantic_analysis(ast_nodes)

        # 2. Second pass: Execute program statements
        try:
            for node in ast_nodes:
                self.step_count += 1
                if self.step_count > self.max_steps:
                    raise ABAPRuntimeError(
                        f"Execution aborted: Exceeded maximum allowed instruction steps ({self.max_steps}). Possible infinite loop.",
                        getattr(node, "line", 1),
                    )

                signal = self._execute_node(node)
                if signal == ExecutionSignal.EXIT:
                    break

            # Flush any remaining buffer in current_line
            if self.current_line:
                self.output_lines.append(self.current_line)
                self.current_line = ""

            status = True
            output = "\n".join(self.output_lines)

        except ABAPException as exc:
            status = False
            self.diagnostics.append({"line": exc.line, "severity": "error", "message": exc.message})
            if self.current_line:
                self.output_lines.append(self.current_line)
            output = "\n".join(self.output_lines)
            output += f"\n[ABAP RUNTIME ERROR - Line {exc.line}]: {exc.message}"

        except ABAPRuntimeError as err:
            status = False
            self.diagnostics.append({"line": err.line, "severity": "error", "message": err.message})
            if self.current_line:
                self.output_lines.append(self.current_line)
            output = "\n".join(self.output_lines)
            output += f"\n[ABAP RUNTIME ERROR - Line {err.line}]: {err.message}"

        return {
            "status": status,
            "output": output,
            "diagnostics": self.diagnostics,
            "variables": {k: v for k, v in self.variables.items() if not isinstance(v, list)},
            "internal_tables": {k: v for k, v in self.variables.items() if isinstance(v, list)},
            "system_fields": self.system_fields,
        }

    def _execute_node(self, node: ASTNode) -> int:
        if isinstance(node, ReportNode):
            self.system_fields["SY-TITLE"] = node.name
            return ExecutionSignal.NONE

        elif isinstance(node, TypesDeclNode):
            fields_list = [f["name"].upper() for f in getattr(node, "fields", []) if isinstance(f, dict) and f.get("name")]
            self.variables[f"__TYPE_DEF_{node.type_name.upper()}"] = fields_list
            return ExecutionSignal.NONE

        elif isinstance(node, DataDeclNode):
            self.variables[f"__TYPE_{node.var_name}"] = node.var_type
            self.variables[f"__TABLE_KIND_{node.var_name}"] = getattr(node, "table_type", "standard")
            self.variables[f"__KEY_DEF_{node.var_name}"] = getattr(node, "key_def", {})
            self.variables[f"__LINE_TYPE_{node.var_name}"] = getattr(node, "line_type", node.var_type)

            if getattr(node, "like_var", None):
                self.variables[f"__LIKE_VAR_{node.var_name}"] = node.like_var

            if getattr(node, "structure_fields", None):
                fields_list = [f["name"].upper() for f in node.structure_fields if isinstance(f, dict) and f.get("name")]
                self.variables[f"__TYPE_DEF_{node.var_name}"] = fields_list
                self.variables[node.var_name] = {f_name: "" for f_name in fields_list}
                return ExecutionSignal.NONE

            if node.is_table:
                self.variables[node.var_name] = []
            elif "REF_TO" in node.var_type.upper() or "REF TO" in node.var_type.upper():
                self.variables[node.var_name] = None
            elif getattr(node, "like_var", None) and node.like_var in self.variables:
                self.variables[node.var_name] = copy.deepcopy(self.variables[node.like_var])
            else:
                type_upper = node.var_type.upper()
                if f"__TYPE_DEF_{type_upper}" in self.variables:
                    type_fields = self.variables[f"__TYPE_DEF_{type_upper}"]
                    init_val = {f_name: "" for f_name in type_fields}
                else:
                    t_type, d_tab, std_tbl = self._resolve_database_table(node.var_type)
                    if t_type == "custom" and d_tab and d_tab.fields_schema:
                        init_val = {f["field"].upper(): self._default_value_for_type(f.get("type", "CHAR")) for f in d_tab.fields_schema if f.get("field")}
                    elif std_tbl and std_tbl.get("columns"):
                        init_val = {col["name"].upper(): self._default_value_for_type(col.get("type", "STRING")) for col in std_tbl["columns"]}
                        if "MANDT" in [c.get("name", "").upper() for c in std_tbl["columns"]]:
                            init_val["MANDT"] = self.system_fields.get("SY-MANDT", "100")
                    else:
                        init_val = self._default_value_for_type(node.var_type)
                        if node.initial_value is not None:
                            init_val = self._cast_value(node.initial_value, node.var_type)
                self.variables[node.var_name] = init_val
            return ExecutionSignal.NONE

        elif isinstance(node, ConstantsDeclNode):
            val = self._cast_value(node.value, node.const_type)
            self.constants[node.const_name] = val
            self.variables[node.const_name] = val
            return ExecutionSignal.NONE

        elif isinstance(node, AssignNode):
            val = self._evaluate_expression(node.expr_tokens)
            self._set_variable_value(node.target, val, node.line)
            return ExecutionSignal.NONE

        elif isinstance(node, WriteNode):
            for item in node.items:
                if item.is_slash:
                    if self.current_line:
                        self.output_lines.append(self.current_line)
                    self.current_line = ""

                val_str = self._resolve_token_string(item.value_token)
                if val_str:
                    if self.current_line and not self.current_line.endswith(" "):
                        self.current_line += " "
                    self.current_line += val_str
            return ExecutionSignal.NONE

        elif isinstance(node, UlineNode):
            if self.current_line:
                self.output_lines.append(self.current_line)
                self.current_line = ""
            self.output_lines.append("--------------------------------------------------------------------------------")
            return ExecutionSignal.NONE

        elif isinstance(node, SkipNode):
            if self.current_line:
                self.output_lines.append(self.current_line)
                self.current_line = ""
            for _ in range(max(1, node.count)):
                self.output_lines.append("")
            return ExecutionSignal.NONE

        elif isinstance(node, ClearNode):
            target = node.target_name.upper().strip()
            if "=>" in target:
                cls_name, attr_name = target.split("=>", 1)
                cls_name, attr_name = cls_name.strip(), attr_name.strip()
                if cls_name in self.classes and attr_name in self.classes[cls_name].class_data:
                    self.classes[cls_name].class_data[attr_name] = self._default_value_for_type("STRING")
            elif "->" in target:
                obj_name, attr_name = target.split("->", 1)
                obj_name, attr_name = obj_name.strip(), attr_name.strip()
                if obj_name == "ME" and self.current_instance:
                    self.current_instance.attributes[attr_name] = self._default_value_for_type("STRING")
                else:
                    obj = self._get_variable_value(obj_name)
                    if isinstance(obj, ABAPInstance):
                        obj.attributes[attr_name] = self._default_value_for_type("STRING")
            elif target in self.variables:
                if isinstance(self.variables[target], list):
                    self.variables[target] = []
                elif isinstance(self.variables[target], dict):
                    self.variables[target] = {k: self._default_value_for_type("STRING") for k in self.variables[target]}
                elif isinstance(self.variables[target], ABAPInstance):
                    self.variables[target] = None
                else:
                    self.variables[target] = self._default_value_for_type("STRING")
            elif self.current_instance and target in self.current_instance.attributes:
                self.current_instance.attributes[target] = self._default_value_for_type("STRING")
            return ExecutionSignal.NONE

        elif isinstance(node, IfNode):
            cond_result = self._evaluate_condition(node.cond_tokens)
            if cond_result:
                return self._execute_block(node.then_body)
            else:
                for branch in node.elseif_branches:
                    if self._evaluate_condition(branch["cond"]):
                        return self._execute_block(branch["body"])
                if node.else_body:
                    return self._execute_block(node.else_body)
            return ExecutionSignal.NONE

        elif isinstance(node, CaseNode):
            case_val = self._evaluate_expression(node.expr_tokens)
            matched = False
            for branch in node.when_branches:
                when_val = self._evaluate_expression(branch["val"])
                if str(case_val).upper() == str(when_val).upper():
                    matched = True
                    sig = self._execute_block(branch["body"])
                    return sig
            if not matched and node.others_body:
                return self._execute_block(node.others_body)
            return ExecutionSignal.NONE

        elif isinstance(node, DoNode):
            max_times = None
            if node.times_expr:
                max_times = int(self._evaluate_expression(node.times_expr))

            iteration = 0
            while True:
                iteration += 1
                if max_times is not None and iteration > max_times:
                    break

                self.system_fields["SY-INDEX"] = iteration
                sig = self._execute_block(node.body)
                if sig == ExecutionSignal.EXIT:
                    break

            return ExecutionSignal.NONE

        elif isinstance(node, WhileNode):
            iteration = 0
            while self._evaluate_condition(node.cond_tokens):
                iteration += 1
                self.system_fields["SY-INDEX"] = iteration
                sig = self._execute_block(node.body)
                if sig == ExecutionSignal.EXIT:
                    break

            return ExecutionSignal.NONE

        elif isinstance(node, LoopNode):
            table = self._get_variable_value(node.table_name)
            if not isinstance(table, list):
                raise ABAPRuntimeError(f"Target '{node.table_name}' in LOOP AT is not an internal table.", node.line)

            # Iterate over snapshot of internal table
            rows = list(table)
            for idx, row in enumerate(rows, start=1):
                self.system_fields["SY-TABIX"] = idx
                self.system_fields["SY-SUBRC"] = 0

                # Copy row to work area
                if node.target_var:
                    self.variables[node.target_var] = copy.deepcopy(row)
                like_var = self.variables.get(f"__LIKE_VAR_{node.table_name}")
                if like_var and like_var != node.target_var and like_var in self.variables:
                    if isinstance(self.variables[like_var], dict) and isinstance(row, dict):
                        self.variables[like_var].update(copy.deepcopy(row))
                    else:
                        self.variables[like_var] = copy.deepcopy(row)
                if node.assigning_fs:
                    self.field_symbols[node.assigning_fs] = row

                # Check WHERE condition if present
                if node.where_tokens:
                    if not self._evaluate_condition(node.where_tokens):
                        continue

                sig = self._execute_block(node.body)
                if sig == ExecutionSignal.EXIT:
                    break

            return ExecutionSignal.NONE

        elif isinstance(node, ReadTableNode):
            table = self._get_variable_value(node.table_name)
            if not isinstance(table, list):
                raise ABAPRuntimeError(f"'{node.table_name}' is not an internal table.", node.line)

            matched_row = None
            found_idx = 0

            # 1. Lookup by index
            if node.index_expr:
                idx = int(self._evaluate_expression(node.index_expr))
                if 1 <= idx <= len(table):
                    matched_row = table[idx - 1]
                    found_idx = idx

            # 2. Lookup with key
            elif node.key_field and node.key_val_tokens:
                expected_val = str(self._evaluate_expression(node.key_val_tokens)).upper()
                for idx, r in enumerate(table, start=1):
                    if isinstance(r, dict):
                        row_val = str(r.get(node.key_field, "")).upper()
                        if row_val == expected_val:
                            matched_row = r
                            found_idx = idx
                            break

            if matched_row is not None:
                self.system_fields["SY-SUBRC"] = 0
                self.system_fields["SY-TABIX"] = found_idx
                if node.target_var:
                    self.variables[node.target_var] = copy.deepcopy(matched_row)
                if node.assigning_fs:
                    self.field_symbols[node.assigning_fs] = matched_row
            else:
                self.system_fields["SY-SUBRC"] = 4
                self.system_fields["SY-TABIX"] = 0

            return ExecutionSignal.NONE

        elif isinstance(node, AppendNode):
            table = None
            if "->" in node.target_table:
                obj_name, attr_name = node.target_table.split("->", 1)
                obj_name, attr_name = obj_name.strip(), attr_name.strip()
                inst = self.current_instance if obj_name == "ME" else self._get_variable_value(obj_name)
                if isinstance(inst, ABAPInstance):
                    if attr_name not in inst.attributes or not isinstance(inst.attributes[attr_name], list):
                        inst.attributes[attr_name] = []
                    table = inst.attributes[attr_name]
            elif self.current_instance and node.target_table in self.current_instance.attributes:
                if not isinstance(self.current_instance.attributes[node.target_table], list):
                    self.current_instance.attributes[node.target_table] = []
                table = self.current_instance.attributes[node.target_table]
            else:
                if node.target_table not in self.variables:
                    self.variables[node.target_table] = []
                table = self.variables[node.target_table]

            if not isinstance(table, list):
                raise ABAPRuntimeError(f"Target '{node.target_table}' for APPEND is not an internal table.", node.line)

            table_kind = self.variables.get(f"__TABLE_KIND_{node.target_table}", "standard")
            if table_kind == "hashed":
                raise ABAPRuntimeError(
                    f"In 'APPEND {node.target_table}', the target must be an index table. Operation APPEND is not permitted for hashed tables.",
                    node.line,
                )

            if node.initial_line:
                new_row = {}
                table.append(new_row)
                if node.assigning_fs:
                    self.field_symbols[node.assigning_fs] = new_row
            else:
                if getattr(node, "source_tokens", None):
                    src_val = self._evaluate_expression(node.source_tokens)
                else:
                    src_val = self._get_variable_value(node.source_var)

                if table_kind == "sorted":
                    key_def = self.variables.get(f"__KEY_DEF_{node.target_table}") or {}
                    key_fields = key_def.get("fields", [])
                    if key_def.get("kind") == "UNIQUE" and key_fields and isinstance(src_val, dict):
                        has_dup = any(
                            all(str(row.get(kf, "")) == str(src_val.get(kf, "")) for kf in key_fields)
                            for row in table if isinstance(row, dict)
                        )
                        if has_dup:
                            raise ABAPRuntimeError(f"Duplicate key in SORTED TABLE '{node.target_table}'.", node.line)
                    table.append(copy.deepcopy(src_val))
                    if key_fields:
                        table.sort(key=lambda r: tuple(str(r.get(kf, "")) for kf in key_fields) if isinstance(r, dict) else str(r))
                else:
                    table.append(copy.deepcopy(src_val))

            self.system_fields["SY-TABIX"] = len(table)
            return ExecutionSignal.NONE

        elif isinstance(node, InsertNode):
            return self._execute_insert(node)

        elif isinstance(node, UpdateNode):
            return self._execute_update(node)

        elif isinstance(node, ModifyNode):
            return self._execute_modify(node)

        elif isinstance(node, DeleteNode):
            return self._execute_delete(node)

        elif isinstance(node, CommitWorkNode):
            return self._execute_commit_work(node)

        elif isinstance(node, RollbackWorkNode):
            return self._execute_rollback_work(node)

        elif isinstance(node, SortNode):
            table = self._get_variable_value(node.table_name)
            if not isinstance(table, list):
                raise ABAPRuntimeError(f"'{node.table_name}' is not an internal table.", node.line)

            if node.field_names:
                field = node.field_names[0]
                table.sort(
                    key=lambda r: r.get(field, "") if isinstance(r, dict) else str(r),
                    reverse=node.descending,
                )
            else:
                table.sort(reverse=node.descending)

            return ExecutionSignal.NONE

        elif isinstance(node, SelectNode):
            return self._execute_select(node)

            return ExecutionSignal.NONE

        elif isinstance(node, PerformNode):
            form = self.forms.get(node.name)
            if form:
                self._execute_block(form.body)
            else:
                self.diagnostics.append(
                    {"line": node.line, "severity": "warning", "message": f"Subroutine FORM {node.name} not found."}
                )
            return ExecutionSignal.NONE

        elif isinstance(node, (ClassDefNode, ClassImplNode, MethodImplNode, InterfaceDefNode)):
            return ExecutionSignal.NONE

        elif isinstance(node, RaiseExceptionNode):
            raise ABAPException(node.exc_class, node.message, node.line)

        elif isinstance(node, CreateObjectNode):
            return self._execute_create_object(node)

        elif isinstance(node, CallMethodNode):
            return self._execute_call_method(node)

        elif isinstance(node, TryNode):
            return self._execute_try_block(node)

        elif isinstance(node, ExitNode):
            return ExecutionSignal.EXIT

        elif isinstance(node, ContinueNode):
            return ExecutionSignal.CONTINUE

        return ExecutionSignal.NONE

    def _get_dictionary_table_model(self, table_name: str):
        try:
            from ..abap_models import ABAPDictionaryTable
            clean = table_name.strip().upper().lstrip("@")
            query = ABAPDictionaryTable.objects.filter(table_name__iexact=clean)
            if self.user_id:
                user_q = query.filter(user_id=self.user_id)
                if self.project_id:
                    proj_tbl = user_q.filter(project__project_id=self.project_id).first()
                    if proj_tbl:
                        return proj_tbl
                user_tbl = user_q.first()
                if user_tbl:
                    return user_tbl
                shared_tbl = query.filter(user__isnull=True).first()
                if shared_tbl:
                    return shared_tbl
                return None
            return query.first()
        except Exception:
            return None

    def _resolve_database_table(self, table_name: str) -> Tuple[Optional[str], Optional[Any], Optional[Dict[str, Any]]]:
        """
        Resolves a database table against the active ABAP Dictionary and Standard SAP Datasets.
        Returns:
            (table_type, dict_table_model, standard_dataset_dict)
            - ("standard", None, std_dataset) for standard SAP tables (KNA1, VBAK, etc.)
            - ("custom", dict_table_model, None) for custom SE11 transparent tables
            - ("synthetic", None, syn_dataset) for in-process tables created via native DDL (when user_id is None)
            - (None, None, None) if table does NOT exist in active dictionary or catalog.
        """
        clean = table_name.strip().upper().lstrip("@")
        if clean in STANDARD_DATASETS:
            return "standard", None, STANDARD_DATASETS[clean]

        dict_model = self._get_dictionary_table_model(clean)
        if dict_model:
            return "custom", dict_model, None

        if self.user_id is None and clean in SYNTHETIC_CUSTOM_TABLES:
            return "synthetic", None, SYNTHETIC_CUSTOM_TABLES[clean]

        return None, None, None

    def _get_table_key_fields(self, dict_table: Optional[Any], table_name: str) -> List[str]:
        if dict_table and dict_table.fields_schema:
            keys = [f.get("field", "").upper() for f in dict_table.fields_schema if f.get("key")]
            if keys:
                return keys
        std = get_standard_table(table_name, user_id=self.user_id, project_id=self.project_id)
        if std and std.get("key_fields"):
            keys = [k.upper() for k in std["key_fields"]]
            if keys:
                return keys
        if dict_table and dict_table.fields_schema:
            fields = [f.get("field", "").upper() for f in dict_table.fields_schema if f.get("field")]
            if fields:
                return [fields[0]]
        return []

    def _match_keys(self, row1: Dict[str, Any], row2: Dict[str, Any], key_fields: List[str]) -> bool:
        if not key_fields:
            common = set(k.upper() for k in row1.keys()) & set(k.upper() for k in row2.keys())
            if not common:
                return False
            return all(str(row1.get(k, "")) == str(row2.get(k, "")) for k in common)
        return all(str(row1.get(k, "")) == str(row2.get(k, "")) for k in key_fields)

    def _build_where_filter(self, where_tokens: Optional[List[Token]]):
        if not where_tokens:
            return lambda r: True
        return lambda r: self._eval_sql_condition(where_tokens, r)

    def _resolve_field_value_from_row(self, fld: str, row: Dict[str, Any]) -> Any:
        fld_clean = fld.strip().upper()
        if not fld_clean or not row:
            return ""

        # 1. Exact match
        if fld_clean in row:
            return row[fld_clean]

        alias = None
        col = fld_clean
        if "~" in fld_clean:
            alias, col = fld_clean.split("~", 1)

        norm_col = col.replace("_", "").replace("-", "")
        alias_prefix = f"{alias}~" if alias else None

        # 2. Alias-scoped matching when alias is provided
        if alias_prefix:
            # 2a. Exact column under matching alias
            for k, v in row.items():
                if k.startswith(alias_prefix) and k[len(alias_prefix):] == col:
                    return v
            # 2b. Normalized column under matching alias
            for k, v in row.items():
                if k.startswith(alias_prefix) and k[len(alias_prefix):].replace("_", "").replace("-", "") == norm_col:
                    return v

        # 3. Direct unqualified match
        if col in row:
            return row[col]

        # 4. Check all keys ending with ~col or unqualified col match
        for k, v in row.items():
            if alias_prefix and "~" in k and not k.startswith(alias_prefix):
                continue
            k_col = k.split("~")[-1]
            if k_col == col:
                return v

        # 5. Normalized column matching (EMP_ID <-> EMPID)
        for k, v in row.items():
            if alias_prefix and "~" in k and not k.startswith(alias_prefix):
                continue
            k_norm = k.split("~")[-1].replace("_", "").replace("-", "")
            if k_norm == norm_col:
                return v

        # 6. Semantic and abbreviation matching
        def _match_fuzzy_col(c1: str, c2: str) -> bool:
            if c1 == c2:
                return True
            # Substring / abbreviation match for ABAP fields (EMPDESIG in EMPDESIGNATION)
            if len(c1) >= 4 and len(c2) >= 4:
                if c1 in c2 or c2 in c1:
                    return True
            # Strip common table prefixes: EMP, Z, Y
            c1_stem = re.sub(r"^(EMP|Z|Y)", "", c1)
            c2_stem = re.sub(r"^(EMP|Z|Y)", "", c2)
            if c1_stem and c2_stem:
                if c1_stem == c2_stem:
                    return True
                if len(c1_stem) >= 4 and len(c2_stem) >= 4:
                    if c1_stem in c2_stem or c2_stem in c1_stem:
                        return True
            # Transposition / typo check (e.g. DEISGN vs DESIGN, EMPSALARY vs EMOSALARY)
            if abs(len(c1) - len(c2)) <= 2:
                diffs = sum(1 for a, b in zip(sorted(c1), sorted(c2)) if a != b) + abs(len(c1) - len(c2))
                if diffs <= 2:
                    return True
            return False

        for k, v in row.items():
            if alias_prefix and "~" in k and not k.startswith(alias_prefix):
                continue
            k_norm = k.split("~")[-1].replace("_", "").replace("-", "")
            if _match_fuzzy_col(norm_col, k_norm):
                return v

        return ""

    def _eval_sql_condition(self, tokens: List[Token], row: Dict[str, Any]) -> bool:
        if not tokens:
            return True

        # Split by OR
        or_groups: List[List[Token]] = []
        current: List[Token] = []
        for t in tokens:
            if t.value.upper() == "OR":
                if current:
                    or_groups.append(current)
                current = []
            else:
                current.append(t)
        if current:
            or_groups.append(current)

        for or_grp in or_groups:
            # Split by AND
            and_groups: List[List[Token]] = []
            cur_and: List[Token] = []
            for t in or_grp:
                if t.value.upper() == "AND":
                    if cur_and:
                        and_groups.append(cur_and)
                    cur_and = []
                else:
                    cur_and.append(t)
            if cur_and:
                and_groups.append(cur_and)

            all_matched = True
            for pred in and_groups:
                if not self._eval_single_sql_predicate(pred, row):
                    all_matched = False
                    break
            if all_matched:
                return True

        return False

    def _eval_single_sql_predicate(self, tokens: List[Token], row: Dict[str, Any]) -> bool:
        if not tokens:
            return True

        # Strip outer parentheses
        while len(tokens) >= 2 and tokens[0].value == "(" and tokens[-1].value == ")":
            tokens = tokens[1:-1]

        tok_vals = [t.value.upper() for t in tokens]
        operators = ["<=", ">=", "<>", "!=", "=", "<", ">", "EQ", "NE", "LE", "GE", "LT", "GT", "LIKE"]
        found_op = None
        op_idx = -1
        for op in operators:
            if op in tok_vals:
                found_op = op
                op_idx = tok_vals.index(op)
                break

        if not found_op or op_idx == -1:
            return True

        left_tokens = tokens[:op_idx]
        right_tokens = tokens[op_idx + 1:]

        left_val = self._eval_sql_operand(left_tokens, row)
        right_val = self._eval_sql_operand(right_tokens, row)

        if found_op == "LIKE":
            pattern = re.escape(str(right_val)).replace("%", ".*").replace("_", ".")
            return re.fullmatch(pattern, str(left_val), flags=re.IGNORECASE) is not None

        try:
            l_num = float(left_val)
            r_num = float(right_val)
            if found_op in ("=", "EQ"):
                return l_num == r_num
            elif found_op in ("<>", "!=", "NE"):
                return l_num != r_num
            elif found_op in ("<", "LT"):
                return l_num < r_num
            elif found_op in (">", "GT"):
                return l_num > r_num
            elif found_op in ("<=", "LE"):
                return l_num <= r_num
            elif found_op in (">=", "GE"):
                return l_num >= r_num
        except (ValueError, TypeError):
            pass

        l_str = str(left_val).upper().strip()
        r_str = str(right_val).upper().strip()
        if found_op in ("=", "EQ"):
            return l_str == r_str
        elif found_op in ("<>", "!=", "NE"):
            return l_str != r_str
        elif found_op in ("<", "LT"):
            return l_str < r_str
        elif found_op in (">", "GT"):
            return l_str > r_str
        elif found_op in ("<=", "LE"):
            return l_str <= r_str
        elif found_op in (">=", "GE"):
            return l_str >= r_str

        return True

    def _eval_sql_operand(self, tokens: List[Token], row: Dict[str, Any]) -> Any:
        if not tokens:
            return ""
        if len(tokens) == 1:
            t = tokens[0]
            if t.type == TokenType.STRING:
                return t.value
            if t.type == TokenType.NUMBER:
                try:
                    return float(t.value) if "." in t.value else int(t.value)
                except ValueError:
                    return t.value
            if t.value.startswith("@"):
                return self._get_variable_value(t.value[1:])
            val = self._resolve_field_value_from_row(t.value, row)
            if val != "":
                return val
            if t.value.upper() in self.variables:
                return self.variables[t.value.upper()]
            return t.value

        if len(tokens) == 3 and tokens[1].value == "~":
            qual = f"{tokens[0].value.upper()}~{tokens[2].value.upper()}"
            val = self._resolve_field_value_from_row(qual, row)
            return val

        return self._evaluate_expression(tokens)

    def _execute_select(self, node: SelectNode) -> int:
        primary_table = node.from_table.strip().upper().lstrip("@")
        primary_alias = (node.from_alias or primary_table).strip().upper()
        p_type, p_dict, p_std = self._resolve_database_table(primary_table)
        if not p_type:
            if node.into_table:
                self.variables[node.into_table.lstrip("@").upper()] = []
            self.system_fields["SY-DBCNT"] = 0
            self.system_fields["SY-SUBRC"] = 4
            self.last_db_failed = True
            self.diagnostics.append({
                "line": node.line,
                "severity": "error",
                "code": "CX_SY_OPEN_SQL_DB",
                "message": f"Database table or view '{primary_table}' not found",
            })
            return ExecutionSignal.NONE

        join_tables_data = []
        for j in getattr(node, "joins", []):
            j_tbl = j["table"].strip().upper().lstrip("@")
            j_alias = (j.get("alias") or j_tbl).strip().upper()
            j_type, j_dict, j_std = self._resolve_database_table(j_tbl)
            if not j_type:
                if node.into_table:
                    self.variables[node.into_table.lstrip("@").upper()] = []
                self.system_fields["SY-DBCNT"] = 0
                self.system_fields["SY-SUBRC"] = 4
                self.last_db_failed = True
                self.diagnostics.append({
                    "line": node.line,
                    "severity": "error",
                    "code": "CX_SY_OPEN_SQL_DB",
                    "message": f"Database table or view '{j_tbl}' not found",
                })
                return ExecutionSignal.NONE
            j_rows = list(j_dict.sample_records or []) if j_type == "custom" else list(j_std.get("rows", []))
            join_tables_data.append({
                "type": j.get("type", "INNER").upper(),
                "table": j_tbl,
                "alias": j_alias,
                "on_tokens": j.get("on_tokens", []),
                "rows": j_rows,
            })

        p_rows = list(p_dict.sample_records or []) if p_type == "custom" else list(p_std.get("rows", []))
        combined_rows: List[Dict[str, Any]] = []
        for r in p_rows:
            row_dict = {}
            for k, v in r.items():
                k_up = str(k).upper()
                row_dict[f"{primary_alias}~{k_up}"] = v
                row_dict[f"{primary_table}~{k_up}"] = v
                row_dict[k_up] = v
            combined_rows.append(row_dict)

        for j_info in join_tables_data:
            j_alias = j_info["alias"]
            j_tbl = j_info["table"]
            j_type = j_info["type"]
            on_tokens = j_info["on_tokens"]
            j_rows = j_info["rows"]

            j_prepared: List[Dict[str, Any]] = []
            for r in j_rows:
                r_dict = {}
                for k, v in r.items():
                    k_up = str(k).upper()
                    r_dict[f"{j_alias}~{k_up}"] = v
                    r_dict[f"{j_tbl}~{k_up}"] = v
                    r_dict[k_up] = v
                j_prepared.append(r_dict)

            next_combined: List[Dict[str, Any]] = []
            for left_r in combined_rows:
                matched = False
                for right_r in j_prepared:
                    candidate = {**left_r, **right_r}
                    if not on_tokens or self._eval_sql_condition(on_tokens, candidate):
                        next_combined.append(candidate)
                        matched = True
                if not matched and "LEFT" in j_type:
                    null_pad = {}
                    if j_prepared:
                        for k in j_prepared[0].keys():
                            null_pad[k] = ""
                    next_combined.append({**left_r, **null_pad})
            combined_rows = next_combined

        if node.where_tokens:
            combined_rows = [r for r in combined_rows if self._eval_sql_condition(node.where_tokens, r)]

        if node.order_by:
            order_field = node.order_by.strip().upper()
            def sort_key(r):
                val = self._resolve_field_value_from_row(order_field, r)
                if isinstance(val, (int, float)):
                    return (0, float(val))
                try:
                    return (0, float(val))
                except (ValueError, TypeError):
                    return (1, str(val).upper())
            combined_rows.sort(key=sort_key, reverse=node.descending)

        if node.up_to_rows and node.up_to_rows > 0:
            combined_rows = combined_rows[:node.up_to_rows]

        target_components: List[str] = []
        if node.into_table:
            tbl_var = node.into_table.lstrip("@").upper()
            line_type = self.variables.get(f"__LINE_TYPE_{tbl_var}", "")
            target_components = self.variables.get(f"__TYPE_DEF_{line_type.upper()}") or []
            if not target_components:
                like_var = self.variables.get(f"__LIKE_VAR_{tbl_var}")
                if like_var:
                    target_components = self.variables.get(f"__TYPE_DEF_{like_var.upper()}") or []
                    if not target_components and isinstance(self.variables.get(like_var), dict):
                        target_components = list(self.variables[like_var].keys())
            if not target_components:
                target_components = self.variables.get(f"__TYPE_DEF_{tbl_var}") or []
            if not target_components:
                t_type, d_tab, std_tab = self._resolve_database_table(line_type)
                if t_type == "custom" and d_tab and d_tab.fields_schema:
                    target_components = [f["field"].upper() for f in d_tab.fields_schema if f.get("field")]
                elif std_tab and std_tab.get("columns"):
                    target_components = [c["name"].upper() for c in std_tab["columns"]]
        elif node.into_wa:
            wa_var = node.into_wa.lstrip("@").upper()
            wa_type = self.variables.get(f"__TYPE_{wa_var}", "")
            target_components = self.variables.get(f"__TYPE_DEF_{wa_type.upper()}") or []
            if not target_components:
                target_components = self.variables.get(f"__TYPE_DEF_{wa_var}") or []
            if not target_components and isinstance(self.variables.get(wa_var), dict):
                target_components = list(self.variables[wa_var].keys())

        if target_components:
            if "MANDT" in target_components and not any(f.split("~")[-1].upper() == "MANDT" for f in node.fields):
                target_components = [c for c in target_components if c != "MANDT"]

        if len(target_components) < len(node.fields):
            for k, v in self.variables.items():
                if k.startswith("__TYPE_DEF_") and isinstance(v, list) and len(v) == len(node.fields):
                    target_components = v
                    break

        projected_results: List[Dict[str, Any]] = []
        is_select_all = (not node.fields or node.fields == ["*"])

        for row in combined_rows:
            if is_select_all:
                projected_results.append(copy.deepcopy(row))
            else:
                proj: Dict[str, Any] = {}
                # 1. Positional mapping into target internal table / structure components
                for idx, fld in enumerate(node.fields):
                    val = self._resolve_field_value_from_row(fld, row)
                    if idx < len(target_components):
                        proj[target_components[idx]] = val

                # 2. Explicit column names and semantic aliases (take precedence)
                for idx, fld in enumerate(node.fields):
                    val = self._resolve_field_value_from_row(fld, row)
                    clean_name = fld.split("~")[-1].upper()
                    proj[clean_name] = val
                    proj[fld.upper()] = val
                    norm_name = clean_name.replace("_", "").replace("-", "")
                    proj[norm_name] = val

                    # Semantic alias projections
                    if norm_name in ("EMPID", "ID") or "EMPID" in norm_name:
                        proj["EMPID"] = val
                        proj["EMP_ID"] = val
                    if norm_name in ("EMPNAME", "NAME") or "EMPNAME" in norm_name:
                        proj["EMPNAME"] = val
                        proj["EMP_NAME"] = val
                    if norm_name in ("EMPDEPT", "DEPT", "DEPARTMENT"):
                        proj["EMPDEPT"] = val
                        proj["DEPT"] = val
                    if norm_name in ("EMPSALARY", "EMOSALARY", "SALARY"):
                        proj["EMPSALARY"] = val
                        proj["EMOSALARY"] = val
                        proj["SALARY"] = val
                    if norm_name in ("EMPCITY", "CITY"):
                        proj["EMPCITY"] = val
                        proj["CITY"] = val
                    if any(sub in norm_name for sub in ("DESIG", "DESIGNATION", "DEISGN")):
                        proj["EMPDESIGNATION"] = val
                        proj["EMPDESIG"] = val
                        proj["DESIGNATION"] = val
                        proj["EMPDEISGNATION"] = val

                projected_results.append(proj)

        if combined_rows and not is_select_all:
            first_row = combined_rows[0]
            for fld in node.fields:
                val = self._resolve_field_value_from_row(fld, first_row)
                col_name = fld.split("~")[-1].upper().replace("_", "").replace("-", "")
                has_key = any(col_name in k.replace("_", "").replace("-", "") for k in first_row.keys())
                if val == "" and not has_key:
                    self.diagnostics.append({
                        "line": node.line,
                        "severity": "warning",
                        "code": "CX_SY_OPEN_SQL_DB",
                        "message": f"Field '{fld}' in SELECT could not be mapped to any source column in joined tables.",
                    })

        if node.into_table:
            tbl_var = node.into_table.lstrip("@").upper()
            self.variables[tbl_var] = copy.deepcopy(projected_results)
            self.system_fields["SY-DBCNT"] = len(projected_results)
            self.system_fields["SY-SUBRC"] = 0 if len(projected_results) > 0 else 4
            self.last_db_failed = (len(projected_results) == 0)
        elif node.into_wa:
            wa_var = node.into_wa.lstrip("@").upper()
            if projected_results:
                self.variables[wa_var] = copy.deepcopy(projected_results[0])
                self.system_fields["SY-DBCNT"] = 1
                self.system_fields["SY-SUBRC"] = 0
                self.last_db_failed = False
            else:
                self.system_fields["SY-DBCNT"] = 0
                self.system_fields["SY-SUBRC"] = 4
                self.last_db_failed = True

        return ExecutionSignal.NONE

    def _execute_insert(self, node: InsertNode) -> int:
        if node.is_internal_table:
            target_var = node.target_table.lstrip("@").upper()
            target = self._get_variable_value(target_var)
            if not isinstance(target, list):
                if target_var not in self.variables:
                    self.variables[target_var] = []
                    target = self.variables[target_var]
                else:
                    raise ABAPRuntimeError(f"Target '{target_var}' is not an internal table.", node.line)
            wa_var = node.wa_var.lstrip("@").upper() if node.wa_var else None
            wa_val = self._get_variable_value(wa_var) if wa_var else {}
            table_kind = self.variables.get(f"__TABLE_KIND_{target_var}", "standard")
            key_def = self.variables.get(f"__KEY_DEF_{target_var}") or {}
            key_kind = key_def.get("kind", "")
            key_fields = key_def.get("fields", [])

            if key_kind == "UNIQUE" and key_fields and isinstance(wa_val, dict):
                has_dup = any(
                    all(str(row.get(kf, "")) == str(wa_val.get(kf, "")) for kf in key_fields)
                    for row in target if isinstance(row, dict)
                )
                if has_dup:
                    self.system_fields["SY-SUBRC"] = 4
                    self.last_db_failed = True
                    return ExecutionSignal.NONE

            if node.index_expr:
                if table_kind == "hashed":
                    raise ABAPRuntimeError(f"Hashed table '{target_var}' cannot be accessed by index.", node.line)
                idx = int(self._evaluate_expression(node.index_expr))
                pos = max(0, min(len(target), idx - 1))
                target.insert(pos, copy.deepcopy(wa_val))
                self.system_fields["SY-TABIX"] = pos + 1
            else:
                target.append(copy.deepcopy(wa_val))
                if table_kind == "sorted" and key_fields:
                    target.sort(key=lambda r: tuple(str(r.get(kf, "")) for kf in key_fields) if isinstance(r, dict) else str(r))
                if table_kind == "hashed":
                    self.system_fields["SY-TABIX"] = 0
                else:
                    self.system_fields["SY-TABIX"] = len(target)

            self.system_fields["SY-SUBRC"] = 0
            self.last_db_failed = False
            return ExecutionSignal.NONE

        # Database Table Insert
        dbtab_name = node.target_table.strip().upper().lstrip("@")
        table_type, dict_table, std_dataset = self._resolve_database_table(dbtab_name)

        if not table_type:
            # Target table does NOT exist in active DDIC or database catalog!
            self.system_fields["SY-SUBRC"] = 4
            self.system_fields["SY-DBCNT"] = 0
            self.last_db_failed = True
            self.diagnostics.append({
                "line": node.line,
                "severity": "error",
                "code": "CX_SY_OPEN_SQL_DB",
                "message": f"Database table or view '{dbtab_name}' not found",
            })
            return ExecutionSignal.NONE

        rows_to_insert: List[Dict[str, Any]] = []

        if node.from_table:
            from_tbl_name = node.from_table.lstrip("@").upper()
            src = self._get_variable_value(from_tbl_name)
            if not isinstance(src, list):
                raise ABAPRuntimeError(f"'{from_tbl_name}' is not an internal table.", node.line)
            if len(src) == 0:
                # An empty internal table: in ABAP, no rows inserted, sy-subrc = 0, sy-dbcnt = 0.
                self.system_fields["SY-SUBRC"] = 0
                self.system_fields["SY-DBCNT"] = 0
                self.last_db_failed = False
                return ExecutionSignal.NONE
            rows_to_insert = [copy.deepcopy(r) if isinstance(r, dict) else {"VALUE": r} for r in src]
        elif node.from_wa:
            from_wa_name = node.from_wa.lstrip("@").upper()
            src = self._get_variable_value(from_wa_name)
            rows_to_insert = [copy.deepcopy(src) if isinstance(src, dict) else {"VALUE": src}]
        elif node.values:
            val = self._evaluate_expression(node.values)
            rows_to_insert = [copy.deepcopy(val) if isinstance(val, dict) else {"VALUE": val}]

        # Retrieve existing records & schema
        if table_type == "custom":
            current_records = list(dict_table.sample_records or [])
            schema = dict_table.fields_schema or []
            key_fields = [str(f.get("field", "")).upper() for f in schema if f.get("key")]
            columns = [str(f.get("field", "")).upper() for f in schema if f.get("field")]
        elif table_type == "standard":
            current_records = list(std_dataset.get("rows", []))
            key_fields = [k.upper() for k in std_dataset.get("key_fields", [])]
            columns = [c.get("name", "").upper() for c in std_dataset.get("columns", []) if c.get("name")]
        else:  # synthetic
            current_records = list(std_dataset.get("rows", []))
            key_fields = [k.upper() for k in std_dataset.get("key_fields", [])]
            columns = [c.get("name", "").upper() for c in std_dataset.get("columns", []) if c.get("name")]

        prepared_rows: List[Dict[str, Any]] = []
        for raw_row in rows_to_insert:
            if not isinstance(raw_row, dict):
                raw_row = {"VALUE": raw_row}
            clean_row = {str(k).upper(): v for k, v in raw_row.items()}
            if "MANDT" in columns and ("MANDT" not in clean_row or not clean_row["MANDT"]):
                clean_row["MANDT"] = self.system_fields.get("SY-MANDT", "100")

            if columns:
                mapped_row = {}
                for col in columns:
                    val = self._resolve_field_value_from_row(col, clean_row)
                    if val != "":
                        mapped_row[col] = val
                    elif col in clean_row:
                        mapped_row[col] = clean_row[col]
                    elif col == "MANDT":
                        mapped_row["MANDT"] = self.system_fields.get("SY-MANDT", "100")
                    else:
                        mapped_row[col] = clean_row.get(col, "")
                clean_row = mapped_row

            prepared_rows.append(clean_row)

        # Check duplicate primary key across existing records and within batch
        has_duplicate = False
        if key_fields:
            existing_keys = set()
            for ex in current_records:
                existing_keys.add(tuple(str(ex.get(k, "")) for k in key_fields))
            batch_keys = set()
            for cand in prepared_rows:
                c_tuple = tuple(str(cand.get(k, "")) for k in key_fields)
                if c_tuple in existing_keys or c_tuple in batch_keys:
                    has_duplicate = True
                    break
                batch_keys.add(c_tuple)

        if has_duplicate:
            self.system_fields["SY-SUBRC"] = 4
            self.system_fields["SY-DBCNT"] = 0
            self.last_db_failed = True
            self.diagnostics.append({
                "line": node.line,
                "severity": "warning",
                "code": "CX_SY_OPEN_SQL_DB",
                "message": f"Duplicate key violation in table '{dbtab_name}'. No duplicate row inserted.",
            })
            return ExecutionSignal.NONE

        current_records.extend(prepared_rows)
        if table_type == "custom":
            dict_table.sample_records = current_records
            dict_table.save(update_fields=["sample_records", "updated_at"])
        elif table_type in ("standard", "synthetic"):
            std_dataset["rows"] = current_records

        self.system_fields["SY-DBCNT"] = len(prepared_rows)
        self.system_fields["SY-SUBRC"] = 0
        self.last_db_failed = False
        return ExecutionSignal.NONE

    def _execute_update(self, node: UpdateNode) -> int:
        dbtab_name = node.target_table.strip().upper().lstrip("@")
        table_type, dict_table, std_dataset = self._resolve_database_table(dbtab_name)
        if not table_type:
            self.system_fields["SY-SUBRC"] = 4
            self.system_fields["SY-DBCNT"] = 0
            self.last_db_failed = True
            self.diagnostics.append({
                "line": node.line,
                "severity": "error",
                "code": "CX_SY_OPEN_SQL_DB",
                "message": f"Database table or view '{dbtab_name}' not found",
            })
            return ExecutionSignal.NONE

        if table_type == "custom":
            current_records = list(dict_table.sample_records or [])
            key_fields = self._get_table_key_fields(dict_table, dbtab_name)
        else:
            current_records = list(std_dataset.get("rows", []))
            key_fields = [k.upper() for k in std_dataset.get("key_fields", [])]

        updated_count = 0

        if node.set_assignments:
            cond_fn = self._build_where_filter(node.where_tokens)
            eval_values = {f.upper(): self._evaluate_expression(tokens) for f, tokens in node.set_assignments.items()}
            for row in current_records:
                if cond_fn(row):
                    for f, val in eval_values.items():
                        row[f] = val
                    updated_count += 1
        elif node.from_table:
            from_tbl_name = node.from_table.lstrip("@").upper()
            src = self._get_variable_value(from_tbl_name)
            if not isinstance(src, list):
                raise ABAPRuntimeError(f"'{from_tbl_name}' is not an internal table.", node.line)
            for new_row in src:
                if not isinstance(new_row, dict):
                    continue
                clean_new = {str(k).upper(): v for k, v in new_row.items()}
                for existing in current_records:
                    if self._match_keys(existing, clean_new, key_fields):
                        existing.update(clean_new)
                        updated_count += 1
                        break
        elif node.from_wa:
            from_wa_name = node.from_wa.lstrip("@").upper()
            new_row = self._get_variable_value(from_wa_name)
            if isinstance(new_row, dict):
                clean_new = {str(k).upper(): v for k, v in new_row.items()}
                for existing in current_records:
                    if self._match_keys(existing, clean_new, key_fields):
                        existing.update(clean_new)
                        updated_count += 1
                        break

        if table_type == "custom":
            dict_table.sample_records = current_records
            dict_table.save(update_fields=["sample_records", "updated_at"])
        elif table_type in ("standard", "synthetic"):
            std_dataset["rows"] = current_records

        self.system_fields["SY-DBCNT"] = updated_count
        self.system_fields["SY-SUBRC"] = 0 if updated_count > 0 else 4
        self.last_db_failed = (updated_count == 0)
        return ExecutionSignal.NONE

    def _execute_modify(self, node: ModifyNode) -> int:
        if not getattr(node, "is_dbtab", False):
            target_var = node.target_table.lstrip("@").upper()
            target = self._get_variable_value(target_var)
            if isinstance(target, list):
                idx = self.system_fields["SY-TABIX"]
                if node.index_expr:
                    idx = int(self._evaluate_expression(node.index_expr))
                if 1 <= idx <= len(target):
                    src_val = self._get_variable_value(node.source_var.lstrip("@").upper()) if node.source_var else {}
                    target[idx - 1] = copy.deepcopy(src_val)
                    self.system_fields["SY-SUBRC"] = 0
                    self.last_db_failed = False
                else:
                    self.system_fields["SY-SUBRC"] = 4
                    self.last_db_failed = True
                return ExecutionSignal.NONE

        return self._execute_modify_db(node)

    def _execute_modify_db(self, node: ModifyNode) -> int:
        dbtab_name = node.target_table.strip().upper().lstrip("@")
        table_type, dict_table, std_dataset = self._resolve_database_table(dbtab_name)
        if not table_type:
            self.system_fields["SY-SUBRC"] = 4
            self.system_fields["SY-DBCNT"] = 0
            self.last_db_failed = True
            self.diagnostics.append({
                "line": node.line,
                "severity": "error",
                "code": "CX_SY_OPEN_SQL_DB",
                "message": f"Database table or view '{dbtab_name}' not found",
            })
            return ExecutionSignal.NONE

        if table_type == "custom":
            current_records = list(dict_table.sample_records or [])
            key_fields = self._get_table_key_fields(dict_table, dbtab_name)
            columns = [str(f.get("field", "")).upper() for f in (dict_table.fields_schema or []) if f.get("field")]
        else:
            current_records = list(std_dataset.get("rows", []))
            key_fields = [k.upper() for k in std_dataset.get("key_fields", [])]
            columns = [c.get("name", "").upper() for c in std_dataset.get("columns", []) if c.get("name")]

        count = 0
        rows_to_upsert: List[Dict[str, Any]] = []
        if getattr(node, "from_table", None):
            src_name = node.from_table.lstrip("@").upper()
            src = self._get_variable_value(src_name)
            if isinstance(src, list):
                rows_to_upsert = [copy.deepcopy(r) if isinstance(r, dict) else {"VALUE": r} for r in src]
        elif node.source_var:
            src_name = node.source_var.lstrip("@").upper()
            src = self._get_variable_value(src_name)
            if isinstance(src, dict):
                rows_to_upsert = [copy.deepcopy(src)]

        for item in rows_to_upsert:
            clean_item = {str(k).upper(): v for k, v in item.items()}
            if "MANDT" in columns and ("MANDT" not in clean_item or not clean_item["MANDT"]):
                clean_item["MANDT"] = self.system_fields.get("SY-MANDT", "100")
            if columns:
                mapped_item = {}
                for col in columns:
                    val = self._resolve_field_value_from_row(col, clean_item)
                    if val != "":
                        mapped_item[col] = val
                    elif col in clean_item:
                        mapped_item[col] = clean_item[col]
                    elif col == "MANDT":
                        mapped_item["MANDT"] = self.system_fields.get("SY-MANDT", "100")
                    else:
                        mapped_item[col] = clean_item.get(col, "")
                clean_item = mapped_item
            found = False
            for existing in current_records:
                if self._match_keys(existing, clean_item, key_fields):
                    existing.update(clean_item)
                    found = True
                    count += 1
                    break
            if not found:
                current_records.append(clean_item)
                count += 1

        if table_type == "custom":
            dict_table.sample_records = current_records
            dict_table.save(update_fields=["sample_records", "updated_at"])
        elif table_type in ("standard", "synthetic"):
            std_dataset["rows"] = current_records

        self.system_fields["SY-DBCNT"] = count
        self.system_fields["SY-SUBRC"] = 0
        self.last_db_failed = False
        return ExecutionSignal.NONE

    def _execute_delete(self, node: DeleteNode) -> int:
        if not getattr(node, "is_dbtab", False):
            target_var = node.target_table.lstrip("@").upper()
            target = self._get_variable_value(target_var)
            if isinstance(target, list):
                if node.index_expr:
                    idx = int(self._evaluate_expression(node.index_expr))
                    if 1 <= idx <= len(target):
                        del target[idx - 1]
                        self.system_fields["SY-SUBRC"] = 0
                        self.last_db_failed = False
                    else:
                        self.system_fields["SY-SUBRC"] = 4
                        self.last_db_failed = True
                    return ExecutionSignal.NONE
                elif node.where_tokens:
                    cond_fn = self._build_where_filter(node.where_tokens)
                    new_table = [r for r in target if not cond_fn(r)]
                    deleted = len(target) - len(new_table)
                    target.clear()
                    target.extend(new_table)
                    self.system_fields["SY-SUBRC"] = 0 if deleted > 0 else 4
                    self.system_fields["SY-DBCNT"] = deleted
                    self.last_db_failed = (deleted == 0)
                    return ExecutionSignal.NONE

        # Database table delete
        dbtab_name = node.target_table.strip().upper().lstrip("@")
        table_type, dict_table, std_dataset = self._resolve_database_table(dbtab_name)
        if not table_type:
            self.system_fields["SY-SUBRC"] = 4
            self.system_fields["SY-DBCNT"] = 0
            self.last_db_failed = True
            self.diagnostics.append({
                "line": node.line,
                "severity": "error",
                "code": "CX_SY_OPEN_SQL_DB",
                "message": f"Database table or view '{dbtab_name}' not found",
            })
            return ExecutionSignal.NONE

        if table_type == "custom":
            current_records = list(dict_table.sample_records or [])
            key_fields = self._get_table_key_fields(dict_table, dbtab_name)
        else:
            current_records = list(std_dataset.get("rows", []))
            key_fields = [k.upper() for k in std_dataset.get("key_fields", [])]

        deleted_count = 0

        if getattr(node, "from_table", None):
            src_name = node.from_table.lstrip("@").upper()
            src = self._get_variable_value(src_name)
            if isinstance(src, list):
                key_fields = self._get_table_key_fields(dict_table, dbtab_name)
                to_delete = []
                for row in current_records:
                    if any(self._match_keys(row, {str(k).upper(): v for k, v in s_row.items()}, key_fields) for s_row in src if isinstance(s_row, dict)):
                        to_delete.append(row)
                for d in to_delete:
                    current_records.remove(d)
                deleted_count = len(to_delete)
        elif getattr(node, "from_wa", None):
            wa_name = node.from_wa.lstrip("@").upper()
            wa = self._get_variable_value(wa_name)
            if isinstance(wa, dict):
                clean_wa = {str(k).upper(): v for k, v in wa.items()}
                to_delete = [r for r in current_records if self._match_keys(r, clean_wa, key_fields)]
                for d in to_delete:
                    current_records.remove(d)
                deleted_count = len(to_delete)
        elif node.where_tokens:
            cond_fn = self._build_where_filter(node.where_tokens)
            to_keep = [r for r in current_records if not cond_fn(r)]
            deleted_count = len(current_records) - len(to_keep)
            current_records.clear()
            current_records.extend(to_keep)
        else:
            deleted_count = len(current_records)
            current_records.clear()

        if table_type == "custom":
            dict_table.sample_records = current_records
            dict_table.save(update_fields=["sample_records", "updated_at"])
        elif table_type in ("standard", "synthetic"):
            std_dataset["rows"] = current_records

        self.system_fields["SY-DBCNT"] = deleted_count
        self.system_fields["SY-SUBRC"] = 0 if deleted_count > 0 else 4
        self.last_db_failed = (deleted_count == 0)
        return ExecutionSignal.NONE

    def _execute_commit_work(self, node: CommitWorkNode) -> int:
        if getattr(self, "last_db_failed", False):
            # A preceding database operation failed; COMMIT WORK must not mask the failure
            return ExecutionSignal.NONE
        self.system_fields["SY-SUBRC"] = 0
        return ExecutionSignal.NONE

    def _execute_rollback_work(self, node: RollbackWorkNode) -> int:
        self.last_db_failed = False
        self.system_fields["SY-SUBRC"] = 0
        return ExecutionSignal.NONE

    def _run_semantic_analysis(self, ast_nodes: List[ASTNode]):
        # 1. Superclass existence and final superclass check
        for cls_name, cls in self.classes.items():
            if cls.superclass:
                if cls.superclass not in self.classes:
                    line = cls.def_node.line if cls.def_node else 1
                    raise ABAPRuntimeError(f"Superclass '{cls.superclass}' not found for class '{cls.name}'.", line)
                super_cls = self.classes[cls.superclass]
                if super_cls.is_final:
                    line = cls.def_node.line if cls.def_node else 1
                    raise ABAPRuntimeError(f"Cannot inherit from FINAL class '{cls.superclass}'.", line)

        # 2. Inheritance cycle detection
        for cls_name, cls in self.classes.items():
            curr = cls
            visited = set()
            while curr and curr.superclass:
                visited.add(curr.name)
                if curr.superclass in visited:
                    line = cls.def_node.line if cls.def_node else 1
                    raise ABAPRuntimeError(f"Inheritance cycle detected involving class '{curr.superclass}'.", line)
                curr = self.classes.get(curr.superclass)

        # 3. Method redefinition validation
        for cls_name, cls in self.classes.items():
            for m_upper, m_info in cls.methods_def.items():
                if m_info.get("is_redefinition"):
                    found_super_def = None
                    curr_super = self.classes.get(cls.superclass) if cls.superclass else None
                    while curr_super:
                        if m_upper in curr_super.methods_def:
                            found_super_def = curr_super.methods_def[m_upper]
                            break
                        curr_super = self.classes.get(curr_super.superclass) if curr_super.superclass else None
                    if not found_super_def:
                        line = cls.def_node.line if cls.def_node else 1
                        raise ABAPRuntimeError(f"Method '{m_upper}' in class '{cls.name}' marked REDEFINITION but not found in any superclass.", line)
                    if found_super_def.get("is_final"):
                        line = cls.def_node.line if cls.def_node else 1
                        raise ABAPRuntimeError(f"Cannot redefine FINAL method '{m_upper}' in class '{cls.name}'.", line)

        # 4. Abstract method implementation check for concrete classes
        for cls_name, cls in self.classes.items():
            if not cls.is_abstract and cls.def_node:
                curr_super = self.classes.get(cls.superclass) if cls.superclass else None
                while curr_super:
                    for sm_upper, sm_info in curr_super.methods_def.items():
                        if sm_info.get("is_abstract"):
                            impl = cls.find_method_impl(sm_upper, self.classes)
                            if not impl or not impl[1]:
                                line = cls.def_node.line if cls.def_node else 1
                                raise ABAPRuntimeError(f"Concrete class '{cls.name}' must implement abstract method '{sm_upper}' from superclass '{curr_super.name}'.", line)
                    curr_super = self.classes.get(curr_super.superclass) if curr_super.superclass else None

        # 5. Interface implementation check for concrete classes
        for cls_name, cls in self.classes.items():
            if cls.def_node and cls.interfaces:
                for intf_name in cls.interfaces:
                    if intf_name in self.interfaces:
                        intf = self.interfaces[intf_name]
                        for im_upper in intf.methods_def.keys():
                            qual = f"{intf_name}~{im_upper}"
                            has_impl = (qual in cls.methods_impl) or (im_upper in cls.methods_impl)
                            if not has_impl:
                                super_impl = cls.find_method_impl(qual, self.classes) or cls.find_method_impl(im_upper, self.classes)
                                if not super_impl:
                                    line = cls.def_node.line if cls.def_node else 1
                                    raise ABAPRuntimeError(f"Class '{cls.name}' does not implement interface method '{qual}'.", line)

    def _is_subclass_of(self, child_name: str, parent_name: str) -> bool:
        if not child_name or not parent_name:
            return False
        curr = self.classes.get(child_name.upper())
        while curr:
            if curr.name == parent_name.upper():
                return True
            curr = self.classes.get(curr.superclass) if curr.superclass else None
        return False

    def _check_member_access(self, target_class: ABAPClass, member_name: str, member_kind: str, line: int):
        m_upper = member_name.upper()
        def_info = None
        defining_class = target_class.name

        if member_kind == "method":
            res = target_class.find_method_def(m_upper, self.classes, self.interfaces)
            if res:
                defining_class, def_info = res
        else:
            res = target_class.find_attribute_def(m_upper, self.classes)
            if res:
                def_class_obj, def_info = res
                defining_class = def_class_obj.name

        if not def_info:
            return

        vis = def_info.get("visibility", "PUBLIC") if isinstance(def_info, dict) else getattr(def_info, "visibility", "PUBLIC")
        vis = (vis or "PUBLIC").upper()

        if vis == "PUBLIC":
            return

        caller_class = self.current_class

        if vis == "PRIVATE":
            if caller_class != defining_class:
                raise ABAPRuntimeError(f"Cannot access PRIVATE {member_kind} '{member_name}' of class '{defining_class}' from '{caller_class or 'main program'}'.", line)

        elif vis == "PROTECTED":
            if not caller_class:
                raise ABAPRuntimeError(f"Cannot access PROTECTED {member_kind} '{member_name}' of class '{defining_class}' from outside class hierarchy.", line)
            is_related = (caller_class == defining_class) or self._is_subclass_of(caller_class, defining_class) or self._is_subclass_of(defining_class, caller_class)
            if not is_related:
                raise ABAPRuntimeError(f"Cannot access PROTECTED {member_kind} '{member_name}' of class '{defining_class}' from unrelated class '{caller_class}'.", line)

    def _ensure_class_constructor_run(self, cls_name: str):
        if not cls_name or cls_name not in self.classes:
            return
        cls = self.classes[cls_name]
        if cls.class_constructor_ran:
            return
        if cls.superclass and cls.superclass in self.classes:
            self._ensure_class_constructor_run(cls.superclass)
        cls.class_constructor_ran = True
        if "CLASS_CONSTRUCTOR" in cls.methods_impl:
            impl = cls.methods_impl["CLASS_CONSTRUCTOR"]
            m_def = cls.methods_def.get("CLASS_CONSTRUCTOR", {})
            dummy_call = CallMethodNode(target_obj=cls_name, method_name="CLASS_CONSTRUCTOR", is_static=True, line=1)
            self._run_method_impl(None, cls, "CLASS_CONSTRUCTOR", impl, m_def, dummy_call)

    def _execute_create_object(self, node: CreateObjectNode) -> int:
        cls_name = node.class_name
        if not cls_name:
            type_hint = self.variables.get(f"__TYPE_{node.target_var}", "")
            if "REF_TO_" in type_hint:
                cls_name = type_hint.replace("REF_TO_", "").strip()
            elif "REF TO" in type_hint.upper():
                cls_name = type_hint.upper().split("REF TO")[-1].strip()

        if not cls_name:
            cls_name = f"CLS_{node.target_var}"

        cls_name = cls_name.upper()
        if cls_name not in self.classes:
            self.classes[cls_name] = ABAPClass(cls_name)

        target_class = self.classes[cls_name]
        if target_class.is_abstract:
            raise ABAPRuntimeError(f"Cannot instantiate ABSTRACT class '{cls_name}'.", node.line)

        # Access visibility check for instantiation
        create_vis = (target_class.create_visibility or "PUBLIC").upper()
        if create_vis == "PRIVATE":
            if self.current_class != cls_name:
                raise ABAPRuntimeError(f"Class '{cls_name}' has CREATE PRIVATE and cannot be instantiated from outside.", node.line)
        elif create_vis == "PROTECTED":
            if not self.current_class or not (self.current_class == cls_name or self._is_subclass_of(self.current_class, cls_name)):
                raise ABAPRuntimeError(f"Class '{cls_name}' has CREATE PROTECTED and cannot be instantiated outside its inheritance hierarchy.", node.line)

        # Ensure static constructors run
        self._ensure_class_constructor_run(cls_name)

        instance = ABAPInstance(target_class, self.classes)
        self.variables[node.target_var] = instance

        # If CONSTRUCTOR method exists, execute it
        ctor_lookup = target_class.find_method_impl("CONSTRUCTOR", self.classes)
        if ctor_lookup:
            defining_cls, ctor_impl = ctor_lookup
            ctor_def = defining_cls.methods_def.get("CONSTRUCTOR", {})
            ctor_call = CallMethodNode(
                target_obj=node.target_var,
                method_name="CONSTRUCTOR",
                is_static=False,
                exporting=node.exporting,
                line=node.line,
            )
            self._run_method_impl(instance, defining_cls, "CONSTRUCTOR", ctor_impl, ctor_def, ctor_call)

        return ExecutionSignal.NONE

    def _execute_call_method(self, node: CallMethodNode) -> int:
        method_name = node.method_name.upper()
        target_obj = node.target_obj.upper()

        target_class: Optional[ABAPClass] = None
        target_instance: Optional[ABAPInstance] = None

        if node.is_static or target_obj in self.classes:
            target_class = self.classes.get(target_obj)
            if not target_class:
                raise ABAPRuntimeError(f"Class '{target_obj}' not defined for static method call.", node.line)
            self._ensure_class_constructor_run(target_class.name)
            self._check_member_access(target_class, method_name, "method", node.line)
            impl_lookup = target_class.find_method_impl(method_name, self.classes)
            if not impl_lookup:
                self.diagnostics.append(
                    {
                        "line": node.line,
                        "severity": "warning",
                        "message": f"Method '{method_name}' has no implementation in class '{target_class.name}'.",
                    }
                )
                return ExecutionSignal.NONE
            impl_class, method_impl = impl_lookup
            method_def = impl_class.methods_def.get(method_name, {})
            self._run_method_impl(None, impl_class, method_name, method_impl, method_def, node)
            return ExecutionSignal.NONE

        elif target_obj == "SUPER":
            if not self.current_instance or not self.current_class:
                raise ABAPRuntimeError("'SUPER' referenced outside of an instance method context.", node.line)
            curr_c = self.classes.get(self.current_class)
            if not curr_c or not curr_c.superclass:
                raise ABAPRuntimeError(f"Class '{self.current_class}' has no superclass to call via SUPER->.", node.line)
            super_c = self.classes.get(curr_c.superclass)
            if not super_c:
                raise ABAPRuntimeError(f"Superclass '{curr_c.superclass}' not found.", node.line)
            impl_lookup = super_c.find_method_impl(method_name, self.classes)
            if not impl_lookup:
                raise ABAPRuntimeError(f"Method '{method_name}' not implemented in superclass hierarchy of '{self.current_class}'.", node.line)
            impl_class, method_impl = impl_lookup
            method_def = impl_class.methods_def.get(method_name, {})
            self._run_method_impl(self.current_instance, impl_class, method_name, method_impl, method_def, node)
            return ExecutionSignal.NONE

        elif target_obj == "ME":
            if not self.current_instance:
                raise ABAPRuntimeError("'ME' referenced outside of an instance method context.", node.line)
            target_instance = self.current_instance
            target_class = target_instance.abap_class

        else:
            instance = self._get_variable_value(target_obj)
            if instance is None and target_obj in self.variables:
                raise ABAPException("CX_SY_REF_IS_INITIAL", f"Object reference '{target_obj}' is initial (Null Object Reference).", node.line)
            if not isinstance(instance, ABAPInstance):
                raise ABAPRuntimeError(f"Variable '{target_obj}' is not an instantiated object (call to {method_name}).", node.line)
            target_instance = instance
            target_class = instance.abap_class

        # Instance method dynamic dispatch
        self._check_member_access(target_class, method_name, "method", node.line)
        impl_lookup = target_class.find_method_impl(method_name, self.classes)
        if not impl_lookup:
            self.diagnostics.append(
                {
                    "line": node.line,
                    "severity": "warning",
                    "message": f"Method '{method_name}' has no implementation in class '{target_class.name}'.",
                }
            )
            return ExecutionSignal.NONE

        impl_class, method_impl = impl_lookup
        method_def = impl_class.methods_def.get(method_name, {})
        self._run_method_impl(target_instance, impl_class, method_name, method_impl, method_def, node)
        return ExecutionSignal.NONE

    def _run_method_impl(
        self,
        target_instance: Optional[ABAPInstance],
        target_class: ABAPClass,
        method_name: str,
        method_impl: Any,
        method_def: Dict[str, Any],
        call_node: CallMethodNode,
    ) -> Any:
        # Handle native callable method implementations (e.g. CL_SQL_STATEMENT, CX_ROOT)
        if callable(method_impl):
            args: Dict[str, Any] = {}
            for p_name, p_tokens in call_node.exporting.items():
                args[p_name.upper()] = self._evaluate_expression(p_tokens)

            importing_def = method_def.get("importing", {})
            param_keys = list(importing_def.keys())
            call_args = {}
            for k, v in args.items():
                if k.startswith("PARAM_"):
                    try:
                        idx = int(k.replace("PARAM_", "")) - 1
                        if idx < len(param_keys):
                            call_args[param_keys[idx]] = v
                        else:
                            call_args[k] = v
                    except ValueError:
                        call_args[k] = v
                else:
                    call_args[k] = v

            res_val = method_impl(target_instance, call_args, call_node.line)
            if call_node.receiving:
                self._set_variable_value(call_node.receiving, res_val, call_node.line)
            if call_node.assign_to:
                self._set_variable_value(call_node.assign_to, res_val, call_node.line)
            return res_val

        # User-defined ABAP Method execution
        caller_args: Dict[str, Any] = {}
        for p_name, p_tokens in call_node.exporting.items():
            caller_args[p_name.upper()] = self._evaluate_expression(p_tokens)

        # Context switch: Save current state
        prev_instance = self.current_instance
        prev_class = self.current_class
        prev_vars = dict(self.variables)

        self.current_instance = target_instance
        self.current_class = target_class.name

        importing_def = method_def.get("importing", {})
        param_keys = list(importing_def.keys())

        # Bind parameters to local scope
        for k, v in caller_args.items():
            if k.startswith("PARAM_"):
                try:
                    idx = int(k.replace("PARAM_", "")) - 1
                    if idx < len(param_keys):
                        self.variables[param_keys[idx]] = v
                    else:
                        self.variables[k] = v
                except ValueError:
                    self.variables[k] = v
            else:
                self.variables[k] = v

        for p_k, p_type in importing_def.items():
            if p_k not in self.variables:
                self.variables[p_k] = self._default_value_for_type(p_type)

        changing_def = method_def.get("changing", {})
        for c_k, c_type in changing_def.items():
            if c_k not in self.variables:
                self.variables[c_k] = self._default_value_for_type(c_type)

        exporting_def = method_def.get("exporting", {})
        for e_k, e_type in exporting_def.items():
            if e_k not in self.variables:
                self.variables[e_k] = self._default_value_for_type(e_type)

        returning_info = method_def.get("returning")
        ret_var_name = returning_info[0].upper() if returning_info else "RESULT"
        ret_var_type = returning_info[1].upper() if returning_info else "STRING"
        if ret_var_name not in self.variables:
            self.variables[ret_var_name] = self._default_value_for_type(ret_var_type)

        result_val = ""
        captured_changing = {}
        try:
            self._execute_block(method_impl.body)
            result_val = self.variables.get(ret_var_name, "")
            captured_changing = {c_k: self.variables.get(c_k) for c_k in changing_def}
        finally:
            self.variables = prev_vars
            self.current_instance = prev_instance
            self.current_class = prev_class

        for c_k, c_val in captured_changing.items():
            caller_toks = call_node.exporting.get(c_k)
            if caller_toks and len(caller_toks) == 1:
                caller_var = caller_toks[0].value.upper()
                if caller_var in self.variables:
                    self.variables[caller_var] = c_val

        if call_node.receiving:
            self._set_variable_value(call_node.receiving, result_val, call_node.line)
        if call_node.assign_to:
            self._set_variable_value(call_node.assign_to, result_val, call_node.line)

        return result_val

    def _execute_try_block(self, node: TryNode) -> int:
        exception_caught: Optional[ABAPException] = None
        sig = ExecutionSignal.NONE

        try:
            sig = self._execute_block(node.try_body)
        except ABAPException as exc:
            exception_caught = exc
        except ABAPRuntimeError as err:
            exc_class = "CX_SQL_EXCEPTION" if ("SQL" in err.message.upper() or "TABLE" in err.message.upper()) else "CX_ROOT"
            exception_caught = ABAPException(exc_class=exc_class, message=err.message, line=err.line)

        if exception_caught:
            # Find matching catch branch
            matched_branch = None
            for branch in node.catch_branches:
                if self._matches_exception(exception_caught.exc_class, branch["classes"]):
                    matched_branch = branch
                    break

            if matched_branch:
                exc_cls_name = exception_caught.exc_class
                if exc_cls_name not in self.classes:
                    self._register_builtin_exception_class(exc_cls_name)

                exc_instance = ABAPInstance(self.classes[exc_cls_name], self.classes)
                exc_instance.attributes["MESSAGE"] = exception_caught.message

                target_var = matched_branch.get("target_var")
                if target_var:
                    self.variables[target_var.upper()] = exc_instance

                sig = self._execute_block(matched_branch["body"])
            else:
                # Re-raise uncaught exception
                raise exception_caught

        return sig

    def _matches_exception(self, thrown_class: str, target_classes: List[str]) -> bool:
        thrown = thrown_class.upper().strip()
        ancestors = EXCEPTION_HIERARCHY.get(thrown, [thrown, "CX_ROOT"])
        for tc in target_classes:
            target = tc.upper().strip()
            if target == "CX_ROOT" or target == thrown or target in ancestors:
                return True
        return False

    def _register_builtin_classes(self):
        # 1. System class CL_SQL_STATEMENT
        sql_cls = ABAPClass("CL_SQL_STATEMENT")
        sql_cls.methods_def["EXECUTE_DDL"] = {
            "name": "EXECUTE_DDL",
            "is_static": False,
            "importing": {"STMT": "STRING"},
            "returning": None,
        }
        sql_cls.methods_def["EXECUTE_UPDATE"] = {
            "name": "EXECUTE_UPDATE",
            "is_static": False,
            "importing": {"STMT": "STRING"},
            "returning": ("ROWS_PROCESSED", "I"),
        }
        sql_cls.methods_impl["EXECUTE_DDL"] = self._native_execute_ddl
        sql_cls.methods_impl["EXECUTE_UPDATE"] = self._native_execute_update
        self.classes["CL_SQL_STATEMENT"] = sql_cls

        # 2. System Exception classes
        for exc_name in ("CX_ROOT", "CX_SQL_EXCEPTION", "CX_SY_OPEN_SQL_ERROR", "CX_DYNAMIC_CHECK", "CX_NO_CHECK", "CX_STATIC_CHECK"):
            self._register_builtin_exception_class(exc_name)

    def _register_builtin_exception_class(self, exc_name: str) -> ABAPClass:
        clean = exc_name.upper().strip()
        if clean in self.classes:
            return self.classes[clean]
        exc_cls = ABAPClass(clean)
        exc_cls.methods_def["GET_TEXT"] = {
            "name": "GET_TEXT",
            "is_static": False,
            "importing": {},
            "returning": ("RESULT", "STRING"),
        }
        exc_cls.methods_impl["GET_TEXT"] = self._native_get_text
        self.classes[clean] = exc_cls
        return exc_cls

    def _native_get_text(self, instance: Optional[ABAPInstance], call_args: Dict[str, Any], line: int) -> str:
        if instance and "MESSAGE" in instance.attributes:
            return str(instance.attributes["MESSAGE"])
        return "An ABAP exception occurred."

    def _native_execute_ddl(self, instance: Optional[ABAPInstance], call_args: Dict[str, Any], line: int) -> Any:
        sql = call_args.get("STMT")
        if sql is None:
            sql = call_args.get("PARAM_1")
        if sql is None and call_args:
            sql = next(iter(call_args.values()))
        if not sql:
            sql = ""

        sql = str(sql).strip()
        if sql.endswith(";") or sql.endswith("."):
            sql = sql[:-1].strip()

        words = sql.split()
        if not words:
            raise ABAPException("CX_SQL_EXCEPTION", "SQL error in DDL statement: Statement is empty.", line)

        first_word = words[0].upper()
        first_two = " ".join(words[:2]).upper() if len(words) >= 2 else first_word

        if first_two == "CREATE TABLE":
            self._ddl_create_table(sql, line)
        elif first_two == "DROP TABLE":
            self._ddl_drop_table(sql, line)
        else:
            raise ABAPException(
                "CX_SQL_EXCEPTION",
                f"SQL error in DDL statement: Command '{first_word}' is not supported in DDL mode. Only CREATE TABLE and DROP TABLE are supported.",
                line,
            )
        return None

    def _ddl_create_table(self, sql: str, line: int):
        import re
        import uuid

        match = re.match(r"(?i)^CREATE\s+TABLE\s+([a-zA-Z0-9_#]+)\s*\((.*)\)\s*$", sql, re.DOTALL)
        if not match:
            raise ABAPException("CX_SQL_EXCEPTION", f"SQL error in DDL statement: Invalid CREATE TABLE syntax in '{sql}'.", line)

        table_name = match.group(1).upper().strip()
        cols_body = match.group(2).strip()

        # Check if table already exists in database
        table_type, _, _ = self._resolve_database_table(table_name)
        if table_type is not None or get_standard_table(table_name, user_id=self.user_id, project_id=self.project_id) is not None:
            raise ABAPException(
                "CX_SQL_EXCEPTION",
                f"Database table already exists. Table '{table_name}' already exists in database schema.",
                line,
            )

        # Parse column definitions
        col_chunks: List[str] = []
        cur_chunk = ""
        b_depth = 0
        for ch in cols_body:
            if ch == "(":
                b_depth += 1
                cur_chunk += ch
            elif ch == ")":
                b_depth -= 1
                cur_chunk += ch
            elif ch == "," and b_depth == 0:
                col_chunks.append(cur_chunk.strip())
                cur_chunk = ""
            else:
                cur_chunk += ch
        if cur_chunk.strip():
            col_chunks.append(cur_chunk.strip())

        if not col_chunks:
            raise ABAPException("CX_SQL_EXCEPTION", f"SQL error in DDL statement: Table '{table_name}' has no columns.", line)

        fields_schema: List[Dict[str, Any]] = []
        for chunk in col_chunks:
            parts = chunk.split()
            if not parts:
                continue

            # Handle table constraint: PRIMARY KEY (col1, col2, ...)
            if parts[0].upper() == "PRIMARY" and len(parts) > 1 and parts[1].upper().startswith("KEY"):
                pk_match = re.search(r"\(([^)]+)\)", chunk)
                if pk_match:
                    pk_cols = [c.strip().upper() for c in pk_match.group(1).split(",")]
                    for f in fields_schema:
                        if f["field"] in pk_cols:
                            f["key"] = True
                continue

            col_name = parts[0].upper().strip()
            raw_type = parts[1].upper().strip() if len(parts) > 1 else "VARCHAR(30)"
            is_key = ("PRIMARY" in chunk.upper() and "KEY" in chunk.upper()) or ("KEY" in [p.upper() for p in parts[1:]])

            len_match = re.search(r"\((\d+)(?:,\s*\d+)?\)", raw_type)
            length = int(len_match.group(1)) if len_match else 10
            base_type = raw_type.split("(")[0].strip()

            if base_type in ("NVARCHAR", "VARCHAR", "CHAR", "TEXT", "STRING"):
                abap_type = "CHAR"
            elif base_type in ("INTEGER", "INT", "INT4", "BIGINT", "INT8"):
                abap_type = "INT4"
                length = 10
            elif base_type in ("DECIMAL", "NUMERIC", "CURR", "FLOAT", "DOUBLE"):
                abap_type = "CURR"
                length = 15
            elif base_type in ("DATE", "DATS"):
                abap_type = "DATS"
                length = 8
            elif base_type in ("TIME", "TIMS"):
                abap_type = "TIMS"
                length = 6
            elif base_type == "CLNT":
                abap_type = "CLNT"
                length = 3
            else:
                abap_type = "CHAR"

            fields_schema.append({
                "field": col_name,
                "name": col_name,
                "key": is_key,
                "type": abap_type,
                "length": length,
                "description": f"Field {col_name}",
            })

        if not any(f.get("key") for f in fields_schema):
            raise ABAPException("CX_SQL_EXCEPTION", f"SQL error in DDL statement: Table '{table_name}' must define at least one primary key field.", line)

        # Stateless direct engine use retains an in-memory table. Requests with
        # an authenticated workspace use the user's database record below.
        if self.user_id is None:
            register_custom_synthetic_table(
                table_name=table_name,
                columns=fields_schema,
                description=f"Transparent Application Table {table_name}",
                rows=[],
            )

        # Register in Django DB model if active
        try:
            from ..abap_models import ABAPDictionaryTable, ABAPProject
            query = ABAPDictionaryTable.objects.filter(table_name=table_name, user_id=self.user_id) if self.user_id else ABAPDictionaryTable.objects.filter(table_name=table_name)
            if self.project_id and self.user_id:
                query = query.filter(project__project_id=self.project_id, project__user_id=self.user_id)
            elif self.user_id:
                query = query.filter(project__isnull=True)
            project = ABAPProject.objects.filter(project_id=self.project_id, user_id=self.user_id).first() if self.project_id and self.user_id else None
            query.get_or_create(defaults={
                "table_id": f"tabl_{uuid.uuid4().hex[:12]}",
                "user_id": self.user_id,
                "project": project,
                "description": f"Transparent Application Table {table_name}",
                "delivery_class": "A",
                "fields_schema": fields_schema,
                "sample_records": [],
            })
        except Exception as exc:
            if self.user_id is not None:
                raise ABAPException("CX_SQL_EXCEPTION", f"Could not save table '{table_name}' in this workspace: {exc}", line)

    def _ddl_drop_table(self, sql: str, line: int):
        import re
        from .datasets import remove_custom_synthetic_table

        match = re.match(r"(?i)^DROP\s+TABLE\s+([a-zA-Z0-9_#]+)\s*$", sql)
        if not match:
            raise ABAPException("CX_SQL_EXCEPTION", f"SQL error in DDL statement: Invalid DROP TABLE syntax in '{sql}'.", line)

        table_name = match.group(1).upper().strip()
        existing = get_standard_table(table_name, user_id=self.user_id, project_id=self.project_id)
        if not existing:
            raise ABAPException("CX_SQL_EXCEPTION", f"SQL error in DDL statement: Table '{table_name}' does not exist.", line)

        if self.user_id is None:
            remove_custom_synthetic_table(table_name)
        try:
            from ..abap_models import ABAPDictionaryTable
            query = ABAPDictionaryTable.objects.filter(table_name=table_name, user_id=self.user_id) if self.user_id else ABAPDictionaryTable.objects.filter(table_name=table_name)
            if self.project_id and self.user_id:
                query = query.filter(project__project_id=self.project_id, project__user_id=self.user_id)
            elif self.user_id:
                query = query.filter(project__isnull=True)
            query.delete()
        except Exception as exc:
            if self.user_id is not None:
                raise ABAPException("CX_SQL_EXCEPTION", f"Could not remove table '{table_name}' from this workspace: {exc}", line)

    def _native_execute_update(self, instance: Optional[ABAPInstance], call_args: Dict[str, Any], line: int) -> int:
        import re
        sql = call_args.get("STMT")
        if sql is None:
            sql = call_args.get("PARAM_1")
        if sql is None and call_args:
            sql = next(iter(call_args.values()))
        if not sql:
            return 0

        sql = str(sql).strip()
        if sql.endswith(";") or sql.endswith("."):
            sql = sql[:-1].strip()

        words = sql.split()
        if not words:
            return 0

        cmd = words[0].upper()
        if cmd == "INSERT":
            match = re.match(
                r"(?is)^INSERT\s+INTO\s+([a-zA-Z0-9_#]+)\s*(?:\((.*?)\))?\s+VALUES\s*\((.*)\)\s*$",
                sql,
            )
            if not match:
                raise ABAPException("CX_SQL_EXCEPTION", "Simulator supports INSERT INTO table [(columns)] VALUES (values) for custom dictionary tables.", line)
            table_name = match.group(1).upper()
            if self.user_id is None:
                raise ABAPException("CX_SQL_EXCEPTION", "Database writes require an authenticated user workspace.", line)

            from ..abap_models import ABAPDictionaryTable
            table_query = ABAPDictionaryTable.objects.filter(table_name__iexact=table_name, user_id=self.user_id)
            if self.project_id:
                table_query = table_query.filter(project__project_id=self.project_id, project__user_id=self.user_id)
            else:
                table_query = table_query.filter(project__isnull=True)
            dictionary_table = table_query.first()
            if dictionary_table is None:
                if get_standard_table(table_name, user_id=self.user_id, project_id=self.project_id):
                    raise ABAPException("CX_SQL_EXCEPTION", f"Standard SAP table '{table_name}' is read-only in the simulator.", line)
                raise ABAPException("CX_SQL_EXCEPTION", f"SQL error: Table '{table_name}' does not exist.", line)

            schema = dictionary_table.fields_schema or []
            schema_fields = [str(field.get("field", "")).upper() for field in schema]
            columns_text = match.group(2)
            columns = [part.strip().strip("`").strip('"').upper() for part in columns_text.split(",")] if columns_text else schema_fields
            values_text = match.group(3).strip()
            raw_values = re.findall(r"'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"|[^,]+", values_text)
            if len(raw_values) != len(columns):
                raise ABAPException("CX_SQL_EXCEPTION", f"INSERT into '{table_name}' has {len(columns)} columns but {len(raw_values)} values.", line)
            if any(column not in schema_fields for column in columns):
                unknown = next(column for column in columns if column not in schema_fields)
                raise ABAPException("CX_SQL_EXCEPTION", f"Column '{unknown}' does not exist in table '{table_name}'.", line)

            record = {name: "" for name in schema_fields}
            for name, raw_value in zip(columns, raw_values):
                value = raw_value.strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                    value = value[1:-1].replace("''", "'").replace('""', '"')
                elif value.upper() == "NULL":
                    value = ""
                else:
                    try:
                        value = float(value) if "." in value else int(value)
                    except ValueError:
                        pass
                record[name] = value

            key_fields = [str(field.get("field", "")).upper() for field in schema if field.get("key")]
            current_records = list(dictionary_table.sample_records or [])
            if key_fields and any(all(str(row.get(key, "")) == str(record.get(key, "")) for key in key_fields) for row in current_records):
                raise ABAPException("CX_SQL_EXCEPTION", f"Duplicate key for table '{table_name}'.", line)
            current_records.append(record)
            dictionary_table.sample_records = current_records
            dictionary_table.save(update_fields=["sample_records", "updated_at"])
            self.system_fields["SY-DBCNT"] = 1
            self.system_fields["SY-SUBRC"] = 0
            return 1
        elif cmd in ("UPDATE", "DELETE"):
            raise ABAPException("CX_SQL_EXCEPTION", f"Simulator limitation: SQL {cmd} statements are not implemented; no rows were changed.", line)
        else:
            raise ABAPException("CX_SQL_EXCEPTION", f"Unsupported update command '{cmd}'.", line)

    def _execute_block(self, body: List[ASTNode]) -> int:
        for node in body:
            self.step_count += 1
            if self.step_count > self.max_steps:
                raise ABAPRuntimeError(f"Execution step limit exceeded.", getattr(node, "line", 1))

            sig = self._execute_node(node)
            if sig in (ExecutionSignal.EXIT, ExecutionSignal.CONTINUE):
                return sig
        return ExecutionSignal.NONE

    # ---------------- Expression & Variable Helpers ---------------- #

    def _get_variable_value(self, name: str) -> Any:
        clean = name.upper().strip()
        if clean in self.system_fields:
            return self.system_fields[clean]
        if clean in self.constants:
            return self.constants[clean]

        # Static attribute access: CLS=>ATTR
        if "=>" in clean and "(" not in clean:
            cls_name, attr_name = clean.split("=>", 1)
            cls_name = cls_name.strip()
            attr_name = attr_name.strip()
            self._ensure_class_constructor_run(cls_name)
            target_class = self.classes.get(cls_name)
            if target_class:
                self._check_member_access(target_class, attr_name, "attribute", 1)
                return target_class.class_data.get(attr_name, "")
            return ""

        # Handle object attribute access or method call: lo_obj->attr or lo_obj->method(...)
        if "->" in clean:
            obj_name, attr_or_method = clean.split("->", 1)
            obj_name = obj_name.strip()
            attr_or_method = attr_or_method.strip()

            # Check if this is an inline method call: lo_obj->method(...) or me->method(...)
            if "(" in attr_or_method:
                m_name = attr_or_method.split("(", 1)[0].strip()
                args_str = attr_or_method[attr_or_method.find("(") + 1 : attr_or_method.rfind(")")].strip()
                exporting: Dict[str, List[Token]] = {}
                if args_str:
                    for part in args_str.split(","):
                        part = part.strip()
                        if "=" in part:
                            p_k, p_v = part.split("=", 1)
                            p_v = p_v.strip().strip("'\"")
                            tok_type = TokenType.NUMBER if p_v.isdigit() else TokenType.STRING
                            exporting[p_k.strip().upper()] = [Token(tok_type, p_v, 1, 1)]
                        elif part:
                            tok_type = TokenType.NUMBER if part.isdigit() else TokenType.STRING
                            exporting[f"PARAM_{len(exporting) + 1}"] = [Token(tok_type, part.strip("'\""), 1, 1)]

                temp_ret = f"__MTH_RET_{self.step_count}"
                call_node = CallMethodNode(
                    target_obj=obj_name,
                    method_name=m_name,
                    is_static=False,
                    exporting=exporting,
                    receiving=temp_ret,
                    line=1,
                )
                self._execute_call_method(call_node)
                return self.variables.get(temp_ret, "")

            if obj_name == "ME":
                if self.current_instance:
                    return self.current_instance.attributes.get(attr_or_method, "")
                raise ABAPRuntimeError("Cannot use 'ME' outside of an instance method context.", 1)
            obj = self._get_variable_value(obj_name)
            if obj is None and obj_name in self.variables:
                raise ABAPException("CX_SY_REF_IS_INITIAL", f"Object reference '{obj_name}' is initial (Null Object Reference).", 1)
            if isinstance(obj, ABAPInstance):
                self._check_member_access(obj.abap_class, attr_or_method, "attribute", 1)
                return obj.attributes.get(attr_or_method, "")
            return ""

        if "=>" in clean and "(" in clean:
            cls_name, m_part = clean.split("=>", 1)
            m_name = m_part.split("(", 1)[0].strip()
            temp_ret = f"__MTH_RET_{self.step_count}"
            call_node = CallMethodNode(
                target_obj=cls_name.strip(),
                method_name=m_name,
                is_static=True,
                exporting={},
                receiving=temp_ret,
                line=1,
            )
            self._execute_call_method(call_node)
            return self.variables.get(temp_ret, "")

        if clean.startswith("LINES(") and clean.endswith(")"):
            inner = clean[6:-1].strip()
            tbl = self._get_variable_value(inner)
            if isinstance(tbl, list):
                return len(tbl)
            return 0

        if clean.startswith("STRLEN(") and clean.endswith(")"):
            inner = clean[7:-1].strip()
            val = self._get_variable_value(inner)
            return len(str(val))

        if clean in self.variables:
            return self.variables[clean]

        # If inside a method and clean is an instance attribute
        if self.current_instance and clean in self.current_instance.attributes:
            return self.current_instance.attributes[clean]

        # If inside a method and clean is static class_data
        cls_to_search = []
        if self.current_instance:
            cls_to_search.append(self.current_instance.abap_class)
        if self.current_class and self.current_class in self.classes:
            c = self.classes[self.current_class]
            if c not in cls_to_search:
                cls_to_search.append(c)

        for c_search in cls_to_search:
            curr = c_search
            while curr:
                if clean in curr.class_data:
                    return curr.class_data[clean]
                curr = self.classes.get(curr.superclass) if curr.superclass else None

        if clean in self.field_symbols:
            return self.field_symbols[clean]

        # Handle structure field access: ls_struc-field
        if "-" in clean:
            struc_name, field_name = clean.split("-", 1)
            struc = self._get_variable_value(struc_name)
            if isinstance(struc, dict):
                if field_name in struc:
                    return struc[field_name]
                val = self._resolve_field_value_from_row(field_name, struc)
                if val != "":
                    return val
                return struc.get(field_name, "")
            elif isinstance(struc, list) and struc:
                first = struc[0]
                if isinstance(first, dict):
                    if field_name in first:
                        return first[field_name]
                    val = self._resolve_field_value_from_row(field_name, first)
                    if val != "":
                        return val
                    return first.get(field_name, "")

        return ""

    def _set_variable_value(self, target: str, val: Any, line: int):
        clean = target.upper().strip()
        if clean in self.constants:
            raise ABAPRuntimeError(f"Cannot overwrite constant '{clean}'.", line)

        if clean in self.system_fields:
            self.system_fields[clean] = val
            return

        # Handle static attribute setting: CLS=>ATTR
        if "=>" in clean:
            cls_name, attr_name = clean.split("=>", 1)
            cls_name = cls_name.strip()
            attr_name = attr_name.strip()
            self._ensure_class_constructor_run(cls_name)
            target_class = self.classes.get(cls_name)
            if target_class:
                self._check_member_access(target_class, attr_name, "attribute", line)
                target_class.class_data[attr_name] = val
                return
            raise ABAPRuntimeError(f"Class '{cls_name}' not defined for static attribute assignment.", line)

        # Handle object attribute setting: lo_obj->attr or me->attr
        if "->" in clean:
            obj_name, attr_name = clean.split("->", 1)
            obj_name = obj_name.strip()
            attr_name = attr_name.strip()
            if obj_name == "ME":
                if self.current_instance:
                    self.current_instance.attributes[attr_name] = val
                    return
                raise ABAPRuntimeError("Cannot use 'ME' outside of an instance method.", line)
            obj = self._get_variable_value(obj_name)
            if obj is None and obj_name in self.variables:
                raise ABAPException("CX_SY_REF_IS_INITIAL", f"Object reference '{obj_name}' is initial (Null Object Reference).", line)
            if isinstance(obj, ABAPInstance):
                self._check_member_access(obj.abap_class, attr_name, "attribute", line)
                obj.attributes[attr_name] = val
                return
            raise ABAPRuntimeError(f"Cannot set attribute '{attr_name}' on non-object '{obj_name}'.", line)

        # If inside a method and target matches an instance attribute and not local variable
        if self.current_instance and clean in self.current_instance.attributes and clean not in self.variables:
            self.current_instance.attributes[clean] = val
            return

        # If inside a method and target matches static class_data
        cls_to_search = []
        if self.current_instance:
            cls_to_search.append(self.current_instance.abap_class)
        if self.current_class and self.current_class in self.classes:
            c = self.classes[self.current_class]
            if c not in cls_to_search:
                cls_to_search.append(c)

        for c_search in cls_to_search:
            curr = c_search
            while curr:
                has_attr = any(
                    (getattr(a, "var_name", None) or (a.get("name") if isinstance(a, dict) else "")).upper() == clean
                    for a in curr.attributes_def
                    if (getattr(a, "is_static", False) or (a.get("is_static", False) if isinstance(a, dict) else False))
                )
                if clean in curr.class_data or has_attr:
                    curr.class_data[clean] = val
                    return
                curr = self.classes.get(curr.superclass) if curr.superclass else None

        if "-" in clean:
            struc_name, field_name = clean.split("-", 1)
            if struc_name not in self.variables:
                self.variables[struc_name] = {}
            if not isinstance(self.variables[struc_name], dict):
                self.variables[struc_name] = {}
            self.variables[struc_name][field_name] = val
            return

        self.variables[clean] = val

    def _resolve_token_string(self, tok: Token) -> str:
        if tok.type == TokenType.STRING:
            # Handle template string interpolation: |Hello { var }|
            content = tok.value
            if "{" in content and "}" in content:
                import re
                def repl(m):
                    vname = m.group(1).strip()
                    return str(self._get_variable_value(vname))
                content = re.sub(r"\{\s*([a-zA-Z0-9_\->#]+)\s*\}", repl, content)
            return content

        elif tok.type == TokenType.NUMBER:
            return tok.value

        else:
            val = self._get_variable_value(tok.value)
            if isinstance(val, dict):
                return " ".join(f"{k}:{v}" for k, v in val.items())
            if isinstance(val, list):
                return f"[Internal Table with {len(val)} lines]"
            return str(val)

    def _evaluate_expression(self, tokens: List[Token]) -> Any:
        if not tokens:
            return ""

        # Pre-process tokens to merge object attribute access: a -> b into a->b
        merged: List[Token] = []
        k = 0
        while k < len(tokens):
            if k + 2 < len(tokens) and tokens[k + 1].value in ("->", "=>"):
                merged_val = f"{tokens[k].value}{tokens[k+1].value}{tokens[k+2].value}"
                merged.append(Token(tokens[k].type, merged_val, tokens[k].line, tokens[k].column))
                k += 3
            else:
                merged.append(tokens[k])
                k += 1
        tokens = merged

        # Single token
        if len(tokens) == 1:
            tok = tokens[0]
            if tok.type == TokenType.STRING:
                return self._resolve_token_string(tok)
            if tok.type == TokenType.NUMBER:
                return float(tok.value) if "." in tok.value else int(tok.value)
            return self._get_variable_value(tok.value)

        # String concatenation with &&
        values = []
        is_concat = any(t.value == "&&" for t in tokens)
        if is_concat:
            parts = []
            for t in tokens:
                if t.value != "&&":
                    parts.append(str(self._resolve_token_string(t)))
            return "".join(parts)

        # Simple arithmetic (+, -, *, /)
        expr_str = ""
        for t in tokens:
            if t.type == TokenType.NUMBER:
                expr_str += t.value + " "
            elif t.value in ("+", "-", "*", "/"):
                expr_str += t.value + " "
            else:
                val = self._get_variable_value(t.value)
                expr_str += str(val if isinstance(val, (int, float)) else 0) + " "

        try:
            return eval(expr_str.strip())
        except Exception:
            return self._resolve_token_string(tokens[0])

    def _evaluate_condition(self, tokens: List[Token]) -> bool:
        if not tokens:
            return True

        tok_values = [t.value for t in tokens]
        str_clause = " ".join(tok_values).upper()

        # Handle 'IS INSTANCE OF' / 'IS NOT INSTANCE OF'
        if "IS INSTANCE OF" in str_clause or "IS NOT INSTANCE OF" in str_clause:
            is_not = "IS NOT INSTANCE OF" in str_clause
            key = "IS NOT INSTANCE OF" if is_not else "IS INSTANCE OF"
            left_part, right_part = str_clause.split(key, 1)
            var_name = left_part.strip().split()[-1]
            target_type = right_part.strip().split()[0].upper()
            val = self._get_variable_value(var_name)
            res = False
            if isinstance(val, ABAPInstance):
                curr = val.abap_class
                while curr:
                    if curr.name == target_type or target_type in curr.interfaces:
                        res = True
                        break
                    curr = self.classes.get(curr.superclass) if curr.superclass else None
            return not res if is_not else res

        # Handle 'IS BOUND' / 'IS NOT BOUND'
        if "IS BOUND" in str_clause or "IS NOT BOUND" in str_clause:
            is_not = "IS NOT BOUND" in str_clause
            key = "IS NOT BOUND" if is_not else "IS BOUND"
            left_part = str_clause.split(key, 1)[0]
            var_name = left_part.strip().split()[-1]
            val = self._get_variable_value(var_name)
            res = (val is not None and isinstance(val, ABAPInstance))
            return not res if is_not else res

        # Handle 'IS INITIAL'
        if "IS INITIAL" in str_clause:
            var_name = tok_values[0]
            val = self._get_variable_value(var_name)
            return val in ("", 0, None, [], {})

        if "IS NOT INITIAL" in str_clause:
            var_name = tok_values[0]
            val = self._get_variable_value(var_name)
            return val not in ("", 0, None, [], {})

        # Standard binary comparisons
        for op in ("=", "<>", "<=", ">=", "<", ">", "EQ", "NE", "LT", "GT", "LE", "GE"):
            if op in tok_values:
                op_idx = tok_values.index(op)
                left_tokens = tokens[:op_idx]
                right_tokens = tokens[op_idx + 1 :]
                left_val = self._evaluate_expression(left_tokens)
                right_val = self._evaluate_expression(right_tokens)

                if op in ("=", "EQ"):
                    return str(left_val).upper() == str(right_val).upper()
                elif op in ("<>", "NE"):
                    return str(left_val).upper() != str(right_val).upper()
                elif op in ("<", "LT"):
                    return float(left_val) < float(right_val)
                elif op in (">", "GT"):
                    return float(left_val) > float(right_val)
                elif op in ("<=", "LE"):
                    return float(left_val) <= float(right_val)
                elif op in (">=", "GE"):
                    return float(left_val) >= float(right_val)

        return bool(self._evaluate_expression(tokens))

    def _default_value_for_type(self, abap_type: str) -> Any:
        t = abap_type.upper()
        if t in ("I", "INT", "INT4", "INT2"):
            return 0
        if t in ("F", "DEC", "CURR", "P"):
            return 0.0
        if t in ("C", "CHAR", "STRING", "D", "DATS", "T", "TIMS"):
            return ""
        return ""

    def _cast_value(self, val: Any, abap_type: str) -> Any:
        t = abap_type.upper()
        if t in ("I", "INT", "INT4"):
            try:
                return int(val)
            except (ValueError, TypeError):
                return 0
        if t in ("F", "DEC", "CURR", "P"):
            try:
                return float(val)
            except (ValueError, TypeError):
                return 0.0
        return str(val)
