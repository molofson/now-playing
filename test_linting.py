def test_function(used_arg, unused_arg):  # noqa: U100
    """Test function with an unused argument."""
    return used_arg


def another_test(arg1, arg2):  # noqa: U100
    """Another function that doesn't use arg2."""
    print(arg1)
