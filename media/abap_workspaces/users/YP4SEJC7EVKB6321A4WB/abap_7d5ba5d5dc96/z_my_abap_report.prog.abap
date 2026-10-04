*&---------------------------------------------------------------------*
*& Report Z_MY_ABAP_REPORT
*& Description: SkilTrix ABAP Development Program
*& Package: $TMP
*&---------------------------------------------------------------------*
REPORT z_my_abap_report.

* Data Declarations
DATA: lv_message TYPE string VALUE 'Welcome to SkilTrix SAP ABAP Studio!'.

* Main Processing Block
START-OF-SELECTION.
  WRITE: / '==================================================',
         / lv_message,
         / 'Current System Date:', sy-datum,
         / 'Current System Time:', sy-uzeit,
         / '=================================================='.
  ULINE.
