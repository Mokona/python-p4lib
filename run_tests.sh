#!bash
export PYTHONPATH=/opt/p4lib/lib/:$PYTHONPATH
export PYTHONPATH=/opt/p4lib/px/:$PYTHONPATH
export PYTHONPATH=/opt/p4lib/test/functionnal/:$PYTHONPATH
echo $PYTHONPATH
python /opt/p4lib/test/functionnal/test.py -x test_px_diff -x test_px_backout -x test_px_genpatch -x test_px_options
