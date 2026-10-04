REPORT zcustomer.

data : begin of wa,
empid type zemployee1-emp_id,
empname type  zemployee-emp_name,
empdept type  zemployee-empdept,
empsalary type  zemployee-emosalary,
empcity type  zemployee1-empcity,
empdesig type  zemployee1-empdesignation,
end of wa.

data : wa1 type zemployee,
  it like table of wa1.

  select a~empid a~empname a~empdept a~empsalary b~empcity b~empdeisgnation into table @it from zemployee as a inner join   zemployee1 as b on a~emp_id = b~emp_id.


  loop at it into wa.
  write: wa1-empid , wa1-empname , wa1-empdept,wa1-empsalary,wa1-empcity,wa1-empdesig.

  uline.

  endloop.


if sy-subrc = 0.
commit work.
write : 'inserted successfully'.
else.
write : 'error in insertion'.
endif.
