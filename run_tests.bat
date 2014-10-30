#!bash
set PYTHONPATH=D:\Code\GitHub\python-p4lib\lib;%PYTHONPATH%
set PYTHONPATH=D:\Code\GitHub\python-p4lib\px;%PYTHONPATH%
set PYTHONPATH=D:\Code\GitHub\python-p4lib\test\functionnal;%PYTHONPATH%
echo %PYTHONPATH%
C:\Python27\python D:\Code\GitHub\python-p4lib\test\functionnal\test.py -x test_px_diff -x test_px_backout -x test_px_genpatch -x test_px_options
pause