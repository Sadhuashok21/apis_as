REPORT zcustomers.

DATA: wa TYPE zcustomers.
DATA it TYpe  TABLE OF zcustomers.



wa-mandt   = 100.
wa-cust_id = 423283.
wa-name    = 'JHON'.
wa-city    = 'ONGOLE'.
wa-empsal  = 50200.

APPEND wa TO it.

INSERT zcustomers FROM TABLE @it.

IF sy-subrc = 0.
  COMMIT WORK.
  WRITE: 'INSERTED SUCCESSFULLY'.
ELSE.
  ROLLBACK WORK.
  WRITE: 'ERROR IN INSERTING. CODE:', sy-subrc.
ENDIF.