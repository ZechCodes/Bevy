def single_return_value_cache(func):
    not_set = object()
    value = not_set

    def wrap(*args, **kwargs):
        nonlocal value
        if value is not_set:
            value = func(*args, **kwargs)

        return value

    return wrap
