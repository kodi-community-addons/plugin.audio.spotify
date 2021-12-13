"""Logless logging platform."""

from contextlib import contextmanager
import datetime
import functools
import inspect
import logging
import threading
import queue
import os
import sys
import time

# pylint: disable = logging-format-interpolation

try:
    import psutil
except Exception as ex:
    psutil = None  # noqa
    logging.warning(
        f"Could not load psutils. Some logging function may not be available. {ex}"
    )


@functools.lru_cache(20)
def get_logger(app_name: str, debug=os.environ.get("DEBUG", None)):
    """
    Get a logger object.

    Arguments
    ---------
        app_name {str} -- An app string to use for the logger.

    Keyword Arguments
    -----------------
        debug {bool} -- Whether to include DEBUG output.

    Returns
    -------
        logger -- A logger object.

    """
    log_format = "%(asctime)s - %(levelname)s - %(message)s"
    log_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(format=log_format)
    logger = logging.getLogger(app_name)
    logger.setLevel(log_level)
    return logger


DEFAULT_HEARTBEAT_MINUTES = 5
DEFAULT_LOGGER = get_logger("slalom.dataops.logs")


def duration_to_string(seconds):
    """Return duration as a concise string. e.g. "32min 3s", "4hr 34min", etc."""
    units = ["hr", "min", "s"]
    duration_parts = [
        int(part) for part in str(datetime.timedelta(seconds=int(seconds))).split(":")
    ]
    if duration_parts[0]:
        # if >=1hr, append seconds as tenth of minutes
        # duration_parts[1] = duration_parts[1] + round(duration_parts[2] / 60, 1)
        duration_parts = duration_parts[:2]
    result = " ".join(
        [str(part) + units[x] for x, part in enumerate(duration_parts, 0) if part]
    )
    return result or "0s"


def elapsed_since(start, template="({duration} elapsed)"):
    """Return a formatted string, e.g. '(HH:MM:SS elapsed)'."""
    seconds = time.time() - start
    duration = duration_to_string(seconds=int(seconds))  # noqa
    return fstr(template, locals())


def flush_buffers():
    """Flush the logging buffers, stderr, and stdout."""
    sys.stdout.flush()
    sys.stderr.flush()
    for loghandler in DEFAULT_LOGGER.handlers:
        loghandler.flush()
    sys.stdout.flush()
    sys.stderr.flush()


def _convert_mem_units(
    from_val, from_units: str = None, to_units: str = None, sig_digits=None
):
    """
    Convert memory units.

    Arguments:
        from_val {[type]} -- [description]

    Keyword Arguments:
        from_units {str} -- [description] (default: {None})
        to_units {str} -- [description] (default: {None})
        sig_digits {[type]} -- [description] (default: {None})

    Returns:
        [type] -- [description]
    """
    from_units = from_units or "B"
    _mem_units_map = {
        "B": 1,
        "K": (1024 ** 1),
        "MB": (1024 ** 2),
        "GB": (1024 ** 3),
        "TB": (1024 ** 4),
    }
    num_bytes = from_val * _mem_units_map[from_units]
    return_tuple = not to_units
    if not to_units:
        cutover_factor = 800
        if to_units not in _mem_units_map:
            if num_bytes < 100:  # < 800 K as K
                to_units = "B"
            if num_bytes < cutover_factor * _mem_units_map["K"]:  # < 800 K as K
                to_units = "K"
            elif num_bytes < cutover_factor * _mem_units_map["MB"]:  # < 800 MB as MB
                to_units = "MB"
            elif num_bytes < cutover_factor * _mem_units_map["GB"]:  # < 800 GB as GB
                to_units = "GB"
            else:  # >= 800 TB as TB
                to_units = "TB"
    result = num_bytes * 1.0 / _mem_units_map[to_units]
    if not sig_digits:
        sig_digits = 1 if result >= 10 else 2
    if return_tuple:
        return round(result, sig_digits), to_units
    return round(result, sig_digits)


def _bytes_to_string(num_bytes, units=None):
    """
    Return a string that efficiently represents the number of bytes.

    e.g. "476.4MB", "0.92TB", etc.
    """
    new_value, units = _convert_mem_units(num_bytes, from_units="B", to_units=None)
    return f"{new_value}{units}"


def _ram_usage_string(process_id=None):
    """
    Return a string representing the amount and percentage of memory used by this process.
    """
    if not psutil:
        return "(unknown mem usage - missing psutil library)"
    process = psutil.Process(process_id or os.getpid())
    amount = _bytes_to_string(process.memory_info().rss)
    percent = process.memory_percent()
    return f"(mem usage: {amount}, {percent:,.1f}%)"


