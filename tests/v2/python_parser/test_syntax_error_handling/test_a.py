import sys

# Each tuple in list contains the following fields in order:
# source, message, start, end, exc_cls=SyntaxError, min_python_version=(3, 10)

test_1 = [
    (
        "f'a = {}'",
        (
            "valid expression required before '}'"
            if sys.version_info >= (3, 12)
            else "f-string: empty expression not allowed"
        ),
        (1, 8) if sys.version_info >= (3, 12) else None,
        (1, 9) if sys.version_info >= (3, 12) else None,
    ),
]