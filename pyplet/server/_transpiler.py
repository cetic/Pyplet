"""This module helps to make generic code compatible with MicroPython."""

import ast
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


class CommentRemover(ast.NodeTransformer):
    def visit_Expr(self, node):
        # Modern Python (3.8+) uses ast.Constant for all literals
        if isinstance(node.value, ast.Constant) and isinstance(
            node.value.value, str
        ):
            return None
        return node


# Uncomplete implementation
class DataclassAheadOfTimeTranspiler(ast.NodeTransformer):
    # 1. STRIP DATACLASS IMPORTS
    def visit_Import(self, node):
        node.names = [n for n in node.names if n.name != "dataclasses"]
        return node if node.names else None

    def visit_ImportFrom(self, node):
        if node.module == "dataclasses":
            return None
        return node

    # 2. UNROLL DATACLASSES INTO VANILLA CLASSES
    def visit_ClassDef(self, node):
        self.generic_visit(node)

        # Check if this class is a dataclass
        is_dataclass = False
        new_decs = []
        for dec in node.decorator_list:
            dec_str = ast.unparse(dec)
            if "dataclass" in dec_str:
                is_dataclass = True
            else:
                new_decs.append(dec)

        if not is_dataclass:
            return node

        # Remove the @dataclass decorator
        node.decorator_list = new_decs

        # Extract fields to build the __init__ signature
        fields = []  # List of (name, default_value_str, is_kw_only)
        kw_only_mode = False
        new_body = []

        for stmt in node.body:
            if isinstance(stmt, ast.AnnAssign) and isinstance(
                stmt.target, ast.Name
            ):
                ann_str = ast.unparse(stmt.annotation)

                # If we hit dataclasses.KW_ONLY, mark it and drop the
                # statement
                if "KW_ONLY" in ann_str:
                    kw_only_mode = True
                    continue

                name = stmt.target.id
                default_str = ast.unparse(stmt.value) if stmt.value else None
                fields.append((name, default_str, kw_only_mode))

            new_body.append(stmt)

        # Synthesize the __init__ method source code
        args = []
        kw_args = []
        init_body = []

        for name, default, is_kw in fields:
            if is_kw or default is not None:
                def_val = default if default is not None else "None"
                kw_args.append(f"{name}={def_val}")
            else:
                args.append(name)

            init_body.append(f"    self.{name} = {name}")

        sig_parts = ["self"] + args
        if kw_args:
            sig_parts.append("*")
            sig_parts.extend(kw_args)

        if not init_body:
            init_body = ["    pass"]

        # Parse the synthesized __init__ string back into an AST node
        init_code = f"def __init__({', '.join(sig_parts)}):\n" + "\n".join(
            init_body
        )

        try:
            init_ast = ast.parse(init_code).body[0]
            new_body.append(init_ast)
        except SyntaxError:
            logger.warning(
                "Warning: Could not synthesize __init__ for %s", node.name
            )

        node.body = new_body
        return node


class DictPatcher(ast.NodeTransformer):
    def visit_Dict(self, node):
        # Visit child nodes first in case of nested dictionaries
        self.generic_visit(node)

        # In AST, a `None` in the keys list represents a `**`
        # unpacking operation
        if None in node.keys:
            try:
                parts = []
                for k, v in zip(node.keys, node.values):
                    v_str = ast.unparse(v)
                    if k is None:
                        # This is a **v unpacking.
                        # Convert it to a list of its items.
                        parts.append(f"list(({v_str}).items())")
                    else:
                        k_str = ast.unparse(k)
                        # This is a standard k: v pair.
                        # Wrap it in a single-item list of tuples.
                        parts.append(f"[({k_str}, {v_str})]")

                # If for some reason we didn't generate any parts, abort safely
                if not parts:
                    return node

                # Construct the MicroPython-safe equivalent
                # logic by concatenating the lists
                # e.g., dict(list(dict1.items())
                # + list(dict2.items()) + [(key, val)])
                safe_code = f"dict({' + '.join(parts)})"

                # Parse our new safe code back into an AST node
                new_node = ast.parse(safe_code).body[0].value

                # Replace the original Dict node with our new Call node
                return ast.copy_location(new_node, node)

            except Exception as e:
                # If something goes catastrophically wrong,
                # print it so we can debug,
                # but don't crash the server.
                import logging

                logging.warning(f"Failed to patch dictionary unpacking: {e}")
                pass

        return node


