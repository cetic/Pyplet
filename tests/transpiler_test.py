"""Unit tests for pyplet.server._transpiler.

Each test class covers one AST transformer or a specific transpilation
scenario.  Tests use ``ast.unparse(ast.parse(source))`` as the canonical
form so that incidental whitespace differences don't cause false failures.
"""

import ast

from pyplet.server._transpiler import (  # LocalVariableObfuscator,
    ASTOptimizer,
    CommentRemover,
    DataclassAheadOfTimeTranspiler,
    DictPatcher,
    HtpyValidateChildrenStripper,
    IsInstanceTypeFixer,
    PositionalOnlyArgsFixer,
    RemoveTypeHint,
    StringJoinFixer,
    StringMethodFixer,
    StrSubclassNewStripper,
    SubscriptFixer,
    UnionTypeFixer,
    transpile_to_pyscript,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _norm(src: str) -> str:
    """Normalise source via a round-trip through the AST."""
    return ast.unparse(ast.parse(src))


def _apply(transformer, src: str) -> str:
    tree = ast.parse(src)
    tree = transformer.visit(tree)
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


# ---------------------------------------------------------------------------
# CommentRemover
# ---------------------------------------------------------------------------


class TestCommentRemover:
    def test_removes_module_docstring(self):
        src = '"""Module docstring."""\nx = 1'
        result = _apply(CommentRemover(), src)
        assert "Module docstring" not in result
        assert "x = 1" in result

    def test_removes_function_docstring(self):
        src = "def foo():\n    '''docstring'''\n    return 1"
        result = _apply(CommentRemover(), src)
        assert "docstring" not in result
        assert "return 1" in result

    def test_preserves_string_assignment(self):
        src = "x = 'this is a value'"
        result = _apply(CommentRemover(), src)
        assert "this is a value" in result

    def test_preserves_string_in_expression(self):
        src = "print('hello')"
        result = _apply(CommentRemover(), src)
        assert "print" in result

    def test_removes_class_docstring(self):
        src = "class Foo:\n    '''class doc'''\n    x = 1"
        result = _apply(CommentRemover(), src)
        assert "class doc" not in result


# ---------------------------------------------------------------------------
# DataclassAheadOfTimeTranspiler
# ---------------------------------------------------------------------------


class TestDataclassTranspiler:
    def test_removes_dataclass_import(self):
        src = "import dataclasses\nx = 1"
        result = _apply(DataclassAheadOfTimeTranspiler(), src)
        assert "dataclasses" not in result

    def test_removes_from_dataclass_import(self):
        src = "from dataclasses import dataclass, field\nx = 1"
        result = _apply(DataclassAheadOfTimeTranspiler(), src)
        assert "dataclasses" not in result
        assert "dataclass" not in result

    def test_converts_simple_dataclass(self):
        src = (
            "from dataclasses import dataclass\n"
            "@dataclass\n"
            "class Point:\n"
            "    x: int\n"
            "    y: int\n"
        )
        result = _apply(DataclassAheadOfTimeTranspiler(), src)
        assert "def __init__" in result
        assert "self.x = x" in result
        assert "self.y = y" in result
        assert "@dataclass" not in result

    def test_dataclass_with_defaults(self):
        src = (
            "from dataclasses import dataclass\n"
            "@dataclass\n"
            "class Config:\n"
            "    debug: bool = False\n"
            "    port: int = 8080\n"
        )
        result = _apply(DataclassAheadOfTimeTranspiler(), src)
        assert "debug=False" in result
        assert "port=8080" in result

    def test_preserves_non_dataclass(self):
        src = "class Plain:\n    x = 1"
        result = _apply(DataclassAheadOfTimeTranspiler(), src)
        assert "class Plain" in result
        assert "__init__" not in result


# ---------------------------------------------------------------------------
# DictPatcher
# ---------------------------------------------------------------------------


class TestDictPatcher:
    def test_patches_dict_unpacking(self):
        src = "x = {**a, **b}"
        result = _apply(DictPatcher(), src)
        assert "**" not in result
        assert "dict(" in result

    def test_patches_mixed_dict(self):
        src = "x = {'key': 1, **extra}"
        result = _apply(DictPatcher(), src)
        assert "**" not in result
        assert "dict(" in result

    def test_leaves_plain_dict_alone(self):
        src = "x = {'a': 1, 'b': 2}"
        result = _apply(DictPatcher(), src)
        assert result == _norm(src)

    def test_nested_dict_unpacking(self):
        src = "x = {**a, 'k': {**b}}"
        result = _apply(DictPatcher(), src)
        assert "**" not in result


# ---------------------------------------------------------------------------
# PositionalOnlyArgsFixer
# ---------------------------------------------------------------------------


class TestPositionalOnlyArgsFixer:
    def test_moves_posonly_to_regular(self):
        src = "def f(x, /, y): pass"
        result = _apply(PositionalOnlyArgsFixer(), src)
        # After fix, no '/' separator in unparsed output
        assert "/" not in result
        assert "def f(x, y)" in result

    def test_regular_args_unchanged(self):
        src = "def f(a, b, c): pass"
        result = _apply(PositionalOnlyArgsFixer(), src)
        assert "def f(a, b, c)" in result


# ---------------------------------------------------------------------------
# SubscriptFixer
# ---------------------------------------------------------------------------


class TestSubscriptFixer:
    def test_strips_list_subscript(self):
        src = "x: list[int] = []"
        result = _apply(SubscriptFixer(), src)
        assert "list[int]" not in result
        assert "list" in result

    def test_strips_dict_subscript(self):
        src = "x: dict[str, int] = {}"
        result = _apply(SubscriptFixer(), src)
        assert "dict[str, int]" not in result

    def test_strips_tuple_subscript(self):
        src = "x: tuple[int, str]"
        result = _apply(SubscriptFixer(), src)
        assert "tuple[int, str]" not in result

    def test_strips_set_subscript(self):
        src = "x: set[float]"
        result = _apply(SubscriptFixer(), src)
        assert "set[float]" not in result

    def test_leaves_other_subscripts_alone(self):
        src = "x = my_list[0]"
        result = _apply(SubscriptFixer(), src)
        assert "my_list[0]" in result

    def test_leaves_custom_class_subscript(self):
        src = "x: MyGeneric[int]"
        result = _apply(SubscriptFixer(), src)
        assert "MyGeneric[int]" in result


# ---------------------------------------------------------------------------
# UnionTypeFixer
# ---------------------------------------------------------------------------


class TestUnionTypeFixer:
    def test_converts_union_in_annotation(self):
        src = "def f(x: int | str) -> None: pass"
        result = _apply(UnionTypeFixer(), src)
        # Annotation should become a tuple
        assert "(int, str)" in result

    def test_converts_three_way_union(self):
        src = "x: int | str | None"
        result = _apply(UnionTypeFixer(), src)
        assert "(int, str, None)" in result

    def test_converts_return_annotation(self):
        src = "def f() -> int | None: pass"
        result = _apply(UnionTypeFixer(), src)
        assert "(int, None)" in result

    def test_preserves_bitwise_or_in_body(self):
        """Runtime | (bitwise OR / set union) must NOT be converted."""
        src = "result = a | b"
        result = _apply(UnionTypeFixer(), src)
        assert "a | b" in result
        assert "(a, b)" not in result

    def test_preserves_dict_merge_in_body(self):
        src = "merged = dict1 | dict2"
        result = _apply(UnionTypeFixer(), src)
        assert "dict1 | dict2" in result

    def test_preserves_set_union_in_body(self):
        src = "s = {1, 2} | {3, 4}"
        result = _apply(UnionTypeFixer(), src)
        assert "|" in result

    def test_converts_isinstance_type_arg(self):
        """isinstance second arg with | should become a tuple."""
        src = "isinstance(x, int | str)"
        result = _apply(UnionTypeFixer(), src)
        assert "(int, str)" in result

    def test_converts_poly_isinstance_type_arg(self):
        src = "poly_isinstance(x, int | str)"
        result = _apply(UnionTypeFixer(), src)
        assert "(int, str)" in result

    def test_annassign_union_becomes_tuple(self):
        src = "x: int | float = 0"
        result = _apply(UnionTypeFixer(), src)
        assert "(int, float)" in result


# ---------------------------------------------------------------------------
# IsInstanceTypeFixer
# ---------------------------------------------------------------------------


class TestIsInstanceTypeFixer:
    def test_isinstance_renamed(self):
        src = "isinstance(x, str)"
        result = _apply(IsInstanceTypeFixer(), src)
        assert "poly_isinstance(x, str)" in result
        assert "isinstance" not in result.replace("poly_isinstance", "")

    def test_issubclass_renamed(self):
        src = "issubclass(MyClass, Base)"
        result = _apply(IsInstanceTypeFixer(), src)
        assert "poly_issubclass" in result
        assert result.count("issubclass") == 1  # only the poly_ one

    def test_other_calls_unchanged(self):
        src = "len([1, 2, 3])"
        result = _apply(IsInstanceTypeFixer(), src)
        assert "len([1, 2, 3])" in result


# ---------------------------------------------------------------------------
# StringMethodFixer
# ---------------------------------------------------------------------------


class TestStringMethodFixer:
    def test_removesuffix_replaced(self):
        src = 's = name.removesuffix("_client")'
        result = _apply(StringMethodFixer(), src)
        assert "__removesuffix" in result
        assert "removesuffix" not in result.replace("__removesuffix", "")

    def test_removeprefix_replaced(self):
        src = 's = name.removeprefix("test_")'
        result = _apply(StringMethodFixer(), src)
        assert "__removeprefix" in result

    def test_removesuffix_args_preserved(self):
        src = 's = name.removesuffix("_client")'
        result = _apply(StringMethodFixer(), src)
        # The original string arg should be in the new call
        assert "_client" in result

    def test_other_methods_unchanged(self):
        src = "x = s.upper()"
        result = _apply(StringMethodFixer(), src)
        assert "s.upper()" in result


# ---------------------------------------------------------------------------
# StrSubclassNewStripper
# ---------------------------------------------------------------------------


class TestStrSubclassNewStripper:
    def test_strips_new_from_str_subclass(self):
        src = (
            "class Markup(str):\n"
            "    def __new__(cls, val):\n"
            "        return super().__new__(cls, val)\n"
            "    def __repr__(self):\n"
            "        return f'M({str(self)!r})'\n"
        )
        result = _apply(StrSubclassNewStripper(), src)
        assert "__new__" not in result
        assert "__repr__" in result

    def test_leaves_non_str_subclass_alone(self):
        src = (
            "class MyList(list):\n"
            "    def __new__(cls):\n"
            "        return super().__new__(cls)\n"
        )
        result = _apply(StrSubclassNewStripper(), src)
        assert "__new__" in result


# ---------------------------------------------------------------------------
# StringJoinFixer
# ---------------------------------------------------------------------------


class TestStringJoinFixer:
    def test_join_wrapped(self):
        src = 'result = ", ".join(items)'
        result = _apply(StringJoinFixer(), src)
        assert "list(map(str, items))" in result

    def test_join_with_generator_wrapped(self):
        src = "result = sep.join(x for x in lst)"
        result = _apply(StringJoinFixer(), src)
        assert "map(str" in result

    def test_join_no_arg_not_touched(self):
        # join with no args (syntax error in real Python, but AST handles it)
        src = "sep.join()"
        result = _apply(StringJoinFixer(), src)
        # Not transformed (0 args)
        assert "map" not in result


# ---------------------------------------------------------------------------
# HtpyValidateChildrenStripper
# ---------------------------------------------------------------------------


class TestHtpyValidateChildrenStripper:
    def test_strips_validate_children_body(self):
        src = (
            "def _validate_children(children):\n"
            "    for c in children:\n"
            "        if not isinstance(c, Node):\n"
            "            raise TypeError(c)\n"
        )
        result = _apply(HtpyValidateChildrenStripper(), src)
        assert "isinstance" not in result
        assert "pass" in result

    def test_leaves_other_functions_alone(self):
        src = "def render(children):\n    return children"
        result = _apply(HtpyValidateChildrenStripper(), src)
        assert "return children" in result


# ---------------------------------------------------------------------------
# RemoveTypeHint
# ---------------------------------------------------------------------------


class TestRemoveTypeHint:
    def test_strips_function_arg_annotations(self):
        src = "def f(x: int, y: str) -> bool: pass"
        result = _apply(RemoveTypeHint(), src)
        assert ": int" not in result
        assert ": str" not in result
        assert "-> bool" not in result

    def test_strips_return_annotation(self):
        src = "def f() -> list[int]: return []"
        result = _apply(RemoveTypeHint(), src)
        assert "->" not in result

    def test_strips_var_annotation_with_value(self):
        src = "x: int = 5"
        result = _apply(RemoveTypeHint(), src)
        assert ": int" not in result
        assert "x = 5" in result

    def test_removes_bare_annotation(self):
        src = "x: int"
        result = _apply(RemoveTypeHint(), src)
        assert "x" not in result or ": int" not in result

    def test_strips_kwonly_annotations(self):
        src = "def f(*, x: int, y: str): pass"
        result = _apply(RemoveTypeHint(), src)
        assert ": int" not in result
        assert ": str" not in result

    def test_strips_vararg_annotation(self):
        src = "def f(*args: int): pass"
        result = _apply(RemoveTypeHint(), src)
        assert ": int" not in result

    def test_strips_kwargs_annotation(self):
        src = "def f(**kwargs: str): pass"
        result = _apply(RemoveTypeHint(), src)
        assert ": str" not in result


# ---------------------------------------------------------------------------
# ASTOptimizer
# ---------------------------------------------------------------------------


class TestASTOptimizer:
    def test_removes_assert(self):
        src = "assert x > 0\ny = 1"
        result = _apply(ASTOptimizer(), src)
        assert "assert" not in result
        assert "y = 1" in result

    def test_eliminates_if_false(self):
        src = "if False:\n    dead_code()\nelse:\n    live_code()"
        result = _apply(ASTOptimizer(), src)
        assert "dead_code" not in result
        assert "live_code" in result

    def test_eliminates_if_debug(self):
        src = "if __debug__:\n    check()\nelse:\n    run()"
        result = _apply(ASTOptimizer(), src)
        assert "check" not in result
        assert "run" in result

    def test_leaves_truthy_if_alone(self):
        src = "if True:\n    always()"
        result = _apply(ASTOptimizer(), src)
        assert "always" in result


# ---------------------------------------------------------------------------
# transpile_to_pyscript — end-to-end
# ---------------------------------------------------------------------------


class TestTranspileEndToEnd:
    def test_py_mode_preserves_type_hints(self):
        """In 'py' mode (CPython/Pyodide), annotations should be kept."""
        src = "def f(x: int) -> str:\n    return str(x)"
        result = transpile_to_pyscript(src, targer_interpreter="py")
        assert "int" in result
        assert "str" in result

    def test_py_mode_strips_docstrings(self):
        src = '"""Module doc."""\nx = 1'
        result = transpile_to_pyscript(src, targer_interpreter="py")
        assert "Module doc" not in result

    def test_mpy_mode_strips_type_hints(self):
        src = "def f(x: int) -> str:\n    return str(x)"
        result = transpile_to_pyscript(src, targer_interpreter="mpy")
        assert ": int" not in result
        assert "-> str" not in result

    def test_mpy_mode_fixes_dict_unpacking(self):
        src = "x = {**a, **b}"
        result = transpile_to_pyscript(src, targer_interpreter="mpy")
        assert "**" not in result
        assert "dict(" in result

    def test_mpy_mode_fixes_posonly_args(self):
        src = "def f(x, /, y): pass"
        result = transpile_to_pyscript(src, targer_interpreter="mpy")
        assert "/" not in result

    def test_mpy_mode_converts_isinstance(self):
        src = "isinstance(x, str)"
        result = transpile_to_pyscript(src, targer_interpreter="mpy")
        assert "poly_isinstance" in result

    def test_mpy_mode_preserves_bitwise_or(self):
        src = "result = flags | mask"
        result = transpile_to_pyscript(src, targer_interpreter="mpy")
        assert "flags | mask" in result
        assert "(flags, mask)" not in result

    def test_mpy_mode_converts_annotation_union(self):
        src = "def f(x: int | str): pass"
        result = transpile_to_pyscript(src, targer_interpreter="mpy")
        # Annotation should be removed entirely (RemoveTypeHint runs after)
        assert ": int" not in result
        assert ": str" not in result

    def test_syntax_error_returns_original(self):
        src = "def f(\n  # broken syntax"
        result = transpile_to_pyscript(src, targer_interpreter="mpy")
        assert result == src

    def test_optimize_removes_assert(self):
        src = "assert x > 0\ny = 1"
        result = transpile_to_pyscript(
            src, targer_interpreter="mpy", optimize=True
        )
        assert "assert" not in result

    def test_mpy_removesuffix_polyfill(self):
        src = 'name = s.removesuffix("_client")'
        result = transpile_to_pyscript(src, targer_interpreter="mpy")
        assert "__removesuffix" in result

    def test_dataclass_transpiled_in_mpy(self):
        src = (
            "from dataclasses import dataclass\n"
            "@dataclass\n"
            "class Point:\n"
            "    x: int\n"
            "    y: int\n"
        )
        result = transpile_to_pyscript(src, targer_interpreter="mpy")
        assert "def __init__" in result
        assert "dataclasses" not in result

    def test_mpy_isinstance_union_converted_to_tuple(self):
        """isinstance with a | union should have the type arg as tuple."""
        src = "isinstance(x, int | str)"
        result = transpile_to_pyscript(src, targer_interpreter="mpy")
        assert "(int, str)" in result
