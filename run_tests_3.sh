#!/bin/bash
DIR=$(dirname "${BASH_SOURCE[0]}")
echo $DIR
pushd $DIR
CURRENT_DIR=`pwd` 

export PYTHONPATH=$CURRENT_DIR/lib/:$PYTHONPATH
export PYTHONPATH=$CURRENT_DIR/px/:$PYTHONPATH
export PYTHONPATH=$CURRENT_DIR/test/functionnal/:$PYTHONPATH
echo $PYTHONPATH

python3 $CURRENT_DIR/test/functionnal/test.py -x test_px_diff -x test_px_backout -x test_px_genpatch -x test_px_options

popd

