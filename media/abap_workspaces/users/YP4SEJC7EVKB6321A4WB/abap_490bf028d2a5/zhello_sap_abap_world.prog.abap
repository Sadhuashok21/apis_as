*&---------------------------------------------------------------------*
*& Report ZHELLO_SAP_ABAP_WORLD
*& Description: Challenge: Hello SAP ABAP World
*& Package: $TMP
*&---------------------------------------------------------------------*
REPORT zhello_sap_abap_world.

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
