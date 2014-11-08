import p4lib


def change_stdout(stdout):
    _, stderr, retval = p4lib._run.return_value
    p4lib._run.return_value = (stdout, stderr, retval)


def change_stdout_list(list_for_stdout):
    p4lib._run.side_effect = [(stdout, "", "") for stdout in list_for_stdout]
