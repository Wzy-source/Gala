import signal


class TimeoutException(Exception):
    pass


def timeout_handler(signum, frame):
    raise TimeoutException("Operation timed out")


def with_timeout(timeout):
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Set the signal alarm for the specified timeout
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(timeout)
            try:
                result = func(*args, **kwargs)
            except TimeoutException:
                print("Function timed out")
                raise TimeoutException("Operation timed out")
            finally:
                signal.alarm(0)  # Disable the alarm
            return result

        return wrapper

    return decorator