class PositionalOnlyArgsFixer(ast.NodeTransformer):
    def visit_arguments(self, node):
        self.generic_visit(node)
        # Check if the function has positional-only
        # arguments (the '/' syntax)
        if getattr(node, "posonlyargs", None):
            # Move them to the standard arguments list
            node.args = node.posonlyargs + node.args
            # Empty out the positional-only list to
            # remove the '/' from the source code
            node.posonlyargs = []
        return node


class SubscriptFixer(ast.NodeTransformer):
    def visit_Subscript(self, node):
        # Visit children first in case of nested subscripts
        # (e.g., list[dict[str, int]])
        self.generic_visit(node)

        # Check if the base value being subscripted is a simple name
        if isinstance(node.value, ast.Name):
            # List of Python 3.9+ built-ins that became subscriptable
            # for type hinting
            pep_585_builtins = {
                "type",
                "list",
                "dict",
                "tuple",
                "set",
                "frozenset",
            }

            if node.value.id in pep_585_builtins:
                # Replace the entire `type[Something]`
                # node with just the `type` node
                return ast.copy_location(node.value, node)

        return node


class UnionTypeFixer(ast.NodeTransformer):
    def visit_BinOp(self, node):
        # Visit children first to handle nested unions (e.g., A | B | None)
        self.generic_visit(node)

        # Check if the operation is a Bitwise OR (|)
        if isinstance(node.op, ast.BitOr):
            # Helper function to guess if an AST node is a Type Hint
            def is_type_node(n):
                # Is it `None`? (You can't mathematically OR with None,
                # so it must be a type union)
                if isinstance(n, ast.Constant) and n.value is None:
                    return True
                # Is it a standard primitive or known htpy type?
                if isinstance(n, ast.Name):
                    return n.id in {
                        "type",
                        "str",
                        "int",
                        "bool",
                        "float",
                        "bytes",
                        "list",
                        "dict",
                        "set",
                        "tuple",
                        "Any",
                        "Node",
                        "Context",
                        "T",
                        "P",
                    }
                # Is it something like t.Any or collections.abc.Mapping?
                if isinstance(n, ast.Attribute):
                    return n.attr in {"Any", "Mapping", "Iterator", "Callable"}
                return False

            # If either side looks like a type, this is a Type Union,
            # not a math operation!
            if is_type_node(node.left) or is_type_node(node.right):
                # Collapse the union by just returning one side.
                # (If the left side is None, return the right side instead)
                if (
                    isinstance(node.left, ast.Constant)
                    and node.left.value is None
                ):
                    return node.right
                return node.left

        return node


class IsInstanceTypeFixer(ast.NodeTransformer):
    """Rewrites Abstract Base Classes in isinstance()
    checks to concrete MicroPython types."""

    def visit_Call(self, node):
        self.generic_visit(node)

        # Intercept isinstance() and issubclass() function calls
        if isinstance(node.func, ast.Name) and node.func.id in {
            "isinstance",
            "issubclass",
        }:
            if len(node.args) == 2:
                # Recursive helper to dig through tuples like
                # isinstance(x, (Mapping, str))
                def rewrite_type(n):
                    if isinstance(n, ast.Name):
                        # Map abstract concepts to concrete primitives that
                        # MicroPython understands
                        if n.id == "Mapping":
                            n.id = "dict"
                        elif n.id in {
                            "Iterable",
                            "Sequence",
                            "MutableSequence",
                        }:
                            n.id = "list"
                    elif isinstance(n, ast.Tuple):
                        for el in n.elts:
                            rewrite_type(el)

                rewrite_type(node.args[1])

        return node


class StringMethodFixer(ast.NodeTransformer):
    """Rewrites Python 3.9+ string methods to use global polyfills."""

    def visit_Call(self, node):
        self.generic_visit(node)

        # Look for a method call like obj.removesuffix(arg)
        if isinstance(node.func, ast.Attribute) and node.func.attr in {
            "removesuffix",
            "removeprefix",
        }:
            # Change obj.removesuffix(arg) to __removesuffix(obj, arg)
            poly_name = f"__{node.func.attr}"

            new_node = ast.Call(
                func=ast.Name(id=poly_name, ctx=ast.Load()),
                args=[node.func.value] + node.args,
                keywords=node.keywords,
            )
            return ast.copy_location(new_node, node)

        return node


