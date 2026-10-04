"""
SkilTrix SAP ABAP Lab - Comprehensive Automated Test Suite
Validates AST lexer, parser, simulator interpreter, Open SQL queries,
data models, REST APIs, and Mode A SAP ADT connector behaviors.
"""

import json
from django.test import TestCase, Client
import tempfile
from pathlib import Path
from unittest.mock import patch
from sfs.models import AllUsers
from .abap_models import (
    ABAPProject,
    ABAPSourceFile,
    ABAPExercise,
    SAPSystemConnection,
    ABAPDictionaryTable,
)
from .abap_engine import (
    execute_abap_code,
    check_abap_syntax,
    preprocess_abap,
    get_standard_table,
    query_synthetic_table,
)


class ABAPEngineUnitTests(TestCase):
    """Tests the AST Parser, Lexer, and Runtime Evaluator for the ABAP language subset."""

    def test_01_report_and_write_elementary(self):
        code = """
        REPORT z_test_01.
        DATA: lv_msg TYPE string VALUE 'Hello SkilTrix ABAP!'.
        WRITE: / 'Greeting:', lv_msg.
        ULINE.
        """
        res = execute_abap_code(code)
        self.assertTrue(res["status"])
        self.assertIn("Greeting: Hello SkilTrix ABAP!", res["output"])
        self.assertIn("--------------------------------------------------------------------------------", res["output"])

    def test_02_chained_statements_and_arithmetic(self):
        code = """
        REPORT z_test_02.
        DATA: lv_a TYPE i VALUE 25,
              lv_b TYPE i VALUE 75,
              lv_sum TYPE i.
        lv_sum = lv_a + lv_b.
        WRITE: / 'Sum is:', lv_sum.
        """
        res = execute_abap_code(code)
        self.assertTrue(res["status"])
        self.assertIn("Sum is: 100", res["output"])

    def test_03_if_elseif_else_conditions(self):
        code = """
        REPORT z_test_03.
        DATA: lv_score TYPE i VALUE 88,
              lv_grade TYPE string.
        IF lv_score >= 90.
          lv_grade = 'A'.
        ELSEIF lv_score >= 80.
          lv_grade = 'B'.
        ELSE.
          lv_grade = 'C'.
        ENDIF.
        WRITE: / 'Assigned Grade:', lv_grade.
        """
        res = execute_abap_code(code)
        self.assertTrue(res["status"])
        self.assertIn("Assigned Grade: B", res["output"])

    def test_04_case_statement(self):
        code = """
        REPORT z_test_04.
        DATA: lv_country TYPE string VALUE 'DE',
              lv_region TYPE string.
        CASE lv_country.
          WHEN 'US'.
            lv_region = 'North America'.
          WHEN 'DE'.
            lv_region = 'Europe'.
          WHEN OTHERS.
            lv_region = 'Global'.
        ENDCASE.
        WRITE: / 'Region:', lv_region.
        """
        res = execute_abap_code(code)
        self.assertTrue(res["status"])
        self.assertIn("Region: Europe", res["output"])

    def test_05_do_loop_with_sy_index(self):
        code = """
        REPORT z_test_05.
        DATA: lv_count TYPE i VALUE 0.
        DO 4 TIMES.
          lv_count = lv_count + sy-index.
        ENDDO.
        WRITE: / 'Total:', lv_count.
        """
        res = execute_abap_code(code)
        self.assertTrue(res["status"])
        # 1 + 2 + 3 + 4 = 10
        self.assertIn("Total: 10", res["output"])

    def test_06_internal_tables_append_loop_sy_tabix(self):
        code = """
        REPORT z_test_06.
        DATA: lt_codes TYPE STANDARD TABLE OF string,
              lv_code TYPE string.
        APPEND 'SAP' TO lt_codes.
        APPEND 'S4H' TO lt_codes.
        APPEND 'BTP' TO lt_codes.

        LOOP AT lt_codes INTO lv_code.
          WRITE: / sy-tabix, lv_code.
        ENDLOOP.
        """
        res = execute_abap_code(code)
        self.assertTrue(res["status"])
        self.assertIn("1 SAP", res["output"])
        self.assertIn("2 S4H", res["output"])
        self.assertIn("3 BTP", res["output"])

    def test_07_read_table_by_index_and_key(self):
        code = """
        REPORT z_test_07.
        DATA: lt_users TYPE STANDARD TABLE OF string,
              lv_u TYPE string.
        APPEND 'ALICE' TO lt_users.
        APPEND 'BOB' TO lt_users.

        READ TABLE lt_users INTO lv_u INDEX 2.
        WRITE: / 'Found User:', lv_u, 'sy-subrc:', sy-subrc.

        READ TABLE lt_users INTO lv_u INDEX 99.
        WRITE: / 'Not Found sy-subrc:', sy-subrc.
        """
        res = execute_abap_code(code)
        self.assertTrue(res["status"])
        self.assertIn("Found User: BOB sy-subrc: 0", res["output"])
        self.assertIn("Not Found sy-subrc: 4", res["output"])

    def test_08_open_sql_select_kna1_and_vbak(self):
        code = """
        REPORT z_test_08.
        DATA: lt_cust TYPE STANDARD TABLE OF kna1,
              ls_cust TYPE kna1.
        SELECT kunnr, name1, land1 FROM kna1 INTO TABLE @lt_cust UP TO 2 ROWS.
        WRITE: / 'Customers Read:', sy-dbcnt.
        LOOP AT lt_cust INTO ls_cust.
          WRITE: / ls_cust-kunnr, ls_cust-name1.
        ENDLOOP.
        """
        res = execute_abap_code(code)
        self.assertTrue(res["status"])
        self.assertIn("Customers Read: 2", res["output"])
        self.assertIn("0000001000 Walmart Global Procurement", res["output"])

    def test_09_open_sql_where_filter_and_order_by(self):
        code = """
        REPORT z_test_09.
        DATA: lt_orders TYPE STANDARD TABLE OF vbak,
              ls_ord TYPE vbak.
        SELECT vbeln, netwr, waerk FROM vbak INTO TABLE @lt_orders WHERE netwr > 20000 ORDER BY netwr DESCENDING.
        WRITE: / 'Filtered Orders:', sy-dbcnt.
        LOOP AT lt_orders INTO ls_ord.
          WRITE: / ls_ord-vbeln, ls_ord-netwr.
        ENDLOOP.
        """
        res = execute_abap_code(code)
        self.assertTrue(res["status"])
        self.assertIn("Filtered Orders: 3", res["output"])
        self.assertIn("0090000004 150000.0", res["output"])
        self.assertIn("0090000003 92000.0", res["output"])
        self.assertIn("0090000005 31400.0", res["output"])

    def test_10_syntax_check_diagnostics(self):
        good_code = "REPORT z_ok.\nWRITE: / 'Clean code'.\n"
        res = check_abap_syntax(good_code)
        self.assertTrue(res["valid"])
        self.assertEqual(len(res["diagnostics"]), 0)

    def test_10b_reports_missing_period_undefined_name_and_block_end(self):
        res = check_abap_syntax("REPORT z_bad.\nDATA lv_value TYPE i.\nWRITE missing_name\nIF lv_value = 1.\n")
        self.assertFalse(res["valid"])
        self.assertTrue(any(d["code"] == "ABAP_MISSING_PERIOD" and d["line"] == 3 for d in res["diagnostics"]))
        self.assertTrue(any(d["code"] == "ABAP_UNDEFINED_NAME" and d["line"] == 3 and d["column"] == 7 for d in res["diagnostics"]))
        self.assertTrue(any("Missing ENDIF" in d["message"] for d in res["diagnostics"]))

    def test_10c_syntax_failure_does_not_execute_program(self):
        result = execute_abap_code("REPORT z_bad.\nWRITE 'must not run'")
        self.assertFalse(result["status"])
        self.assertIn("Compilation failed", result["output"])
        self.assertNotIn("must not run", result["output"])

    def test_10d_open_sql_like_filters_rows(self):
        code = """
        DATA: lt_customer TYPE STANDARD TABLE OF kna1,
             ls_customer TYPE kna1.
        SELECT kunnr, name1 FROM kna1 INTO TABLE @lt_customer WHERE name1 LIKE 'Apple%'.
        WRITE: / sy-dbcnt.
        LOOP AT lt_customer INTO ls_customer.
          WRITE: / ls_customer-name1.
        ENDLOOP.
        """
        result = execute_abap_code(code)
        self.assertTrue(result["status"])
        self.assertIn("1", result["output"])
        self.assertIn("Apple Operations Europe", result["output"])
        self.assertNotIn("Walmart Global Procurement", result["output"])

    def test_10e_missing_period_before_assignment_and_undefined_names(self):
        result = check_abap_syntax(
            "REPORT z_period.\nDATA lv_count TYPE i.\nlv_count = 1\nlv_count = missing_count + 1.\nIF another_missing = 2.\nENDIF."
        )
        self.assertFalse(result["valid"])
        self.assertTrue(any(d["code"] == "ABAP_MISSING_PERIOD" and d["line"] == 3 for d in result["diagnostics"]))
        unresolved = [d for d in result["diagnostics"] if d["code"] == "ABAP_UNDEFINED_NAME"]
        self.assertEqual({d["message"] for d in unresolved}, {
            "'missing_count' is not declared in this program.",
            "'another_missing' is not declared in this program.",
        })

    def test_19_abap_oo_classes_and_methods(self):
        code = """
        REPORT z_oo_demo.

        CLASS lcl_vehicle DEFINITION.
          PUBLIC SECTION.
            DATA: mv_model TYPE string,
                  mv_speed TYPE i.
            METHODS:
              constructor IMPORTING iv_model TYPE string,
              accelerate IMPORTING iv_delta TYPE i,
              get_info RETURNING VALUE(rv_info) TYPE string.
        ENDCLASS.

        CLASS lcl_vehicle IMPLEMENTATION.
          METHOD constructor.
            me->mv_model = iv_model.
            me->mv_speed = 0.
          ENDMETHOD.

          METHOD accelerate.
            mv_speed = mv_speed + iv_delta.
          ENDMETHOD.

          METHOD get_info.
            rv_info = |Model: { mv_model } - Speed: { mv_speed } km/h|.
          ENDMETHOD.
        ENDCLASS.

        START-OF-SELECTION.
          DATA: lo_car TYPE REF TO lcl_vehicle.
          CREATE OBJECT lo_car EXPORTING iv_model = 'Porsche 911'.
          lo_car->accelerate( iv_delta = 85 ).
          WRITE: / lo_car->get_info( ).
          WRITE: / 'Direct Speed Access:', lo_car->mv_speed.

          " Test second instance
          DATA(lo_bmw) = NEW lcl_vehicle( ).
          lo_bmw->mv_model = 'BMW M3'.
          lo_bmw->accelerate( 120 ).
          WRITE: / lo_bmw->get_info( ).
        """
        res = execute_abap_code(code)
        self.assertTrue(res["status"], f"Execution failed: {res.get('output')} Diagnostics: {res.get('diagnostics')}")
        self.assertIn("Model: Porsche 911 - Speed: 85 km/h", res["output"])
        self.assertIn("Direct Speed Access: 85", res["output"])
        self.assertIn("Model: BMW M3 - Speed: 120 km/h", res["output"])

    def test_20_try_catch_success_path(self):
        """E.1: TRY completes successfully without entering CATCH."""
        code = """
        REPORT z_try_success.
        DATA: lv_status TYPE string VALUE 'INIT',
              lx_err TYPE REF TO cx_root.
        TRY.
            lv_status = 'TRY_COMPLETED'.
          CATCH cx_root INTO lx_err.
            lv_status = 'CATCH_ENTERED'.
        ENDTRY.
        WRITE: / 'Final Status:', lv_status.
        """
        res = execute_abap_code(code)
        self.assertTrue(res["status"])
        self.assertIn("Final Status: TRY_COMPLETED", res["output"])
        self.assertNotIn("CATCH_ENTERED", res["output"])

    def test_21_try_catch_sql_exception_and_get_text(self):
        """E.2 & E.3: Simulated SQL exception enters matching CATCH, GET_TEXT() returns message."""
        code = """
        REPORT z_try_catch_sql.
        DATA: lo_sql TYPE REF TO cl_sql_statement,
              lx_sql TYPE REF TO cx_sql_exception.
        TRY.
            CREATE OBJECT lo_sql.
            lo_sql->execute_ddl( 'ALTER TABLE INVALID_SYNTAX' ).
            WRITE: / 'Should not execute'.
          CATCH cx_sql_exception INTO lx_sql.
            WRITE: / 'Caught:', lx_sql->get_text( ).
        ENDTRY.
        """
        res = execute_abap_code(code)
        self.assertTrue(res["status"])
        self.assertIn("Caught: SQL error in DDL statement", res["output"])
        self.assertNotIn("Should not execute", res["output"])

    def test_22_mandatory_acceptance_test_cl_sql_ddl(self):
        """
        MANDATORY ACCEPTANCE TEST:
        Valid CREATE TABLE creates table in schema and writes success.
        Re-executing raises CX_SQL_EXCEPTION, enters CATCH, and writes get_text().
        """
        code = """
        DATA lo_sql TYPE REF TO cl_sql_statement.
        DATA lx_sql TYPE REF TO cx_sql_exception.

        TRY.
            CREATE OBJECT lo_sql.
            lo_sql->execute_ddl(
              `CREATE TABLE ZSTUDENT_DEMO (` &&
              `STUDENT_ID NVARCHAR(10) PRIMARY KEY, ` &&
              `NAME NVARCHAR(40), ` &&
              `AGE INTEGER)` ).
            WRITE: / 'Table created successfully'.
          CATCH cx_sql_exception INTO lx_sql.
            WRITE: / lx_sql->get_text( ).
        ENDTRY.
        """
        # Run 1: First creation succeeds (E.5)
        res1 = execute_abap_code(code)
        self.assertTrue(res1["status"])
        self.assertIn("Table created successfully", res1["output"])

        # Run 2: Duplicate creation enters CATCH with clear error (E.6 & E.7)
        res2 = execute_abap_code(code)
        self.assertTrue(res2["status"])
        self.assertIn("Table 'ZSTUDENT_DEMO' already exists in database schema.", res2["output"])
        self.assertNotIn("Table created successfully", res2["output"])

    def test_23_invalid_ddl_statement_raises_exception(self):
        """E.4 & E.7: Invalid CREATE TABLE raises simulated exception and does not print success."""
        code = """
        DATA lo_sql TYPE REF TO cl_sql_statement.
        DATA lx_sql TYPE REF TO cx_sql_exception.

        TRY.
            CREATE OBJECT lo_sql.
            lo_sql->execute_ddl( `CREATE TABLE` ).
            WRITE: / 'Table created successfully'.
          CATCH cx_sql_exception INTO lx_sql.
            WRITE: / 'Caught error:', lx_sql->get_text( ).
        ENDTRY.
        """
        res = execute_abap_code(code)
        self.assertTrue(res["status"])
        self.assertIn("Caught error:", res["output"])
        self.assertNotIn("Table created successfully", res["output"])

    def test_24_inline_catch_declaration(self):
        """B: CATCH cx_sql_exception INTO DATA(lx_sql) inline declaration."""
        code = """
        DATA lo_sql TYPE REF TO cl_sql_statement.
        TRY.
            CREATE OBJECT lo_sql.
            lo_sql->execute_ddl( 'UNSUPPORTED COMMAND FOO' ).
            WRITE: / 'SHOULD_FAIL'.
          CATCH cx_sql_exception INTO DATA(lx_err).
            WRITE: / 'INLINE_CAUGHT:', lx_err->get_text( ).
        ENDTRY.
        """
        res = execute_abap_code(code)
        self.assertTrue(res["status"])
        self.assertIn("INLINE_CAUGHT:", res["output"])
        self.assertNotIn("SHOULD_FAIL", res["output"])

    def test_25_created_table_accessible_via_open_sql_and_dictionary(self):
        """E.5: Newly created table is immediately queryable via Open SQL and registered in dictionary."""
        ddl_code = """
        DATA lo_sql TYPE REF TO cl_sql_statement.
        TRY.
            CREATE OBJECT lo_sql.
            lo_sql->execute_ddl(
              `CREATE TABLE ZCOURSES_DEMO (` &&
              `COURSE_ID NVARCHAR(10) PRIMARY KEY, ` &&
              `TITLE NVARCHAR(50), ` &&
              `PRICE INTEGER)` ).
            WRITE: / 'Table ZCOURSES_DEMO created'.
          CATCH cx_sql_exception INTO DATA(lx_err).
            WRITE: / lx_err->get_text( ).
        ENDTRY.
        """
        res_ddl = execute_abap_code(ddl_code)
        self.assertTrue(res_ddl["status"])
        self.assertIn("Table ZCOURSES_DEMO created", res_ddl["output"])

        # Verify table exists in synthetic tables or database dictionary
        from skiltrix.abap_engine.datasets import get_standard_table
        tbl_info = get_standard_table("ZCOURSES_DEMO")
        self.assertIsNotNone(tbl_info)
        col_names = [c["field"] for c in tbl_info.get("columns", [])]
        self.assertIn("COURSE_ID", col_names)
        self.assertIn("TITLE", col_names)
        self.assertIn("PRICE", col_names)



