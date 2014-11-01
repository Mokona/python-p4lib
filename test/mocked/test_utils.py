import p4lib


def change_stdout(stdout):
    _, stderr, retval = p4lib._run.return_value
    p4lib._run.return_value = (stdout, stderr, retval)

