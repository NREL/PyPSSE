@echo off

set ccfile="conec.flx"
set ctfile="conet.flx"

rem -------------------------------------------------------------------------------

for /F "useback tokens=*" %%i in ('%ccfile%') do (^
    set ccfpth=%%~dpi
    set ccfsrc=%%~ni
    set ccfext=%%~xi
)
set ccfobj="%ccfsrc%.obj"

for /F "useback tokens=*" %%i in ('%ctfile%') do (^
    set ctfpth=%%~dpi
    set ctfsrc=%%~ni
    set ctfext=%%~xi
)
set ctfobj="%ctfsrc%.obj"

set argall=%ccfile%
set argall=%argall% %ctfile%

set arg=%1
for /f "useback tokens=*" %%a in ('%arg%') do set arg=%%~a
if not "%arg%"=="" set argall=%argall% "%arg%"

if EXIST %ccfile% (
   if EXIST conec.obj del conec.obj
)
if EXIST %ctfile% (
   if EXIST conet.obj del conet.obj
)
CALL PARSEXT ~TPARSEXT.BAT void.txt 1
CALL ~TPARSEXT.BAT
for /f "useback tokens=*" %%a in ('%FBINPATH%') do set FBINPATH=%%~a
for /f "useback tokens=*" %%a in ('%Py27%') do set Py27=%%~a

"%Py27%python.exe" "%FBINPATH%cmdlusr.py" %argall%

if EXIST ~TPARSEXT.BAT del ~TPARSEXT.BAT
if EXIST %ccfobj% rename %ccfobj% conec.obj
if EXIST %ctfobj% rename %ctfobj% conet.obj

@ECHO If no errors, run "cload4"
