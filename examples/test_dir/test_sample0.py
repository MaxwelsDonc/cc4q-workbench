"""[C1] [docstring][module]"""

# [C2P1] [block][module]
#
# [C2P2] [block][module]


def add(a, b):
    """[C3] [docstring][function]"""
    # [C4] [block][function]
    result = a + b  # [C5] [inline][sentence]
    return result


"""?[C6] [docstring][module]"""


# [C7] [block][module]
def subtract(a, b):
    """[C8] [docstring][function]"""
    # [C9] [block][function]
    result = a - b  # [C10] [inline][sentence]
    return result


class MyClass:
    """[C11] [docstring][class]"""

    # [C12P1] [block][class]
    # [C12P2] [block][class]

    """?[C13] [docstring][class]"""

    def __init__(self):
        """[C14] [docstring][function]"""
        self.x = 42  # [C15] [inline][sentence]
        # [C16] [block][function]
        self.y = 0

    def compute(self):
        # [C17] [block][function]
        return self.x + self.y  # [C18] [inline][sentence]
