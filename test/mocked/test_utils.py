import p4lib


def change_stdout(stdout):
    _, stderr, retval = p4lib._run.return_value
    p4lib._run.return_value = (stdout, stderr, retval)


def change_stdout_list(list_for_stdout):
    p4lib._run.side_effect = [(stdout, "", "") for stdout in list_for_stdout]


def test_options(testobject, method, *args, **kwargs):
    p4 = p4lib.P4()

    method_kwargs = dict(kwargs)
    if "expected" in method_kwargs:
        del method_kwargs["expected"]

    m = getattr(p4, method)
    m(user='other', *args, **method_kwargs)

    expected = ['p4', '-u', 'other'] + kwargs.get("expected", [])

    p4lib._run.assert_called_with(expected)


def test_raw_result(testobject, stdout, method, *args, **kwargs):
    p4 = p4lib.P4()

    change_stdout(stdout)

    kwargs["_raw"] = True

    m = getattr(p4, method)
    raw_result = m(*args, **kwargs)

    testobject.assertIn('stdout', raw_result)
    testobject.assertIn('stderr', raw_result)
    testobject.assertIn('retval', raw_result)

    testobject.assertEqual(stdout, raw_result['stdout'])
    testobject.assertEqual("", raw_result['stderr'])
    testobject.assertEqual(0, raw_result['retval'])
