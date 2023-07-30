import functools


def throw_up(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        ret = func(*args, **kwargs)
        raise Exception(f"throw_up - ret: {ret}")

    return wrapper


def break_up(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        ret = func(*args, **kwargs)
        breakpoint()
        return ret

    return wrapper