class StrSubclassNewStripper(ast.NodeTransformer):
    """
    MicroPython cannot handle super().__new__(cls, val) on built-ins.
    This safely strips __new__ from any class inheriting from `str`
    (like markupsafe.Markup).
    """

    def visit_ClassDef(self, node):
        self.generic_visit(node)

        # Check if the class inherits from 'str'
        is_str_subclass = any(
            isinstance(base, ast.Name) and base.id == "str"
            for base in node.bases
        )

        if is_str_subclass:
            # Rebuild the class body, filtering out '__new__'
            node.body = [
                stmt
                for stmt in node.body
                if not (
                    isinstance(stmt, ast.FunctionDef)
                    and stmt.name == "__new__"
                )
            ]

        return node


class StringJoinFixer(ast.NodeTransformer):
    """
    MicroPython's .join() is strictly typed and prefers lists of pure strings.
    This rewrites obj.join(iterable) -> obj.join(list(map(str, iterable)))
    """

    def visit_Call(self, node):
        self.generic_visit(node)

        # Intercept any method call named 'join'
        if isinstance(node.func, ast.Attribute) and node.func.attr == "join":
            if len(node.args) == 1:
                # 1. Create the map(str, iterable) call
                map_call = ast.Call(
                    func=ast.Name(id="map", ctx=ast.Load()),
                    args=[ast.Name(id="str", ctx=ast.Load()), node.args[0]],
                    keywords=[],
                )

                # 2. Wrap it in list(...)
                list_call = ast.Call(
                    func=ast.Name(id="list", ctx=ast.Load()),
                    args=[map_call],
                    keywords=[],
                )

                # 3. Replace the original argument with our sanitized list
                node.args[0] = list_call

        return node


class HtpyValidateChildrenStripper(ast.NodeTransformer):
    """
    htpy's _validate_children() uses complex isinstance checks against
    type unions and dummy typing objects that crash MicroPython.
    This strips the validation.
    """

    def visit_FunctionDef(self, node):
        self.generic_visit(node)

        # If the function is named '_validate_children', delete its body
        if node.name == "_validate_children":
            node.body = [ast.Pass()]

        return node


class RemoveTypeHint(ast.NodeTransformer):
    # --- 1. STRIP FUNCTION ANNOTATIONS (def & async def) ---
    def _strip_function_annotations(self, node):
        # Remove return type hint: def foo() -> str:
        node.returns = None

        # Helper to wipe annotations from arguments
        def clear_args(arg_list):
            for arg in arg_list:
                arg.annotation = None

        # Clear standard, positional-only, and keyword-only args
        clear_args(node.args.posonlyargs)
        clear_args(node.args.args)
        clear_args(node.args.kwonlyargs)

        # Clear *args and **kwargs
        if node.args.vararg:
            node.args.vararg.annotation = None
        if node.args.kwarg:
            node.args.kwarg.annotation = None

        self.generic_visit(node)
        return node

    def visit_FunctionDef(self, node):
        return self._strip_function_annotations(node)

    def visit_AsyncFunctionDef(self, node):
        return self._strip_function_annotations(node)

    # --- 2. STRIP VARIABLE ANNOTATIONS (x: int = 5) ---
    def visit_AnnAssign(self, node):
        self.generic_visit(node)

        if node.value is not None:
            # If it has a value (e.g., x: int = 5), convert to standard
            # assignment (x = 5)
            new_node = ast.Assign(targets=[node.target], value=node.value)
            return ast.copy_location(new_node, node)
        else:
            # If it has no value (e.g., just `x: int`),
            # delete the line entirely
            return None


class ASTOptimizer(ast.NodeTransformer):
    """Safely eliminates dead code and assertions
    to reduce VFS size and execution time."""

    def visit_Assert(self, node):
        # Strip all 'assert' statements
        return None

    def visit_If(self, node):
        self.generic_visit(node)

        # Dead code elimination for `if False:` or `if 0:`
        if isinstance(node.test, ast.Constant) and not bool(node.test.value):
            # If there is an 'else' block, elevate it.
            # Otherwise, delete the block entirely.
            return node.orelse if node.orelse else None

        # Eliminate `if __debug__:` blocks
        # (assuming this transpiler is for production release)
        if isinstance(node.test, ast.Name) and node.test.id == "__debug__":
            return node.orelse if node.orelse else None

        return node