def _cpu_usage_string(process_id=None):
    """
    Return a string representing the amount and percentage of memory used by this process.
    """
    if not psutil:
        return "(unknown CPU usage - missing psutil library)"
    process = psutil.Process(process_id or os.getpid())
    return f"(CPU {process.cpu_percent(interval=0.2)}%)"


def _get_printable_context(context: dict = None, as_str=True):
    """Return a string or dict, obfuscating names that look like keys."""
    printable_dict = {
        k: (
            v
            if not any(
                [
                    "secret" in k.lower(),
                    "pwd" in k.lower(),
                    "pass" in k.lower(),
                    "access.key" in k.lower(),
                ]
            )
            else "****"
        )
        for k, v in context.items()
        if k != "__builtins__"
    }
    if as_str:
        return "\n".join([f"\t{k}:\t{v}" for k, v in printable_dict.items()])
    return printable_dict


def _caller_and_lineno():
    caller = inspect.getframeinfo(inspect.stack()[1][0])
    return f"{caller.filename}:{caller.lineno}"


def fstr(fstring_text, locals, globals=None):
    """Dynamically evaluate the provided `fstring_text`.

    Sample usage:
        format_str = "{i}*{i}={i*i}"
        i = 2
        fstr(format_str, locals()) # "2*2=4"
        i = 4
        fstr(format_str, locals()) # "4*4=16"
        fstr(format_str, {"i": 12}) # "10*10=100"
    """
    locals = locals or {}
    globals = globals or {}
    result = eval(f'f"{fstring_text}"', locals, globals)
    return result


def heartbeat_printer(
    desc_text,
    msg_queue: queue.Queue,
    interval,
    show_memory=True,
    show_cpu=None,
    start_time=None,
):
    start_time = start_time or time.time()
    show_memory = show_memory if show_memory is not None else True
    show_cpu = show_cpu if show_cpu is not None else show_memory
    time.sleep(interval)
    while msg_queue.empty():
        elapsed_str = elapsed_since(start_time, template="({duration} and counting...)")
        msg = f"Still {desc_text} {elapsed_str}"
        if show_cpu:
            msg += _cpu_usage_string(process_id=None)
        if show_memory:
            msg += _ram_usage_string(process_id=None)
        DEFAULT_LOGGER.info(msg)
        time.sleep(interval)


@contextmanager
def logged_block(
    desc_text,
    start_msg="Beginning {desc_text}...",
    success_msg="Completed {desc_text} {success_detail}  {elapsed}",
    success_detail="",  # noqa
    show_memory=None,
    heartbeat_interval=DEFAULT_HEARTBEAT_MINUTES * 60,
    **kwargs,
):
    """
    Time and log the execution inside a with block.

    Sample usage:

        with logged_block("running '{job.name}' job", job=job_obj):
            do_job(job)
    """
    start = time.time()
    context_dict = locals().copy()
    context_dict.update(kwargs)
    if start_msg:
        if show_memory:
            start_msg = start_msg + (" " * 15) + _ram_usage_string()
        DEFAULT_LOGGER.info(fstr(start_msg, locals=context_dict))
    msg_queue = None
    if heartbeat_interval:
        msg_queue = queue.Queue()
        heartbeat = threading.Thread(
            target=heartbeat_printer,
            args=[],
            kwargs={
                "desc_text": desc_text,
                "msg_queue": msg_queue,
                "interval": heartbeat_interval,
                "show_memory": show_memory,
            },
        )
        heartbeat.daemon = True
        heartbeat.start()
    yield
    if heartbeat:
        try:
            msg_queue.put("cancel")
        except Exception as ex:
            DEFAULT_LOGGER.exception("Failed to kill heartbeat log. {ex}")
    context_dict["elapsed"] = elapsed_since(start)
    if success_msg:
        if show_memory:
            success_msg = success_msg + _ram_usage_string()
        DEFAULT_LOGGER.info(fstr(success_msg, locals=context_dict))