class ABAPApiEndpointTests(TestCase):
    """Tests the DRF API endpoints under /apps/skiltrix/api/abap/."""

    def setUp(self):
        self.temp_workspace_root = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_workspace_root.cleanup)
        abap_patch = patch("skiltrix.abap_views.ABAP_WORKSPACE_BASE_DIR", Path(self.temp_workspace_root.name))
        abap_patch.start()
        self.addCleanup(abap_patch.stop)
        self.client = Client()
        self.user, _ = AllUsers.objects.get_or_create(
            user_id="abap_test_user_01",
            defaults={
                "username": "abap_dev",
                "name": "ABAP",
                "lastname": "Developer",
                "email": "abap@example.com",
                "user_type": "admin",
                "platform": "web",
                "platform_name": "SkilTrix",
                "type": "user",
                "ip": "127.0.0.1",
            },
        )
        if getattr(self.user, "user_type", "") != "admin":
            self.user.user_type = "admin"
            self.user.save()
        self.client.force_login(self.user, backend="django.contrib.auth.backends.ModelBackend")

    def test_11_health_check(self):
        response = self.client.get("/apps/skiltrix/api/abap/health/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("simulator", data["modes"])
        self.assertIn("sap_connected", data["modes"])

    def test_12_execute_simulator_api(self):
        payload = {
            "code": "REPORT z_api_test.\nWRITE: / 'API Execution Succeeded'.\n",
            "execution_mode": "simulator",
        }
        response = self.client.post(
            "/apps/skiltrix/api/abap/execute/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["status"])
        self.assertIn("API Execution Succeeded", data["output"])
        self.assertEqual(data["execution_mode"], "simulator")

    def test_13_syntax_check_api(self):
        payload = {"code": "REPORT z_syntax.\nWRITE: / 'OK'.\n"}
        response = self.client.post(
            "/apps/skiltrix/api/abap/syntax-check/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["valid"])

    def test_custom_table_insert_persists_only_in_selected_user_project(self):
        project = ABAPProject.objects.create(
            project_id="abap_insert_scope_test", user=self.user,
            title="Insert Test", slug="insert-test",
        )
        table = ABAPDictionaryTable.objects.create(
            table_id="tabl_insert_scope_test", project=project, user=self.user,
            table_name="ZINSERT_TEST", description="Insert test table",
            fields_schema=[
                {"field": "MANDT", "key": True, "type": "CLNT"},
                {"field": "ITEM_ID", "key": True, "type": "CHAR"},
                {"field": "ITEM_NAME", "key": False, "type": "CHAR"},
            ], sample_records=[],
        )
        from .abap_engine.interpreter import ABAPInterpreter
        interpreter = ABAPInterpreter(user_id=self.user.user_id, project_id=project.project_id)
        changed = interpreter._native_execute_update(
            None,
            {"STMT": "INSERT INTO ZINSERT_TEST (MANDT, ITEM_ID, ITEM_NAME) VALUES ('100', '1', 'First Item')"},
            1,
        )
        table.refresh_from_db()
        self.assertEqual(changed, 1)
        self.assertEqual(table.sample_records, [{"MANDT": "100", "ITEM_ID": "1", "ITEM_NAME": "First Item"}])

    def test_14_dictionary_preview_api(self):
        response = self.client.get("/apps/skiltrix/api/abap/dictionary/preview/?table=KNA1")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["table_name"], "KNA1")
        self.assertGreater(data["row_count"], 0)
        self.assertTrue(any(c["name"] == "KUNNR" for c in data["columns"]))

    def test_15_project_crud_and_file_operations(self):
        # Create Project
        proj_payload = {
            "title": "Z_DEMO_PROJECT",
            "package_name": "$TMP",
            "execution_mode": "simulator",
            "description": "Integration test project",
            "user_id": self.user.user_id,
        }
        create_resp = self.client.post(
            "/apps/skiltrix/api/abap/projects/",
            data=json.dumps(proj_payload),
            content_type="application/json",
        )
        self.assertEqual(create_resp.status_code, 201)
        proj_data = create_resp.json()
        project_id = proj_data["project_id"]
        self.assertTrue(project_id.startswith("abap_"))

        # List files in project
        files_resp = self.client.get(f"/apps/skiltrix/api/abap/projects/{project_id}/files/")
        self.assertEqual(files_resp.status_code, 200)
        files = files_resp.json()
        self.assertGreater(len(files), 0)
        first_file_name = files[0]["name"]

        # Save file content
        new_content = "REPORT z_demo.\nWRITE: / 'Updated Content'.\n"
        save_resp = self.client.post(
            f"/apps/skiltrix/api/abap/projects/{project_id}/files/save/",
            data=json.dumps({"name": first_file_name, "content": new_content}),
            content_type="application/json",
        )
        self.assertEqual(save_resp.status_code, 200)
        self.assertTrue(save_resp.json()["status"])

        # Retrieve updated content
        content_resp = self.client.get(
            f"/apps/skiltrix/api/abap/projects/{project_id}/files/content/?name={first_file_name}"
        )
        self.assertEqual(content_resp.status_code, 200)
        self.assertEqual(content_resp.json()["content"], new_content)

        # Export Project ZIP
        zip_resp = self.client.get(f"/apps/skiltrix/api/abap/projects/{project_id}/export/")
        self.assertEqual(zip_resp.status_code, 200)
        self.assertEqual(zip_resp["Content-Type"], "application/zip")

    def test_16_sap_system_connection_and_security(self):
        conn_payload = {
            "system_name": "Test S4H Corp",
            "system_id": "S4H",
            "client": "100",
            "host": "127.0.0.1",
            "port": 8443,
            "username": "SAP_DEV",
            "password": "SuperSecretPassword123!",
            "user_id": self.user.user_id,
        }
        create_resp = self.client.post(
            "/apps/skiltrix/api/abap/connections/",
            data=json.dumps(conn_payload),
            content_type="application/json",
        )
        self.assertEqual(create_resp.status_code, 201)
        data = create_resp.json()

        # Security check: Password must NEVER be leaked in API response
        self.assertNotIn("password", data)
        self.assertNotIn("encrypted_password", data)
        self.assertTrue(data["has_credentials"])
        conn_id = data["connection_id"]

        # Test Connection ping
        test_resp = self.client.post(f"/apps/skiltrix/api/abap/connections/{conn_id}/test_connection/")
        self.assertEqual(test_resp.status_code, 200)
        test_data = test_resp.json()
        self.assertIn("status", test_data)
        self.assertIn("message", test_data)

    def test_17_exercise_submission_and_evaluation(self):
        # Create an exercise with a sample and hidden test case
        from .abap_models import ABAPExercise, ABAPTestCase
        import uuid
        ex = ABAPExercise.objects.create(
            exercise_id=f"ex_{uuid.uuid4().hex[:12]}",
            title="Calculate Total Tax",
            slug="calculate-total-tax",
            category="Beginner",
            difficulty="Easy",
            topic="Arithmetic",
            problem_statement="Calculate 18% VAT on 1000",
            starter_code="REPORT z_tax.\nDATA: lv_amount TYPE i VALUE 1000.\n",
            points=20,
        )
        ABAPTestCase.objects.create(
            test_case_id=f"tc_{uuid.uuid4().hex[:12]}",
            exercise=ex,
            expected_output="Tax Amount: 180",
            is_sample=True,
            is_hidden=False,
            order=1,
        )

        # Submit correct solution
        sol_code = "REPORT z_tax.\nDATA: lv_val TYPE i VALUE 1000, lv_tax TYPE i.\nlv_tax = lv_val * 18 / 100.\nWRITE: / 'Tax Amount:', lv_tax.\n"
        sub_resp = self.client.post(
            f"/apps/skiltrix/api/abap/exercises/{ex.exercise_id}/submit/",
            data=json.dumps({"code": sol_code, "user_id": self.user.user_id}),
            content_type="application/json",
        )
        self.assertEqual(sub_resp.status_code, 200)
        sub_data = sub_resp.json()
        self.assertEqual(sub_data["verdict"], "Accepted")
        self.assertEqual(sub_data["passed_tests"], 1)
        self.assertEqual(sub_data["points_earned"], 20)

    def test_18_custom_transparent_table_lifecycle_and_open_sql(self):
        # 1. Create a custom transparent table in the database
        tbl_payload = {
            "table_name": "ZEMPLOYEES",
            "description": "Custom Employee Master Table",
            "delivery_class": "A",
            "fields_schema": [
                {"field": "MANDT", "key": True, "type": "CLNT", "length": 3, "description": "Client"},
                {"field": "EMP_ID", "key": True, "type": "CHAR", "length": 10, "description": "Employee ID"},
                {"field": "NAME", "key": False, "type": "CHAR", "length": 40, "description": "Full Name"},
                {"field": "SALARY", "key": False, "type": "CURR", "length": 15, "description": "Monthly Salary"},
            ],
            "sample_records": [
                {"MANDT": "100", "EMP_ID": "EMP001", "NAME": "Rajesh Sharma", "SALARY": 85000.0},
            ],
        }
        create_resp = self.client.post(
            "/apps/skiltrix/api/abap/dictionary/",
            data=json.dumps(tbl_payload),
            content_type="application/json",
        )
        self.assertEqual(create_resp.status_code, 201)
        tbl_data = create_resp.json()
        table_id = tbl_data["table_id"]

        # 2. Insert another record via add_record action
        add_resp = self.client.post(
            f"/apps/skiltrix/api/abap/dictionary/{table_id}/add_record/",
            data=json.dumps({"record": {"MANDT": "100", "EMP_ID": "EMP002", "NAME": "Priya Nair", "SALARY": 92000.0}}),
            content_type="application/json",
        )
        self.assertEqual(add_resp.status_code, 200)
        self.assertEqual(add_resp.json()["row_count"], 2)

        # 3. Preview table data via SE16N endpoint
        prev_resp = self.client.get("/apps/skiltrix/api/abap/dictionary/preview/?table=ZEMPLOYEES")
        self.assertEqual(prev_resp.status_code, 200)
        prev_data = prev_resp.json()
        self.assertEqual(prev_data["row_count"], 2)
        self.assertEqual(prev_data["rows"][0]["NAME"], "Rajesh Sharma")
        self.assertEqual(prev_data["rows"][1]["NAME"], "Priya Nair")

        # 4. Execute a dynamic ABAP program querying this custom table using Open SQL!
        code = """
        REPORT z_emp_report.
        DATA: lt_emp TYPE STANDARD TABLE OF zemployees,
              ls_emp TYPE zemployees.

        SELECT emp_id, name, salary FROM zemployees INTO TABLE @lt_emp ORDER BY salary DESCENDING.
        WRITE: / 'Employees Retrieved:', sy-dbcnt.
        ULINE.
        LOOP AT lt_emp INTO ls_emp.
          WRITE: / ls_emp-emp_id, ls_emp-name, ls_emp-salary.
        ENDLOOP.
        """
        exec_resp = self.client.post(
            "/apps/skiltrix/api/abap/execute/",
            data=json.dumps({"code": code, "execution_mode": "simulator"}),
            content_type="application/json",
        )
        self.assertEqual(exec_resp.status_code, 200)
        exec_data = exec_resp.json()
        self.assertTrue(exec_data["status"])
        self.assertIn("Employees Retrieved: 2", exec_data["output"])
        self.assertIn("EMP002 Priya Nair 92000.0", exec_data["output"])
        self.assertIn("EMP001 Rajesh Sharma 85000.0", exec_data["output"])

    def test_26_file_explorer_operations(self):
        """Validates complete VS Code explorer file & folder operations in backend."""
        # 1. Create a project
        proj_resp = self.client.post(
            "/apps/skiltrix/api/abap/projects/",
            data=json.dumps({"title": "Z_EXPLORER_TEST", "user_id": self.user.user_id}),
            content_type="application/json",
        )
        self.assertEqual(proj_resp.status_code, 201)
        project_id = proj_resp.json()["project_id"]

        # 2. Create folder
        fld_resp = self.client.post(
            f"/apps/skiltrix/api/abap/projects/{project_id}/files/folder/",
            data=json.dumps({"folder_path": "src/reports"}),
            content_type="application/json",
        )
        self.assertEqual(fld_resp.status_code, 201)
        self.assertTrue(fld_resp.json()["status"])

        # 3. Create nested file inside folder
        cf_resp = self.client.post(
            f"/apps/skiltrix/api/abap/projects/{project_id}/files/create/",
            data=json.dumps({"name": "src/reports/z_test.prog.abap", "content": "WRITE: / 'Test'."}),
            content_type="application/json",
        )
        self.assertEqual(cf_resp.status_code, 201)
        self.assertEqual(cf_resp.json()["name"], "src/reports/z_test.prog.abap")

        # 4. Duplicate file
        dup_resp = self.client.post(
            f"/apps/skiltrix/api/abap/projects/{project_id}/files/duplicate/",
            data=json.dumps({"source_path": "src/reports/z_test.prog.abap"}),
            content_type="application/json",
        )
        self.assertEqual(dup_resp.status_code, 201)
        dup_name = dup_resp.json()["name"]
        self.assertIn("_copy", dup_name)

        # 5. Rename file
        ren_resp = self.client.post(
            f"/apps/skiltrix/api/abap/projects/{project_id}/files/rename/",
            data=json.dumps({"old_path": dup_name, "new_path": "src/reports/z_renamed.prog.abap"}),
            content_type="application/json",
        )
        self.assertEqual(ren_resp.status_code, 200)

        # 6. Move file to another directory or root
        move_resp = self.client.post(
            f"/apps/skiltrix/api/abap/projects/{project_id}/files/move/",
            data=json.dumps({"source_path": "src/reports/z_renamed.prog.abap", "target_folder": ""}),
            content_type="application/json",
        )
        self.assertEqual(move_resp.status_code, 200)

        # 7. Check folder cannot move into itself
        bad_move = self.client.post(
            f"/apps/skiltrix/api/abap/projects/{project_id}/files/move/",
            data=json.dumps({"source_path": "src", "target_folder": "src/reports"}),
            content_type="application/json",
        )
        self.assertEqual(bad_move.status_code, 400)

        # 8. Delete folder recursively
        del_resp = self.client.delete(
            f"/apps/skiltrix/api/abap/projects/{project_id}/files/delete/?path=src"
        )
        self.assertEqual(del_resp.status_code, 200)
        self.assertTrue(del_resp.json()["status"])

    def test_open_sql_insert_commit_and_dictionary_ops(self):
        tbl = ABAPDictionaryTable.objects.create(
            table_id="tabl_test_zemp",
            user=self.user,
            table_name="ZEMPDETAILS",
            description="Employee Details",
            fields_schema=[
                {"field": "MANDT", "type": "CLNT", "length": 3, "key": True},
                {"field": "EMPID", "type": "INT4", "length": 10, "key": True},
                {"field": "NAME", "type": "CHAR", "length": 30, "key": False},
                {"field": "CITY", "type": "CHAR", "length": 30, "key": False},
                {"field": "EMPSAL", "type": "CURR", "length": 15, "key": False},
            ],
            sample_records=[],
        )

        code = """REPORT zempdetails.
DATA : WA TYPE ZEMPDETAILS.
DATA : IT TYPE TABLE OF WA.

WA-EMPID = 100.
WA-NAME = 'JHON'.
WA-CITY = 'ONGOLE'.
WA-EMPSAL = 5000.
APPEND WA TO IT.
INSERT INTO ZEMPDETAILS FROM TABLE IT.

IF SY-SUBRC = 0.
COMMIT WORK.
WRITE : 'INSERTED SUCCESSFULLY'.
ELSE.
WRITE : ' ERROR IN INSERTIN'.
ENDIF.
"""
        result = execute_abap_code(code, user_id=self.user.user_id)
        self.assertTrue(result["status"])
        self.assertIn("INSERTED SUCCESSFULLY", result["output"])

        tbl.refresh_from_db()
        self.assertEqual(len(tbl.sample_records), 1)
        self.assertEqual(tbl.sample_records[0]["NAME"], "JHON")
        self.assertEqual(tbl.sample_records[0]["CITY"], "ONGOLE")

        # Test SELECT from table
        sel_code = """REPORT zemp_sel.
DATA: it_res TYPE STANDARD TABLE OF zempdetails,
      wa_res TYPE zempdetails.
SELECT * FROM zempdetails INTO TABLE it_res.
LOOP AT it_res INTO wa_res.
  WRITE: / wa_res-empid, wa_res-name.
ENDLOOP.
"""
        sel_res = execute_abap_code(sel_code, user_id=self.user.user_id)
        self.assertTrue(sel_res["status"])
        self.assertIn("100 JHON", sel_res["output"])

        # Test DELETE
        del_code = """REPORT zemp_del.
DELETE FROM zempdetails WHERE empid = 100.
IF sy-subrc = 0.
  WRITE: / 'DELETED OK'.
ENDIF.
"""
        del_res = execute_abap_code(del_code, user_id=self.user.user_id)
        self.assertTrue(del_res["status"])
        self.assertIn("DELETED OK", del_res["output"])
        tbl.refresh_from_db()
        self.assertEqual(len(tbl.sample_records), 0)

    def test_dictionary_create_no_duplicate_tables(self):
        payload = {
            "table_name": "ZCUSTOM_DEMO",
            "description": "First Version",
            "fields_schema": [{"field": "CUST_ID", "type": "CHAR", "length": 10, "key": True}],
            "sample_records": [],
        }
        res1 = self.client.post("/apps/skiltrix/api/abap/dictionary/", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(res1.status_code, 201)

        payload["description"] = "Updated Version"
        res2 = self.client.post("/apps/skiltrix/api/abap/dictionary/", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(res2.status_code, 400)
        self.assertIn("Database table already exists", res2.json().get("detail", ""))

        # Check total count in DB remains 1
        self.assertEqual(ABAPDictionaryTable.objects.filter(table_name="ZCUSTOM_DEMO", user=self.user).count(), 1)

    def test_regression_insert_nonexistent_table_truthful_failure(self):
        """Inserting into a nonexistent table must fail with SY-SUBRC=4 and not enter success branch."""
        # Ensure ZNONEXISTENT does not exist in DB
        ABAPDictionaryTable.objects.filter(table_name="ZNONEXISTENT").delete()

        code = """REPORT ztest_nonexistent.
DATA: wa TYPE znonexistent.
DATA: it TYPE TABLE OF wa.

wa-empid = 100.
wa-name = 'JHON'.
APPEND wa TO it.

INSERT znonexistent FROM TABLE it.

IF sy-subrc = 0.
  COMMIT WORK.
  WRITE: 'INSERTED SUCCESSFULLY'.
ELSE.
  WRITE: 'ERROR IN INSERTING'.
ENDIF.
"""
        result = execute_abap_code(code, user_id=self.user.user_id)
        self.assertTrue(result["status"])
        self.assertIn("ERROR IN INSERTING", result["output"])
        self.assertNotIn("INSERTED SUCCESSFULLY", result["output"])
        self.assertEqual(result["system_fields"].get("SY-SUBRC"), 4)
        self.assertEqual(result["system_fields"].get("SY-DBCNT"), 0)
        self.assertTrue(any(d.get("code") == "CX_SY_OPEN_SQL_DB" and "Database table or view 'ZNONEXISTENT' not found" in d.get("message", "") for d in result.get("diagnostics", [])))
        # Verify table was NOT silently created in database
        self.assertFalse(ABAPDictionaryTable.objects.filter(table_name="ZNONEXISTENT").exists())

    def test_regression_insert_existing_table_and_database_preview(self):
        """Inserting one valid row into an existing table succeeds and reflects in Database Preview."""
        tbl = ABAPDictionaryTable.objects.create(
            table_id="tabl_test_preview",
            user=self.user,
            table_name="ZPREVIEW_TAB",
            description="Preview Test Table",
            fields_schema=[
                {"field": "MANDT", "type": "CLNT", "length": 3, "key": True},
                {"field": "ITEM_ID", "type": "CHAR", "length": 10, "key": True},
                {"field": "LABEL", "type": "CHAR", "length": 40, "key": False},
            ],
            sample_records=[],
        )

        code = """REPORT ztest_preview.
DATA: wa TYPE zpreview_tab.
DATA: it TYPE TABLE OF wa.

wa-item_id = 'ITEM001'.
wa-label = 'Widget A'.
APPEND wa TO it.

INSERT zpreview_tab FROM TABLE it.
IF sy-subrc = 0.
  COMMIT WORK.
  WRITE: 'INSERTED'.
ENDIF.
"""
        result = execute_abap_code(code, user_id=self.user.user_id)
        self.assertTrue(result["status"])
        self.assertIn("INSERTED", result["output"])
        self.assertEqual(result["system_fields"].get("SY-SUBRC"), 0)
        self.assertEqual(result["system_fields"].get("SY-DBCNT"), 1)

        # Verify preview endpoint reads the exact same table data
        preview_resp = self.client.get("/apps/skiltrix/api/abap/dictionary/preview/?table=ZPREVIEW_TAB")
        self.assertEqual(preview_resp.status_code, 200)
        pdata = preview_resp.json()
        self.assertEqual(pdata["row_count"], 1)
        self.assertEqual(pdata["rows"][0]["ITEM_ID"], "ITEM001")
        self.assertEqual(pdata["rows"][0]["LABEL"], "Widget A")

    def test_regression_insert_duplicate_primary_key_fails(self):
        """Inserting duplicate primary key must set SY-SUBRC=4 and not insert extra rows."""
        tbl = ABAPDictionaryTable.objects.create(
            table_id="tabl_test_dup",
            user=self.user,
            table_name="ZDUP_TAB",
            description="Duplicate Check Table",
            fields_schema=[
                {"field": "MANDT", "type": "CLNT", "length": 3, "key": True},
                {"field": "CODE", "type": "CHAR", "length": 5, "key": True},
                {"field": "VAL", "type": "CHAR", "length": 20, "key": False},
            ],
            sample_records=[{"MANDT": "100", "CODE": "A01", "VAL": "Initial"}],
        )

        code = """REPORT ztest_dup.
DATA: wa TYPE zdup_tab.
wa-code = 'A01'.
wa-val = 'Duplicate'.

INSERT zdup_tab FROM wa.
IF sy-subrc = 0.
  WRITE: 'SUCCESS'.
ELSE.
  WRITE: 'DUPLICATE REJECTED'.
ENDIF.
"""
        result = execute_abap_code(code, user_id=self.user.user_id)
        self.assertTrue(result["status"])
        self.assertIn("DUPLICATE REJECTED", result["output"])
        self.assertEqual(result["system_fields"].get("SY-SUBRC"), 4)
        self.assertEqual(result["system_fields"].get("SY-DBCNT"), 0)

        tbl.refresh_from_db()
        self.assertEqual(len(tbl.sample_records), 1)
        self.assertEqual(tbl.sample_records[0]["VAL"], "Initial")

    def test_regression_insert_empty_itab_and_batch_rows(self):
        """Inserting empty internal table sets SY-SUBRC=0, SY-DBCNT=0; batch insert inserts multiple rows."""
        tbl = ABAPDictionaryTable.objects.create(
            table_id="tabl_test_batch",
            user=self.user,
            table_name="ZBATCH_TAB",
            description="Batch Test Table",
            fields_schema=[
                {"field": "MANDT", "type": "CLNT", "length": 3, "key": True},
                {"field": "SEQ", "type": "INT4", "length": 5, "key": True},
                {"field": "TEXT", "type": "CHAR", "length": 20, "key": False},
            ],
            sample_records=[],
        )

        # 1. Empty itab
        code_empty = """REPORT ztest_batch_empty.
DATA: it_empty TYPE TABLE OF zbatch_tab.
INSERT zbatch_tab FROM TABLE it_empty.
WRITE: / 'SUBRC:', sy-subrc, 'DBCNT:', sy-dbcnt.
"""
        res_empty = execute_abap_code(code_empty, user_id=self.user.user_id)
        self.assertTrue(res_empty["status"])
        self.assertEqual(res_empty["system_fields"].get("SY-SUBRC"), 0)
        self.assertEqual(res_empty["system_fields"].get("SY-DBCNT"), 0)
        self.assertIn("SUBRC: 0 DBCNT: 0", res_empty["output"])

        # 2. Batch of 2 rows
        code_batch = """REPORT ztest_batch_two.
DATA: wa TYPE zbatch_tab.
DATA: it TYPE TABLE OF zbatch_tab.
wa-seq = 1. wa-text = 'One'. APPEND wa TO it.
wa-seq = 2. wa-text = 'Two'. APPEND wa TO it.
INSERT zbatch_tab FROM TABLE it.
WRITE: / 'SUBRC:', sy-subrc, 'DBCNT:', sy-dbcnt.
"""
        res_batch = execute_abap_code(code_batch, user_id=self.user.user_id)
        self.assertTrue(res_batch["status"])
        self.assertEqual(res_batch["system_fields"].get("SY-SUBRC"), 0)
        self.assertEqual(res_batch["system_fields"].get("SY-DBCNT"), 2)
        self.assertIn("SUBRC: 0 DBCNT: 2", res_batch["output"])

        tbl.refresh_from_db()
        self.assertEqual(len(tbl.sample_records), 2)

    def test_regression_commit_work_does_not_mask_failed_insert(self):
        """COMMIT WORK must not turn SY-SUBRC=4 into 0 after a failed insert."""
        code = """REPORT ztest_commit.
INSERT znot_existing_tab FROM TABLE it_none.
COMMIT WORK.
WRITE: / 'SUBRC:', sy-subrc.
"""
        result = execute_abap_code(code, user_id=self.user.user_id)
        self.assertTrue(result["status"])
        self.assertEqual(result["system_fields"].get("SY-SUBRC"), 4)
        self.assertIn("SUBRC: 4", result["output"])

    def test_regression_host_variable_syntax_and_case_insensitivity(self):
        """Modern ABAP host variable @wa and lowercase table names work consistently."""
        tbl = ABAPDictionaryTable.objects.create(
            table_id="tabl_test_hostvar",
            user=self.user,
            table_name="ZHOST_VAR_TAB",
            description="Host Variable Table",
            fields_schema=[
                {"field": "MANDT", "type": "CLNT", "length": 3, "key": True},
                {"field": "KID", "type": "INT4", "length": 5, "key": True},
                {"field": "TITLE", "type": "CHAR", "length": 30, "key": False},
            ],
            sample_records=[],
        )

        code = """REPORT ztest_hostvar.
DATA: wa TYPE zhost_var_tab.
wa-kid = 99.
wa-title = 'Modern Syntax'.
INSERT zhost_var_tab FROM @wa.
IF sy-subrc = 0.
  WRITE: 'HOST VAR SUCCESS'.
ENDIF.
"""
        result = execute_abap_code(code, user_id=self.user.user_id)
        self.assertTrue(result["status"])
        self.assertIn("HOST VAR SUCCESS", result["output"])
        self.assertEqual(result["system_fields"].get("SY-SUBRC"), 0)

        tbl.refresh_from_db()
        self.assertEqual(len(tbl.sample_records), 1)
        self.assertEqual(tbl.sample_records[0]["TITLE"], "Modern Syntax")

    def test_regression_ddl_create_table_already_exists(self):
        """Native DDL CREATE TABLE rejects table that already exists with Database table already exists."""
        tbl = ABAPDictionaryTable.objects.create(
            table_id="tabl_test_ddl_dup",
            user=self.user,
            table_name="ZEXISTING_DDL_TAB",
            description="Existing DDL Table",
            fields_schema=[{"field": "MANDT", "type": "CLNT", "length": 3, "key": True}],
            sample_records=[],
        )

        ddl_code = """REPORT zddl_dup.
DATA: lo_sql TYPE REF TO cl_sql_statement.
CREATE OBJECT lo_sql.
lo_sql->execute_ddl( 'CREATE TABLE ZEXISTING_DDL_TAB ( ID CHAR(10) )' ).
"""
        res = execute_abap_code(ddl_code, user_id=self.user.user_id)
        self.assertFalse(res["status"])
        self.assertIn("Database table already exists", res["output"])

    def test_regression_case_insensitive_execution(self):
        """Lowercase and uppercase ABAP programs execute identically with correct SY-SUBRC."""
        code_upper = """REPORT ZCASE_UPPER.
DATA: LV_VAL TYPE I VALUE 100.
WRITE: / 'RESULT:', LV_VAL.
"""
        code_lower = """report zcase_lower.
data: lv_val type i value 100.
write: / 'RESULT:', lv_val.
"""
        res_upper = execute_abap_code(code_upper, user_id=self.user.user_id)
        res_lower = execute_abap_code(code_lower, user_id=self.user.user_id)

        self.assertTrue(res_upper["status"])
        self.assertTrue(res_lower["status"])
        self.assertIn("RESULT: 100", res_upper["output"])
        self.assertIn("RESULT: 100", res_lower["output"])
        self.assertEqual(res_upper["system_fields"].get("SY-SUBRC"), 0)
        self.assertEqual(res_lower["system_fields"].get("SY-SUBRC"), 0)

    def test_regression_syntax_check_exact_line_and_column(self):
        """Syntax check identifies exact line and column for invalid statements."""
        code_bad = "REPORT zsyntax_err.\nINVALID_STMT_CMD."
        chk_res = check_abap_syntax(code_bad)
        self.assertFalse(chk_res["valid"])
        self.assertGreater(len(chk_res["diagnostics"]), 0)
        first_diag = chk_res["diagnostics"][0]
        self.assertEqual(first_diag["line"], 2)
        self.assertGreaterEqual(first_diag["column"], 1)

    def test_regression_style_a_type_table_of(self):
        """Style A: DATA it TYPE TABLE OF zcustomers is accepted without 'Specify table type' errors."""
        code = """REPORT zstyle_a.
DATA it TYPE TABLE OF zcustomers.
"""
        chk = check_abap_syntax(code)
        self.assertTrue(chk["valid"], f"Syntax errors: {chk['diagnostics']}")
        errors = [d["message"] for d in chk["diagnostics"] if d["severity"] == "error"]
        self.assertEqual(len(errors), 0)

    def test_regression_style_b_like_table_of(self):
        """Style B: DATA it LIKE TABLE OF wa resolves line type from wa and appends correctly."""
        code = """REPORT zstyle_b.
DATA: wa TYPE zcustomers.
DATA it LIKE TABLE OF wa.
wa-cust_id = 1001.
wa-name = 'Test User'.
APPEND wa TO it.
WRITE: / 'Count:', lines( it ).
"""
        res = execute_abap_code(code)
        self.assertTrue(res["status"])
        self.assertIn("Count: 1", res["output"])
        self.assertIn("IT", res["internal_tables_state"])
        self.assertEqual(len(res["internal_tables_state"]["IT"]), 1)
        self.assertEqual(res["internal_tables_state"]["IT"][0]["CUST_ID"], 1001)

    def test_regression_style_c_standard_table_empty_key(self):
        """Style C: DATA it TYPE STANDARD TABLE OF zcustomers WITH EMPTY KEY is valid."""
        code = """REPORT zstyle_c.
DATA it TYPE STANDARD TABLE OF zcustomers WITH EMPTY KEY.
"""
        chk = check_abap_syntax(code)
        self.assertTrue(chk["valid"])
        self.assertEqual(len(chk["diagnostics"]), 0)

    def test_regression_style_d_sorted_and_hashed_tables(self):
        """Style D: Explicit SORTED and HASHED tables with valid UNIQUE KEY definitions."""
        code = """REPORT zstyle_d.
DATA it_sort TYPE SORTED TABLE OF zcustomers WITH UNIQUE KEY cust_id.
DATA it_hash TYPE HASHED TABLE OF zcustomers WITH UNIQUE KEY cust_id.
"""
        chk = check_abap_syntax(code)
        self.assertTrue(chk["valid"])
        self.assertEqual(len(chk["diagnostics"]), 0)

    def test_regression_itab_key_specification_restrictions(self):
        """Compiler rejects invalid key declarations for HASHED, SORTED, and STANDARD tables."""
        # 1. Hashed table without key
        chk1 = check_abap_syntax("REPORT zbad1.\nDATA it TYPE HASHED TABLE OF zcustomers.\n")
        self.assertFalse(chk1["valid"])
        self.assertTrue(any("unique key must be specified" in d["message"].lower() for d in chk1["diagnostics"]))

        # 2. Hashed table with non-unique key
        chk2 = check_abap_syntax("REPORT zbad2.\nDATA it TYPE HASHED TABLE OF zcustomers WITH NON-UNIQUE KEY cust_id.\n")
        self.assertFalse(chk2["valid"])
        self.assertTrue(any("unique key" in d["message"].lower() for d in chk2["diagnostics"]))

        # 3. Sorted table with empty key
        chk3 = check_abap_syntax("REPORT zbad3.\nDATA it TYPE SORTED TABLE OF zcustomers WITH EMPTY KEY.\n")
        self.assertFalse(chk3["valid"])
        self.assertTrue(any("does not allow empty key" in d["message"].lower() for d in chk3["diagnostics"]))

        # 4. Standard table with unique key
        chk4 = check_abap_syntax("REPORT zbad4.\nDATA it TYPE STANDARD TABLE OF zcustomers WITH UNIQUE KEY cust_id.\n")
        self.assertFalse(chk4["valid"])
        self.assertTrue(any("cannot have a unique key" in d["message"].lower() for d in chk4["diagnostics"]))

    def test_regression_append_to_hashed_table_forbidden(self):
        """APPEND operation to a HASHED TABLE is forbidden and reports clear diagnostic."""
        code = """REPORT zappend_hash.
DATA it TYPE HASHED TABLE OF zcustomers WITH UNIQUE KEY cust_id.
DATA wa TYPE zcustomers.
APPEND wa TO it.
"""
        chk = check_abap_syntax(code)
        self.assertFalse(chk["valid"])
        self.assertTrue(any("hashed tables cannot be accessed with append" in d["message"].lower() for d in chk["diagnostics"]))

        res = execute_abap_code(code)
        self.assertFalse(res["status"])
        self.assertTrue(any("hashed tables cannot be accessed with append" in d["message"].lower() for d in res["diagnostics"]))

        # Also verify runtime interpreter enforcement
        from .abap_engine.interpreter import ABAPInterpreter, ABAPRuntimeError
        from .abap_engine.parser import AppendNode
        interp = ABAPInterpreter()
        interp.variables["IT"] = []
        interp.variables["__TABLE_KIND_IT"] = "hashed"
        with self.assertRaises(ABAPRuntimeError) as ctx:
            interp._execute_node(AppendNode(source_var="WA", target_table="IT"))
        self.assertIn("not permitted for hashed tables", str(ctx.exception))

    def test_regression_full_program_insert_from_table_host_variable(self):
        """End-to-end user program: Style A internal table declaration, work area populate, APPEND, and INSERT FROM TABLE @it."""
        tbl = ABAPDictionaryTable.objects.create(
            table_id="tabl_test_cust_prog",
            user=self.user,
            table_name="ZCUSTOMERS",
            description="Customers Table",
            fields_schema=[
                {"field": "MANDT", "type": "CLNT", "length": 3, "key": True},
                {"field": "CUST_ID", "type": "INT4", "length": 10, "key": True},
                {"field": "NAME", "type": "CHAR", "length": 50, "key": False},
                {"field": "CITY", "type": "CHAR", "length": 50, "key": False},
            ],
            sample_records=[],
        )

        prog = """REPORT zcustomers.

DATA: wa TYPE zcustomers.
DATA it TYPE TABLE OF zcustomers.

wa-cust_id = 4234.
wa-name = 'ACME CORP'.
wa-city = 'BERLIN'.

APPEND wa TO it.

INSERT zcustomers FROM TABLE @it.

IF sy-subrc = 0.
  COMMIT WORK.
  WRITE: / 'CUSTOMER INSERTED SUCCESSFULLY'.
ELSE.
  WRITE: / 'INSERT FAILED'.
ENDIF.
"""
        chk = check_abap_syntax(prog)
        self.assertTrue(chk["valid"], f"Syntax check failed: {chk['diagnostics']}")

        res = execute_abap_code(prog, user_id=self.user.user_id)
        self.assertTrue(res["status"], f"Execution error: {res['output']}")
        self.assertIn("CUSTOMER INSERTED SUCCESSFULLY", res["output"])
        self.assertEqual(res["system_fields"].get("SY-SUBRC"), 0)

        tbl.refresh_from_db()
        self.assertEqual(len(tbl.sample_records), 1)
        self.assertEqual(str(tbl.sample_records[0]["CUST_ID"]), "4234")
        self.assertEqual(tbl.sample_records[0]["NAME"], "ACME CORP")
        self.assertEqual(tbl.sample_records[0]["CITY"], "BERLIN")

    def test_custom_table_creation_without_mandt(self):
        """Creating custom table without client_dependent does NOT add MANDT."""
        payload = {
            "table_name": "ZCLIENT_FREE",
            "description": "Client Free Table",
            "client_dependent": False,
            "fields_schema": [
                {"field": "CUST_ID", "type": "INT4", "length": 10, "key": True},
                {"field": "NAME", "type": "CHAR", "length": 50, "key": False},
                {"field": "CITY", "type": "CHAR", "length": 50, "key": False},
            ],
            "sample_records": [],
        }
        res = self.client.post("/apps/skiltrix/api/abap/dictionary/", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(res.status_code, 201)
        data = res.json()
        fields = [f["field"] for f in data["fields_schema"]]
        self.assertNotIn("MANDT", fields)
        self.assertEqual(fields, ["CUST_ID", "NAME", "CITY"])
        keys = [f["field"] for f in data["fields_schema"] if f.get("key")]
        self.assertEqual(keys, ["CUST_ID"])

    def test_custom_table_creation_composite_key(self):
        """User-defined composite keys without MANDT are respected."""
        payload = {
            "table_name": "ZCOMPOSITE_KEY",
            "description": "Composite Key Table",
            "client_dependent": False,
            "fields_schema": [
                {"field": "CUST_ID", "type": "INT4", "length": 10, "key": True},
                {"field": "CITY", "type": "CHAR", "length": 50, "key": True},
                {"field": "NAME", "type": "CHAR", "length": 50, "key": False},
            ],
            "sample_records": [],
        }
        res = self.client.post("/apps/skiltrix/api/abap/dictionary/", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(res.status_code, 201)
        data = res.json()
        keys = [f["field"] for f in data["fields_schema"] if f.get("key")]
        self.assertEqual(keys, ["CUST_ID", "CITY"])
        self.assertNotIn("MANDT", [f["field"] for f in data["fields_schema"]])

    def test_custom_table_creation_rejected_when_no_key(self):
        """Table creation without any key field returns 400 Bad Request."""
        payload = {
            "table_name": "ZNO_KEY_TABLE",
            "description": "No Key Table",
            "client_dependent": False,
            "fields_schema": [
                {"field": "NAME", "type": "CHAR", "length": 50, "key": False},
                {"field": "CITY", "type": "CHAR", "length": 50, "key": False},
            ],
            "sample_records": [],
        }
        res = self.client.post("/apps/skiltrix/api/abap/dictionary/", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(res.status_code, 400)
        self.assertIn("key field is required", res.json().get("detail", ""))

    def test_custom_table_client_dependent_explicitly_adds_mandt(self):
        """Setting client_dependent=True adds MANDT client field."""
        payload = {
            "table_name": "ZCLIENT_DEP",
            "description": "Client Dependent Table",
            "client_dependent": True,
            "fields_schema": [
                {"field": "CUST_ID", "type": "INT4", "length": 10, "key": True},
                {"field": "NAME", "type": "CHAR", "length": 50, "key": False},
            ],
            "sample_records": [],
        }
        res = self.client.post("/apps/skiltrix/api/abap/dictionary/", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(res.status_code, 201)
        data = res.json()
        fields = [f["field"] for f in data["fields_schema"]]
        self.assertIn("MANDT", fields)

    def test_crud_on_client_independent_table_without_mandt(self):
        """INSERT, SELECT, UPDATE, DELETE on table without MANDT respects exact schema."""
        tbl = ABAPDictionaryTable.objects.create(
            table_id="tabl_test_free_cust",
            user=self.user,
            table_name="ZCUSTOMERS_FREE",
            description="Free Customers",
            fields_schema=[
                {"field": "CUST_ID", "type": "INT4", "length": 10, "key": True},
                {"field": "NAME", "type": "CHAR", "length": 50, "key": False},
                {"field": "CITY", "type": "CHAR", "length": 50, "key": False},
            ],
            sample_records=[],
        )

        prog = """REPORT zfree_test.
DATA: wa TYPE zcustomers_free.
wa-cust_id = 999.
wa-name = 'GLOBAL INC'.
wa-city = 'TOKYO'.
INSERT zcustomers_free FROM @wa.
IF sy-subrc = 0.
  WRITE: / 'INSERT OK'.
ENDIF.
"""
        res = execute_abap_code(prog, user_id=self.user.user_id)
        self.assertTrue(res["status"], res["output"])
        self.assertIn("INSERT OK", res["output"])

        tbl.refresh_from_db()
        self.assertEqual(len(tbl.sample_records), 1)
        self.assertEqual(str(tbl.sample_records[0]["CUST_ID"]), "999")
        self.assertNotIn("MANDT", tbl.sample_records[0])

    def test_open_sql_inner_join_and_aliases_full_program(self):
        """Full Open SQL INNER JOIN with table aliases, qualified columns, positional struct mapping, lines(), and LOOP AT."""
        ABAPDictionaryTable.objects.create(
            table_id="tabl_zemployee",
            user=self.user,
            table_name="ZEMPLOYEE",
            description="Employees Table",
            fields_schema=[
                {"field": "EMP_ID", "type": "INT4", "length": 10, "key": True},
                {"field": "EMP_NAME", "type": "CHAR", "length": 50, "key": False},
                {"field": "EMP_DEPT", "type": "CHAR", "length": 50, "key": False},
                {"field": "EMP_SALARY", "type": "INT4", "length": 10, "key": False},
            ],
            sample_records=[
                {"EMP_ID": 101, "EMP_NAME": "JOHN DOE", "EMP_DEPT": "ENGINEERING", "EMP_SALARY": 95000},
                {"EMP_ID": 102, "EMP_NAME": "ALICE SMITH", "EMP_DEPT": "FINANCE", "EMP_SALARY": 85000},
            ],
        )

        ABAPDictionaryTable.objects.create(
            table_id="tabl_zemployee1",
            user=self.user,
            table_name="ZEMPLOYEE1",
            description="Employees Extra Info",
            fields_schema=[
                {"field": "EMP_ID", "type": "INT4", "length": 10, "key": True},
                {"field": "EMPCITY", "type": "CHAR", "length": 50, "key": False},
                {"field": "EMPDESIG", "type": "CHAR", "length": 50, "key": False},
            ],
            sample_records=[
                {"EMP_ID": 101, "EMPCITY": "ONGOLE", "EMPDESIG": "LEAD ARCHITECT"},
                {"EMP_ID": 102, "EMPCITY": "HYDERABAD", "EMPDESIG": "FINANCIAL ANALYST"},
            ],
        )

        prog = """REPORT zjoin_demo.

TYPES: BEGIN OF ty_employee,
         empid TYPE i,
         empname TYPE c LENGTH 20,
         empdept TYPE c LENGTH 20,
         empsalary TYPE i,
         empcity TYPE c LENGTH 20,
         empdesig TYPE c LENGTH 20,
       END OF ty_employee.

DATA wa TYPE ty_employee.
DATA it TYPE TABLE OF ty_employee.

SELECT a~emp_id, a~emp_name, a~emp_dept, a~emp_salary,
       b~empcity, b~empdesig
  FROM zemployee AS a
  INNER JOIN zemployee1 AS b
    ON a~emp_id = b~emp_id
  ORDER BY a~emp_id
  INTO TABLE @it.

WRITE: / 'TOTAL RECORDS:', lines( it ).

LOOP AT it INTO wa.
  WRITE: / wa-empid, wa-empname, wa-empcity, wa-empdesig.
ENDLOOP.
"""
        chk = check_abap_syntax(prog)
        self.assertTrue(chk["valid"], f"Syntax errors: {chk['diagnostics']}")

        res = execute_abap_code(prog, user_id=self.user.user_id)
        self.assertTrue(res["status"], f"Execution error: {res['output']}")
        self.assertIn("TOTAL RECORDS: 2", res["output"])
        self.assertIn("101 JOHN DOE ONGOLE LEAD ARCHITECT", res["output"])
        self.assertIn("102 ALICE SMITH HYDERABAD FINANCIAL ANALYST", res["output"])

    def test_open_sql_left_outer_join(self):
        """LEFT OUTER JOIN preserves unmatched left records with null-padded right fields."""
        ABAPDictionaryTable.objects.create(
            table_id="tabl_zleft_emp",
            user=self.user,
            table_name="ZLEFT_EMP",
            description="Left Table",
            fields_schema=[
                {"field": "EMP_ID", "type": "INT4", "length": 10, "key": True},
                {"field": "NAME", "type": "CHAR", "length": 50, "key": False},
            ],
            sample_records=[
                {"EMP_ID": 1, "NAME": "MATCHED"},
                {"EMP_ID": 2, "NAME": "UNMATCHED"},
            ],
        )

        ABAPDictionaryTable.objects.create(
            table_id="tabl_zright_emp",
            user=self.user,
            table_name="ZRIGHT_EMP",
            description="Right Table",
            fields_schema=[
                {"field": "EMP_ID", "type": "INT4", "length": 10, "key": True},
                {"field": "LOCATION", "type": "CHAR", "length": 50, "key": False},
            ],
            sample_records=[
                {"EMP_ID": 1, "LOCATION": "NEW YORK"},
            ],
        )

        prog = """REPORT zleft_demo.
DATA: it TYPE TABLE OF string,
      wa TYPE string.
SELECT a~emp_id, a~name, b~location
  FROM zleft_emp AS a
  LEFT OUTER JOIN zright_emp AS b
    ON a~emp_id = b~emp_id
  INTO TABLE @it.
WRITE: / 'COUNT:', lines( it ).
"""
        res = execute_abap_code(prog, user_id=self.user.user_id)
        self.assertTrue(res["status"], res["output"])
        self.assertIn("COUNT: 2", res["output"])

    def test_open_sql_join_missing_table_fails(self):
        """JOIN on non-existent table returns error diagnostic and sy-subrc = 4."""
        prog = """REPORT zmissing_join.
DATA: it TYPE TABLE OF string.
SELECT a~emp_id, b~info
  FROM kna1 AS a
  INNER JOIN znonexistent_table AS b
    ON a~kunnr = b~kunnr
  INTO TABLE @it.
WRITE: / 'SUBRC:', sy-subrc.
"""
        res = execute_abap_code(prog, user_id=self.user.user_id)
        self.assertEqual(res["system_fields"].get("SY-SUBRC"), 4)
        self.assertTrue(any("znonexistent_table" in d.get("message", "").lower() for d in res.get("diagnostics", [])))

    def test_regression_open_sql_join_all_six_fields_mapped(self):
        """Assert all six fields (id, name, dept, salary, city, desig) are populated and output in order."""
        ABAPDictionaryTable.objects.filter(table_name__in=["ZTST_EMP", "ZTST_EMP_EXTRA"], user=self.user).delete()

        ABAPDictionaryTable.objects.create(
            table_id="tabl_ztst_emp",
            user=self.user,
            table_name="ZTST_EMP",
            description="Employee Primary",
            fields_schema=[
                {"field": "EMP_ID", "type": "INT4", "length": 10, "key": True},
                {"field": "EMP_NAME", "type": "STRING", "length": 50, "key": False},
                {"field": "EMPDEPT", "type": "CHAR", "length": 30, "key": False},
                {"field": "EMOSALARY", "type": "CURR", "length": 15, "key": False},
            ],
            sample_records=[
                {"EMP_ID": 101, "EMP_NAME": "SMITH", "EMPDEPT": "BACKEND", "EMOSALARY": 50000},
            ],
        )

        ABAPDictionaryTable.objects.create(
            table_id="tabl_ztst_emp_extra",
            user=self.user,
            table_name="ZTST_EMP_EXTRA",
            description="Employee Secondary",
            fields_schema=[
                {"field": "EMP_ID", "type": "INT4", "length": 10, "key": True},
                {"field": "EMP_NAME", "type": "STRING", "length": 50, "key": False},
                {"field": "EMPCITY", "type": "CHAR", "length": 30, "key": False},
                {"field": "EMPDESIGNATION", "type": "CHAR", "length": 30, "key": False},
            ],
            sample_records=[
                {"EMP_ID": 101, "EMP_NAME": "SMITH", "EMPCITY": "ONGOLE", "EMPDESIGNATION": "DEVELOPER"},
            ],
        )

        # 1. Test Modern TYPES structure with INTO TABLE after FROM
        prog_modern = """REPORT ztest_join_six.
TYPES: BEGIN OF ty_emp_all,
         empid TYPE i,
         empname TYPE string,
         empdept TYPE string,
         empsalary TYPE i,
         empcity TYPE string,
         empdesig TYPE string,
       END OF ty_emp_all.

DATA: it TYPE STANDARD TABLE OF ty_emp_all WITH EMPTY KEY,
      wa TYPE ty_emp_all.

SELECT a~emp_id, a~emp_name, a~empdept, a~emosalary, b~empcity, b~empdesignation
  FROM ztst_emp AS a
  INNER JOIN ztst_emp_extra AS b
    ON a~emp_id = b~emp_id
  ORDER BY a~emp_id
  INTO TABLE @it.

LOOP AT it INTO wa.
  WRITE: / wa-empid, wa-empname, wa-empdept, wa-empsalary, wa-empcity, wa-empdesig.
ENDLOOP.
"""
        res_m = execute_abap_code(prog_modern, user_id=self.user.user_id)
        self.assertTrue(res_m["status"], res_m["output"])
        self.assertIn("101 SMITH BACKEND 50000 ONGOLE DEVELOPER", res_m["output"])

        # 2. Test Classic DATA: BEGIN OF structure with INTO TABLE before FROM
        prog_classic = """REPORT ztest_classic_join.
DATA: BEGIN OF wa,
        empid TYPE ztst_emp-emp_id,
        empname TYPE ztst_emp-emp_name,
        empdept TYPE ztst_emp-empdept,
        empsalary TYPE ztst_emp-emosalary,
        empcity TYPE ztst_emp_extra-empcity,
        empdesig TYPE ztst_emp_extra-empdesignation,
      END OF wa.

DATA: wa1 TYPE ztst_emp,
      it LIKE TABLE OF wa1.

SELECT a~empid a~empname a~empdept a~empsalary b~empcity b~empdeisgnation
  INTO TABLE @it
  FROM ztst_emp AS a
  INNER JOIN ztst_emp_extra AS b
    ON a~emp_id = b~emp_id
  ORDER BY a~emp_id.

LOOP AT it INTO wa.
  WRITE: / wa-empid, wa-empname, wa-empdept, wa-empsalary, wa-empcity, wa-empdesig.
ENDLOOP.
"""
        res_c = execute_abap_code(prog_classic, user_id=self.user.user_id)
        self.assertTrue(res_c["status"], res_c["output"])
        self.assertIn("101 SMITH BACKEND 50000 ONGOLE DEVELOPER", res_c["output"])

    def test_regression_open_sql_join_unmatched_does_not_fabricate(self):
        """Unmatched join rows must not fabricate city or designation values."""
        ABAPDictionaryTable.objects.filter(table_name__in=["ZTST_LEFT", "ZTST_RIGHT"], user=self.user).delete()

        ABAPDictionaryTable.objects.create(
            table_id="tabl_ztst_left",
            user=self.user,
            table_name="ZTST_LEFT",
            description="Left",
            fields_schema=[{"field": "EMP_ID", "type": "INT4", "key": True}],
            sample_records=[{"EMP_ID": 999}],
        )
        ABAPDictionaryTable.objects.create(
            table_id="tabl_ztst_right",
            user=self.user,
            table_name="ZTST_RIGHT",
            description="Right",
            fields_schema=[
                {"field": "EMP_ID", "type": "INT4", "key": True},
                {"field": "EMPCITY", "type": "CHAR", "key": False},
            ],
            sample_records=[{"EMP_ID": 100, "EMPCITY": "MUMBAI"}],
        )

        prog = """REPORT zleft_test.
TYPES: BEGIN OF ty_row,
         empid TYPE i,
         empcity TYPE string,
       END OF ty_row.
DATA: it TYPE STANDARD TABLE OF ty_row WITH EMPTY KEY,
      wa TYPE ty_row.

SELECT a~emp_id, b~empcity
  FROM ztst_left AS a
  LEFT OUTER JOIN ztst_right AS b
    ON a~emp_id = b~emp_id
  INTO TABLE @it.

LOOP AT it INTO wa.
  WRITE: / 'ID:', wa-empid, 'CITY:', wa-empcity.
ENDLOOP.
"""
        res = execute_abap_code(prog, user_id=self.user.user_id)
        self.assertTrue(res["status"])
        self.assertIn("ID: 999 CITY:", res["output"])
        self.assertNotIn("MUMBAI", res["output"])

    def test_regression_open_sql_unmapped_field_diagnostic(self):
        """Selected columns that cannot be mapped must report a diagnostic."""
        prog = """REPORT zdiag_test.
DATA: it TYPE TABLE OF string.
SELECT a~kunnr, b~completely_missing_column
  FROM kna1 AS a
  INNER JOIN kna1 AS b
    ON a~kunnr = b~kunnr
  INTO TABLE @it.
"""
        res = execute_abap_code(prog, user_id=self.user.user_id)
        self.assertTrue(any("COMPLETELY_MISSING_COLUMN" in d.get("message", "") for d in res.get("diagnostics", [])))

    def test_regression_select_without_order_by_executes_and_inline_data(self):
        """SELECT statements without ORDER BY must compile and execute cleanly with @DATA inline declarations."""
        ABAPDictionaryTable.objects.filter(table_name__in=["ZORD_CUST", "ZORD_CUST2"], user=self.user).delete()

        ABAPDictionaryTable.objects.create(
            table_id="tabl_zord_cust",
            user=self.user,
            table_name="ZORD_CUST",
            description="Customers Table",
            fields_schema=[
                {"field": "CUST_ID", "type": "INT4", "key": True},
                {"field": "NAME", "type": "STRING", "key": False},
                {"field": "CITY", "type": "CHAR", "length": 30, "key": False},
            ],
            sample_records=[
                {"CUST_ID": 20, "NAME": "BOB", "CITY": "BERLIN"},
                {"CUST_ID": 10, "NAME": "ALICE", "CITY": "AMSTERDAM"},
            ],
        )

        ABAPDictionaryTable.objects.create(
            table_id="tabl_zord_cust2",
            user=self.user,
            table_name="ZORD_CUST2",
            description="Customers Secondary Table",
            fields_schema=[
                {"field": "CUST_ID", "type": "INT4", "key": True},
                {"field": "COUNTRY", "type": "CHAR", "length": 10, "key": False},
            ],
            sample_records=[
                {"CUST_ID": 10, "COUNTRY": "NL"},
                {"CUST_ID": 20, "COUNTRY": "DE"},
            ],
        )

        # 1. SELECT * without ORDER BY into @DATA(lt_customers)
        prog1 = """REPORT ztest_no_order1.
SELECT *
  FROM zord_cust
  INTO TABLE @DATA(lt_customers).
WRITE: / 'COUNT:', lines( lt_customers ).
"""
        res1 = execute_abap_code(prog1, user_id=self.user.user_id)
        self.assertTrue(res1["status"], res1["output"])
        self.assertIn("COUNT: 2", res1["output"])

        # 2. SELECT specific fields without ORDER BY into @DATA(lt_customers)
        prog2 = """REPORT ztest_no_order2.
SELECT cust_id, name, city
  FROM zord_cust
  INTO TABLE @DATA(lt_customers).
WRITE: / 'COUNT:', lines( lt_customers ).
"""
        res2 = execute_abap_code(prog2, user_id=self.user.user_id)
        self.assertTrue(res2["status"], res2["output"])
        self.assertIn("COUNT: 2", res2["output"])

        # 3. INNER JOIN without ORDER BY into @DATA(lt_customers)
        prog3 = """REPORT ztest_no_order3.
SELECT a~cust_id, a~name, b~country
  FROM zord_cust AS a
  INNER JOIN zord_cust2 AS b
    ON a~cust_id = b~cust_id
  INTO TABLE @DATA(lt_customers).
WRITE: / 'COUNT:', lines( lt_customers ).
"""
        res3 = execute_abap_code(prog3, user_id=self.user.user_id)
        self.assertTrue(res3["status"], res3["output"])
        self.assertIn("COUNT: 2", res3["output"])

        # 4. SELECT with explicit ORDER BY sorts correctly
        prog4 = """REPORT ztest_with_order.
DATA: wa TYPE zord_cust.
SELECT cust_id, name, city
  FROM zord_cust
  ORDER BY cust_id
  INTO TABLE @DATA(lt_customers).

LOOP AT lt_customers INTO wa.
  WRITE: / wa-cust_id, wa-name.
ENDLOOP.
"""
        res4 = execute_abap_code(prog4, user_id=self.user.user_id)
        self.assertTrue(res4["status"], res4["output"])
        lines_out = [line.strip() for line in res4["output"].splitlines() if line.strip()]
        self.assertEqual(lines_out[0], "10 ALICE")
        self.assertEqual(lines_out[1], "20 BOB")

        # 5. WHERE combined with JOIN works with or without ORDER BY
        prog5_no_order = """REPORT ztest_where_join.
DATA: wa TYPE zord_cust.
SELECT a~cust_id, a~name, b~country
  FROM zord_cust AS a
  INNER JOIN zord_cust2 AS b
    ON a~cust_id = b~cust_id
  WHERE a~cust_id = 10
  INTO TABLE @DATA(lt_customers).
WRITE: / 'COUNT:', lines( lt_customers ).
"""
        res5 = execute_abap_code(prog5_no_order, user_id=self.user.user_id)
        self.assertTrue(res5["status"], res5["output"])
        self.assertIn("COUNT: 1", res5["output"])

        prog5_with_order = """REPORT ztest_where_join_order.
SELECT a~cust_id, a~name, b~country
  FROM zord_cust AS a
  INNER JOIN zord_cust2 AS b
    ON a~cust_id = b~cust_id
  WHERE a~cust_id > 0
  ORDER BY a~cust_id DESCENDING
  INTO TABLE @DATA(lt_customers).
WRITE: / 'COUNT:', lines( lt_customers ).
"""
        res5_order = execute_abap_code(prog5_with_order, user_id=self.user.user_id)
        self.assertTrue(res5_order["status"], res5_order["output"])
        self.assertIn("COUNT: 2", res5_order["output"])

    def test_62_abap_oo_class_basics_instance_and_static(self):
        """ABAP OO: Class definition, instance methods, static methods, class-data, write attributes."""
        code = """REPORT zoo_basics.
CLASS lcl_counter DEFINITION.
  PUBLIC SECTION.
    CLASS-DATA total_count TYPE i.
    DATA local_count TYPE i.
    CLASS-METHODS increment_total.
    METHODS increment_local.
    METHODS display.
ENDCLASS.

CLASS lcl_counter IMPLEMENTATION.
  METHOD increment_total.
    total_count = total_count + 1.
  ENDMETHOD.

  METHOD increment_local.
    local_count = local_count + 1.
  ENDMETHOD.

  METHOD display.
    WRITE: / 'LOCAL:', local_count, 'TOTAL:', total_count.
  ENDMETHOD.
ENDCLASS.

START-OF-SELECTION.
  DATA lo_c1 TYPE REF TO lcl_counter.
  DATA lo_c2 TYPE REF TO lcl_counter.
  CREATE OBJECT lo_c1.
  CREATE OBJECT lo_c2.

  lo_c1->increment_local( ).
  lo_c1->increment_local( ).
  lcl_counter=>increment_total( ).

  lo_c2->increment_local( ).
  lcl_counter=>increment_total( ).

  lo_c1->display( ).
  lo_c2->display( ).
"""
        res = execute_abap_code(code)
        self.assertTrue(res["status"], res["output"])
        self.assertIn("LOCAL: 2 TOTAL: 2", res["output"])
        self.assertIn("LOCAL: 1 TOTAL: 2", res["output"])

    def test_63_abap_oo_visibility_sections_access_control(self):
        """ABAP OO: PUBLIC, PROTECTED, and PRIVATE access controls."""
        code_illegal = """REPORT zoo_private.
CLASS lcl_vault DEFINITION.
  PUBLIC SECTION.
    METHODS open_vault.
  PRIVATE SECTION.
    DATA secret TYPE string VALUE 'SENSITIVE'.
ENDCLASS.

CLASS lcl_vault IMPLEMENTATION.
  METHOD open_vault.
    WRITE: / 'SECRET:', secret.
  ENDMETHOD.
ENDCLASS.

START-OF-SELECTION.
  DATA lo_v TYPE REF TO lcl_vault.
  CREATE OBJECT lo_v.
  WRITE: / lo_v->secret.
"""
        res_fail = execute_abap_code(code_illegal)
        self.assertFalse(res_fail["status"])
        self.assertIn("Cannot access PRIVATE attribute 'SECRET'", res_fail["output"])

        code_legal = """REPORT zoo_legal.
CLASS lcl_vault DEFINITION.
  PUBLIC SECTION.
    METHODS open_vault.
  PRIVATE SECTION.
    DATA secret TYPE string VALUE 'SENSITIVE'.
ENDCLASS.

CLASS lcl_vault IMPLEMENTATION.
  METHOD open_vault.
    WRITE: / 'SECRET:', secret.
  ENDMETHOD.
ENDCLASS.

START-OF-SELECTION.
  DATA lo_v TYPE REF TO lcl_vault.
  CREATE OBJECT lo_v.
  lo_v->open_vault( ).
"""
        res_ok = execute_abap_code(code_legal)
        self.assertTrue(res_ok["status"], res_ok["output"])
        self.assertIn("SECRET: SENSITIVE", res_ok["output"])

    def test_64_abap_oo_inheritance_polymorphism_and_redefinition(self):
        """ABAP OO: Inheritance, REDEFINITION, and dynamic dispatch (polymorphism)."""
        code = """REPORT zoo_poly.
CLASS animal DEFINITION.
  PUBLIC SECTION.
    METHODS speak.
ENDCLASS.

CLASS animal IMPLEMENTATION.
  METHOD speak.
    WRITE: / 'GENERIC ANIMAL SOUND'.
  ENDMETHOD.
ENDCLASS.

CLASS dog DEFINITION INHERITING FROM animal.
  PUBLIC SECTION.
    METHODS speak REDEFINITION.
ENDCLASS.

CLASS dog IMPLEMENTATION.
  METHOD speak.
    WRITE: / 'WOOF WOOF'.
  ENDMETHOD.
ENDCLASS.

CLASS cat DEFINITION INHERITING FROM animal.
  PUBLIC SECTION.
    METHODS speak REDEFINITION.
ENDCLASS.

CLASS cat IMPLEMENTATION.
  METHOD speak.
    WRITE: / 'MEOW MEOW'.
  ENDMETHOD.
ENDCLASS.

START-OF-SELECTION.
  DATA lo_anim1 TYPE REF TO animal.
  DATA lo_anim2 TYPE REF TO animal.
  CREATE OBJECT lo_anim1 TYPE dog.
  CREATE OBJECT lo_anim2 TYPE cat.

  lo_anim1->speak( ).
  lo_anim2->speak( ).
"""
        res = execute_abap_code(code)
        self.assertTrue(res["status"], res["output"])
        self.assertIn("WOOF WOOF", res["output"])
        self.assertIn("MEOW MEOW", res["output"])

    def test_65_abap_oo_super_call(self):
        """ABAP OO: super-> call within method redefinition."""
        code = """REPORT zoo_super.
CLASS lcl_parent DEFINITION.
  PUBLIC SECTION.
    METHODS greet.
ENDCLASS.

CLASS lcl_parent IMPLEMENTATION.
  METHOD greet.
    WRITE: / 'HELLO FROM PARENT'.
  ENDMETHOD.
ENDCLASS.

CLASS lcl_child DEFINITION INHERITING FROM lcl_parent.
  PUBLIC SECTION.
    METHODS greet REDEFINITION.
ENDCLASS.

CLASS lcl_child IMPLEMENTATION.
  METHOD greet.
    super->greet( ).
    WRITE: / 'AND CHILD'.
  ENDMETHOD.
ENDCLASS.

START-OF-SELECTION.
  DATA lo_c TYPE REF TO lcl_child.
  CREATE OBJECT lo_c.
  lo_c->greet( ).
"""
        res = execute_abap_code(code)
        self.assertTrue(res["status"], res["output"])
        self.assertIn("HELLO FROM PARENT", res["output"])
        self.assertIn("AND CHILD", res["output"])

    def test_66_abap_oo_abstract_classes_and_methods(self):
        """ABAP OO: ABSTRACT class cannot be instantiated, abstract methods must be implemented."""
        code_fail = """REPORT zoo_abs_fail.
CLASS lcl_shape DEFINITION ABSTRACT.
  PUBLIC SECTION.
    METHODS draw ABSTRACT.
ENDCLASS.

START-OF-SELECTION.
  DATA lo_s TYPE REF TO lcl_shape.
  CREATE OBJECT lo_s.
"""
        res_fail = execute_abap_code(code_fail)
        self.assertFalse(res_fail["status"])
        self.assertIn("Cannot instantiate ABSTRACT class 'LCL_SHAPE'", res_fail["output"])

        code_ok = """REPORT zoo_abs_ok.
CLASS lcl_shape DEFINITION ABSTRACT.
  PUBLIC SECTION.
    METHODS draw ABSTRACT.
ENDCLASS.

CLASS lcl_circle DEFINITION INHERITING FROM lcl_shape.
  PUBLIC SECTION.
    METHODS draw REDEFINITION.
ENDCLASS.

CLASS lcl_circle IMPLEMENTATION.
  METHOD draw.
    WRITE: / 'DRAWING CIRCLE'.
  ENDMETHOD.
ENDCLASS.

START-OF-SELECTION.
  DATA lo_s TYPE REF TO lcl_shape.
  CREATE OBJECT lo_s TYPE lcl_circle.
  lo_s->draw( ).
"""
        res_ok = execute_abap_code(code_ok)
        self.assertTrue(res_ok["status"], res_ok["output"])
        self.assertIn("DRAWING CIRCLE", res_ok["output"])

    def test_67_abap_oo_interfaces(self):
        """ABAP OO: INTERFACE definition, INTERFACES statement, qualified call and interface reference dispatch."""
        code = """REPORT zoo_intf.
INTERFACE zif_printable.
  METHODS print.
ENDINTERFACE.

CLASS zcl_document DEFINITION.
  PUBLIC SECTION.
    INTERFACES zif_printable.
ENDCLASS.

CLASS zcl_document IMPLEMENTATION.
  METHOD zif_printable~print.
    WRITE: / 'DOCUMENT PRINTED'.
  ENDMETHOD.
ENDCLASS.

START-OF-SELECTION.
  DATA lo_doc TYPE REF TO zcl_document.
  DATA lif_prn TYPE REF TO zif_printable.
  CREATE OBJECT lo_doc.

  lo_doc->zif_printable~print( ).

  lif_prn = lo_doc.
  lif_prn->print( ).
"""
        res = execute_abap_code(code)
        self.assertTrue(res["status"], res["output"])
        self.assertIn("DOCUMENT PRINTED", res["output"])

    def test_68_abap_oo_constructor_and_class_constructor(self):
        """ABAP OO: CONSTRUCTOR with parameters and CLASS_CONSTRUCTOR."""
        code = """REPORT zoo_ctors.
CLASS lcl_item DEFINITION.
  PUBLIC SECTION.
    CLASS-DATA init_status TYPE string.
    DATA item_name TYPE string.
    CLASS-METHODS class_constructor.
    METHODS constructor IMPORTING name TYPE string.
    METHODS display.
ENDCLASS.

CLASS lcl_item IMPLEMENTATION.
  METHOD class_constructor.
    init_status = 'INITIALIZED'.
  ENDMETHOD.

  METHOD constructor.
    item_name = name.
  ENDMETHOD.

  METHOD display.
    WRITE: / 'ITEM:', item_name, 'STATUS:', init_status.
  ENDMETHOD.
ENDCLASS.

START-OF-SELECTION.
  DATA lo_item TYPE REF TO lcl_item.
  CREATE OBJECT lo_item EXPORTING name = 'LAPTOP'.
  lo_item->display( ).
"""
        res = execute_abap_code(code)
        self.assertTrue(res["status"], res["output"])
        self.assertIn("ITEM: LAPTOP STATUS: INITIALIZED", res["output"])

    def test_69_abap_oo_method_parameters_and_returning(self):
        """ABAP OO: Method parameters with RETURNING and CHANGING."""
        code = """REPORT zoo_params.
CLASS lcl_calc DEFINITION.
  PUBLIC SECTION.
    METHODS add IMPORTING a TYPE i b TYPE i RETURNING VALUE(result) TYPE i.
    METHODS double_val CHANGING val TYPE i.
ENDCLASS.

CLASS lcl_calc IMPLEMENTATION.
  METHOD add.
    result = a + b.
  ENDMETHOD.

  METHOD double_val.
    val = val * 2.
  ENDMETHOD.
ENDCLASS.

START-OF-SELECTION.
  DATA lo_calc TYPE REF TO lcl_calc.
  CREATE OBJECT lo_calc.
  DATA lv_sum TYPE i.
  lv_sum = lo_calc->add( a = 15, b = 25 ).
  WRITE: / 'SUM:', lv_sum.

  DATA lv_num TYPE i VALUE 7.
  lo_calc->double_val( EXPORTING val = lv_num ).
  WRITE: / 'DOUBLED:', lv_num.
"""
        res = execute_abap_code(code)
        self.assertTrue(res["status"], res["output"])
        self.assertIn("SUM: 40", res["output"])
        self.assertIn("DOUBLED: 14", res["output"])

    def test_70_abap_oo_references_bound_initial_instance_of(self):
        """ABAP OO: IS BOUND, IS NOT BOUND, IS INITIAL, IS INSTANCE OF, null check."""
        code = """REPORT zoo_refs.
INTERFACE zif_worker.
  METHODS work.
ENDINTERFACE.

CLASS lcl_emp DEFINITION.
  PUBLIC SECTION.
    INTERFACES zif_worker.
ENDCLASS.

CLASS lcl_emp IMPLEMENTATION.
  METHOD zif_worker~work.
    WRITE: / 'WORKING'.
  ENDMETHOD.
ENDCLASS.

START-OF-SELECTION.
  DATA lo_e TYPE REF TO lcl_emp.
  IF lo_e IS NOT BOUND.
    WRITE: / 'NOT_BOUND_1'.
  ENDIF.
  IF lo_e IS INITIAL.
    WRITE: / 'INITIAL_1'.
  ENDIF.

  CREATE OBJECT lo_e.
  IF lo_e IS BOUND.
    WRITE: / 'BOUND_2'.
  ENDIF.
  IF lo_e IS NOT INITIAL.
    WRITE: / 'NOT_INITIAL_2'.
  ENDIF.

  IF lo_e IS INSTANCE OF lcl_emp.
    WRITE: / 'INSTANCE_OF_CLASS'.
  ENDIF.
  IF lo_e IS INSTANCE OF zif_worker.
    WRITE: / 'INSTANCE_OF_INTF'.
  ENDIF.

  CLEAR lo_e.
  IF lo_e IS NOT BOUND.
    WRITE: / 'NOT_BOUND_AFTER_CLEAR'.
  ENDIF.
"""
        res = execute_abap_code(code)
        self.assertTrue(res["status"], res["output"])
        self.assertIn("NOT_BOUND_1", res["output"])
        self.assertIn("INITIAL_1", res["output"])
        self.assertIn("BOUND_2", res["output"])
        self.assertIn("NOT_INITIAL_2", res["output"])
        self.assertIn("INSTANCE_OF_CLASS", res["output"])
        self.assertIn("INSTANCE_OF_INTF", res["output"])
        self.assertIn("NOT_BOUND_AFTER_CLEAR", res["output"])

    def test_71_abap_oo_raise_exception_type(self):
        """ABAP OO: RAISE EXCEPTION TYPE with TRY CATCH and get_text()."""
        code = """REPORT zoo_exc.
START-OF-SELECTION.
  TRY.
      WRITE: / 'BEFORE RAISE'.
      RAISE EXCEPTION TYPE cx_static_check EXPORTING text = 'CUSTOM EXCEPTION OCCURRED'.
      WRITE: / 'AFTER RAISE'.
    CATCH cx_static_check INTO DATA(lx_err).
      WRITE: / 'CAUGHT:', lx_err->get_text( ).
  ENDTRY.
"""
        res = execute_abap_code(code)
        self.assertTrue(res["status"], res["output"])
        self.assertIn("BEFORE RAISE", res["output"])
        self.assertNotIn("AFTER RAISE", res["output"])
        self.assertIn("CAUGHT: CUSTOM EXCEPTION OCCURRED", res["output"])








