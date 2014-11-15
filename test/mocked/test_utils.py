import p4lib


def change_stdout(stdout):
    _, stderr, retval = p4lib._run.return_value
    p4lib._run.return_value = (stdout, stderr, retval)


def change_stdout_list(list_for_stdout):
    p4lib._run.side_effect = [(stdout, "", "") for stdout in list_for_stdout]


def test_raw_option(testobject, method, *args, **kwargs):
    p4 = p4lib.P4()

    method_kwargs = dict(kwargs)
    if "expected" in method_kwargs:
        del method_kwargs["expected"]

    m = getattr(p4, method)
    m(user='other', *args, **method_kwargs)

    expected = ['p4', '-u', 'other'] + kwargs.get("expected", [])

    p4lib._run.assert_called_with(expected)
