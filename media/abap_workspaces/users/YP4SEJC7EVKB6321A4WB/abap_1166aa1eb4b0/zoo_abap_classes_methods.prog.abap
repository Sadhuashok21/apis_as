*&---------------------------------------------------------------------*
*& Report ZOO_ABAP_CLASSES_METHODS
*& Description: Challenge: Object-Oriented ABAP: Classes & Methods
*& Package: $TMP
*&---------------------------------------------------------------------*
REPORT zoo_abap_classes_methods.

* Data Declarations
DATA: lv_message TYPE string VALUE 'Welcome to SkilTrix SAP ABAP Studio!'.

* Main Processing Block
START-OF-SELECTION.
  WRITe '==================================================',
         / lv_message,
         / 'Current System Date:', sy-datum,
         / 'Current System Time:', sy-uzeit,
         / '=================================================='.
  ULINE.