class LocalVariableObfuscator(ast.NodeTransformer):
    """Mangles local variables inside functions to
    make reverse-engineering difficult."""

    def visit_FunctionDef(self, node):
        # 1. Gather all variables explicitly assigned inside this function
        local_vars = set()
        for child in ast.walk(node):
            if isinstance(child, ast.Assign):
                for target in child.targets:
                    if isinstance(target, ast.Name):
                        local_vars.add(target.id)

        # 2. Identify variables that are NOT safe to rename
        # (Function arguments)
        arg_names = {
            arg.arg
            for arg in node.args.args
            + node.args.posonlyargs
            + node.args.kwonlyargs
        }
        if node.args.vararg:
            arg_names.add(node.args.vararg.arg)
        if node.args.kwarg:
            arg_names.add(node.args.kwarg.arg)

        # Exclude common built-ins or globals that
        # might accidentally get caught
        safe_to_rename = local_vars - arg_names - {"self", "cls", "super"}

        # 3. Create a scrambling mapping
        # (e.g., 'user_id' -> '_O0', 'temp_data' -> '_O1')
        mapping = {
            old_name: f"_O{i}" for i, old_name in enumerate(safe_to_rename)
        }

        # 4. Sub-transformer to actually rewrite
        # the names in the function body
        class InnerRenamer(ast.NodeTransformer):
            def visit_Name(self, n):
                if n.id in mapping:
                    n.id = mapping[n.id]
                return n

        # Apply the renaming to the function
        node = InnerRenamer().visit(node)

        # Continue traversing the tree in case of nested functions
        self.generic_visit(node)
        return node

    # Apply exactly the same logic to Async functions
    def visit_AsyncFunctionDef(self, node):
        return self.visit_FunctionDef(node)


def transpile_to_pyscript(
    source_code: str,
    filename: str = "<unknown>",
    targer_interpreter: str = "mpy",
    optimize: bool = False,
    obfuscate: bool = False,
) -> str:
    """
    Parses CPython source code and unparses it to normalize the syntax
    (fixes implicit f-string concatenations) for Pyscript
    (MicroPython or Pyodide) on the fly.

    Args:
        source_code (str): The source code to transpile.
        filename (str, optional): The filename of the source code.
            Defaults to "<unknown>".
        targer_interpreter (str, optional): The target interpreter.
            Defaults to "mpy".
        optimize (bool, optional): Whether to optimize the transpiled code.
            Defaults to False.
        obfuscate (bool, optional): Whether to obfuscate the transpiled code.
            Defaults to False.

    Returns:
        str: The transpiled code.
    """
    try:
        # CPython parses the code and resolves the implicit
        # strings automatically
        # Remove comments
        tree = ast.parse(source_code, filename=filename)
        # 1. Clean up garbage
        tree = CommentRemover().visit(tree)

        if targer_interpreter in ("mpy",):
            # 2. Fix htpy specific dictionary unpacking
            tree = DictPatcher().visit(tree)

            # 3. Unroll dataclasses BEFORE we strip the types they rely on

            tree = DataclassAheadOfTimeTranspiler().visit(tree)

            # 4. Strip modern CPython syntax MicroPython hates
            tree = PositionalOnlyArgsFixer().visit(tree)
            tree = SubscriptFixer().visit(tree)
            tree = UnionTypeFixer().visit(tree)
            tree = IsInstanceTypeFixer().visit(tree)

            tree = StringMethodFixer().visit(tree)

            tree = StrSubclassNewStripper().visit(tree)

            tree = StringJoinFixer().visit(tree)

            tree = HtpyValidateChildrenStripper().visit(tree)

            # 5. Finally, nuke all remaining type hints
            tree = RemoveTypeHint().visit(tree)

        if optimize:
            tree = ASTOptimizer().visit(tree)

        if obfuscate:
            tree = LocalVariableObfuscator().visit(tree)

        ast.fix_missing_locations(tree)

        # Re-generate the code from the syntax tree
        return ast.unparse(tree)

    except SyntaxError as error:
        # If the code is genuinely broken CPython,
        # log it so you know why it failed
        logging.error("CPython syntax error in %s: %s", filename, error)

        # Fallback to returning the raw source
        # so the browser can try to handle it
        return source_code