class logged():
    """
    Decorator class for logging function start, completion, and elapsed time.

    Sample usage:
        @logged()
        def my_func_a():
            pass

        @logged(log_fn=logging.debug)
        def my_func_b():
            pass

        @logged("doing a thing")
        def my_func_c():
            pass

        @logged("doing a thing with {foo_obj.name}")
        def my_func_d(foo_obj):
            pass

        @logged("doing a thing with '{custom_kwarg}'", custom_kwarg="foo")
        def my_func_d(foo_obj):
            pass
    """

    def __init__(
        self,
        desc_text="{fn.__name__}() for '{desc_detail}'",
        desc_detail="",
        start_msg="Beginning {desc_text}...",
        success_msg="Completed {desc_text} {elapsed} ({success_detail})",
        success_detail="",
        buffer_lines=0,
        log_fn=None,
        **addl_kwargs,
    ):
        """All arguments optional."""
        log_fn = log_fn or DEFAULT_LOGGER.info
        self.default_context = addl_kwargs.copy()  # start with addl. args
        self.default_context.update(locals())  # merge all constructor args
        self.buffer_lines = buffer_lines

    def print_buffer(self):
        """Clear print buffer."""
        if self.buffer_lines:
            nl = "\n"
            flush_buffers()
            sys.stdout.write(f"\n\n{('-' * 80 + nl) * self.buffer_lines}\n\n")
            flush_buffers()

    def __call__(self, fn):
        """Call the decorated function."""

        def wrapped_fn(*args, **kwargs):
            """
            The decorated function definition.

            Note that the log needs access to
            all passed arguments to the decorator, as well as all of the function's
            native args in a dictionary, even if args are not provided by keyword.
            If start_msg is None or success_msg is None, those log entries are skipped.
            """

            def re_eval(context_dict, context_key: str):
                """Evaluate any f-strings in context_dict[context_key], save the result."""
                try:
                    context_dict[context_key] = fstr(
                        context_dict[context_key], locals=context_dict
                    )
                except Exception as ex:
                    DEFAULT_LOGGER.warning(
                        f"Error evaluating '{context_key}' "
                        f"({context_dict.get(context_key, '(missing)')})"
                        f": '{ex}' with context: '{_get_printable_context(context_dict)}'"
                    )

            start = time.time()
            fn_context = self.default_context.copy()
            fn_context["fn"] = fn
            fn_context["elapsed"] = None
            argspec = inspect.getfullargspec(fn)
            # DEFAULT_LOGGER.info(f"argspec: {argspec}")
            if argspec.defaults:
                # DEFAULT_LOGGER.info(
                #     f"attempting to set defaults: {list(enumerate(argspec.defaults, 1))}"
                # )
                for i, v in enumerate(reversed(argspec.defaults), 1):
                    fn_context[argspec.args[-1 * i]] = v
            if argspec.kwonlydefaults:
                fn_context.update(dict(argspec.kwonlydefaults))
            fn_arg_names = argspec.args.copy()
            # DEFAULT_LOGGER.info(f"args: {fn_arg_names}")
            if argspec.varargs is not None:
                # unnamed ordered args
                fn_context[argspec.varargs] = args
            else:
                for x, arg_value in enumerate(args, 0):
                    # DEFAULT_LOGGER.info(
                    #     f"Attempting to set: fn_arg_names[{x}] = {arg_value}"
                    # )
                    fn_context[fn_arg_names[x]] = arg_value
            fn_context.update(kwargs)
            desc_detail_fn = None
            log_fn = fn_context["log_fn"]
            # If desc_detail is callable, evaluate dynamically (both before and after)
            if callable(fn_context["desc_detail"]):
                desc_detail_fn = fn_context["desc_detail"]
                fn_context["desc_detail"] = desc_detail_fn()
            # Re-evaluate any decorator args which are fstrings
            re_eval(fn_context, "desc_detail")
            re_eval(fn_context, "desc_text")
            # Remove 'desc_detail' if blank or unused
            fn_context["desc_text"] = fn_context["desc_text"].replace("'' ", "")
            re_eval(fn_context, "start_msg")
            if fn_context["start_msg"]:
                self.print_buffer()
                log_fn(fn_context["start_msg"])  # log start of execution
            result = fn(*args, **kwargs)
            if fn_context["success_msg"]:  # log the end of execution
                if callable(fn_context["success_msg"]):
                    fn_context["success_msg"] = fn_context["success_msg"]()
                fn_context["result"] = result
                if desc_detail_fn:  # If desc_detail callable, then reevaluate
                    fn_context["desc_detail"] = desc_detail_fn()
                fn_context["elapsed"] = elapsed_since(start)
                re_eval(fn_context, "success_detail")
                re_eval(fn_context, "success_msg")
                log_fn(fn_context["success_msg"].replace(" ()", ""))
                self.print_buffer()
            return result

        wrapped_fn.__doc__ = fn.__doc__  # Use docstring from inner function.
        return wrapped_fn
