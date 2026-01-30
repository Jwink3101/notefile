"""
Restricted, AST-based evaluator for notefile queries.

Safety approach / threat model:
- Do not use eval/exec. Parse with `ast` and interpret a tiny, explicit subset.
- Allow only known-safe operations and whitelisted call targets.
- Deny attribute access on arbitrary objects; allow only on safe modules/str/dict.
- Block private names/attributes and `**kwargs` to reduce dynamic behavior.

Threat vectors considered:
- Arbitrary code execution (imports, exec/eval, attribute traversal to __*__).
- Filesystem/network access via module imports or object attributes.
- Escaping via dunder attributes or function globals.

Threat vectors not fully mitigated:
- Resource exhaustion (e.g., expensive regex, large comprehensions).
- Logic bombs / slow expressions (no timeouts or CPU limits).
- Regex catastrophic backtracking (use carefully; inputs may be large).

Supported (safe_query):
- Literals, names, lists/tuples/sets/dicts
- Boolean ops (and/or), unary ops (not, +/-), comparisons (incl. in)
- Subscripts and slices
- If-expressions (x if cond else y)
- Comprehensions (list/set/dict/generator)
- Function calls to an explicit allowlist and safe builtins
- Attribute access only on allowed modules, safe string methods, and safe dict methods

Not supported:
- Imports, lambdas, class/def, attribute access on arbitrary objects
- Private names/attributes, **kwargs, or other dynamic execution features

Future extensions (guarded):
- More whitelisted helpers (e.g., basename/dirname, contains_any).
- Optional resource limits (timeouts, regex limits).
- Additional safe container methods if needed.
"""

import ast
import types
import operator


class SafeEvalError(ValueError):
    pass


_BOOL_OPS = {
    ast.And: all,
    ast.Or: any,
}

_UNARY_OPS = {
    ast.Not: operator.not_,
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.BitOr: operator.or_,
    ast.BitAnd: operator.and_,
    ast.BitXor: operator.xor,
    ast.LShift: operator.lshift,
    ast.RShift: operator.rshift,
}

_CMP_OPS = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.In: lambda a, b: a in b,
    ast.NotIn: lambda a, b: a not in b,
    ast.Is: operator.is_,
    ast.IsNot: operator.is_not,
}

_SAFE_BUILTINS = {
    "True": True,
    "False": False,
    "None": None,
    "any": any,
    "all": all,
    "len": len,
    "set": set,
    "list": list,
    "tuple": tuple,
    "sorted": sorted,
    "min": min,
    "max": max,
    "sum": sum,
}

# String methods that are considered safe for querying. Keep this list tight and
# expand deliberately (avoid anything that can access the filesystem or modules).
_SAFE_STR_ATTRS = {
    "lower",
    "upper",
    "casefold",
    "strip",
    "lstrip",
    "rstrip",
    "startswith",
    "endswith",
    "split",
    "rsplit",
    "splitlines",
    "replace",
    "find",
    "count",
    "title",
    "capitalize",
    "swapcase",
    "removeprefix",
    "removesuffix",
    "join",
}

# Dict methods that are considered safe for querying.
_SAFE_DICT_ATTRS = {
    "get",
    "keys",
    "values",
    "items",
    "copy",
}


class SafeEvaluator:
    def __init__(self, names, allowed_callables=None, allowed_modules=None):
        self._names = names if names is not None else {}
        self._allowed_callables = set(allowed_callables or [])
        self._allowed_modules = set(allowed_modules or [])
        self._allowed_module_names = {m.__name__ for m in self._allowed_modules}
        self._lines = []

    def eval(self, code):
        """
        Evaluate a restricted query string and return the last expression value.

        Raises SafeEvalError on syntax errors or unsupported constructs.
        """
        try:
            tree = ast.parse(code, mode="exec")
        except SyntaxError as exc:
            raise SafeEvalError(str(exc))

        self._lines = code.splitlines() or [code]

        if not tree.body:
            raise SafeEvalError("Empty query")

        if not isinstance(tree.body[-1], ast.Expr):
            raise SafeEvalError("Last line must be an expression")

        last_value = None
        for stmt in tree.body:
            if isinstance(stmt, ast.Expr):
                last_value = self._eval_expr(stmt.value, {})
            elif isinstance(stmt, ast.Assign):
                value = self._eval_expr(stmt.value, {})
                for target in stmt.targets:
                    self._assign_target(target, value)
                last_value = value
            else:
                self._raise(stmt, "Unsupported statement")

        return last_value

    def _assign_target(self, target, value):
        if isinstance(target, ast.Name):
            self._names[target.id] = value
            return
        if isinstance(target, (ast.Tuple, ast.List)):
            if not isinstance(value, (tuple, list)):
                self._raise(target, "Can only unpack tuple/list")
            if len(target.elts) != len(value):
                self._raise(target, "Unpack length mismatch")
            for t, v in zip(target.elts, value):
                self._assign_target(t, v)
            return
        self._raise(target, "Unsupported assignment target")

    def _eval_expr(self, node, local_vars):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            if node.id in local_vars:
                return local_vars[node.id]
            if node.id in self._names:
                return self._names[node.id]
            if node.id in _SAFE_BUILTINS:
                return _SAFE_BUILTINS[node.id]
            self._raise(node, f"Unknown name: {node.id}")
        if isinstance(node, ast.List):
            return [self._eval_expr(e, local_vars) for e in node.elts]
        if isinstance(node, ast.Tuple):
            return tuple(self._eval_expr(e, local_vars) for e in node.elts)
        if isinstance(node, ast.Set):
            return {self._eval_expr(e, local_vars) for e in node.elts}
        if isinstance(node, ast.Dict):
            return {
                self._eval_expr(k, local_vars): self._eval_expr(v, local_vars)
                for k, v in zip(node.keys, node.values)
            }
        if isinstance(node, ast.UnaryOp):
            op = _UNARY_OPS.get(type(node.op))
            if not op:
                self._raise(node, "Unsupported unary operator")
            return op(self._eval_expr(node.operand, local_vars))
        if isinstance(node, ast.BinOp):
            op = _BIN_OPS.get(type(node.op))
            if not op:
                self._raise(node, "Unsupported binary operator")
            return op(
                self._eval_expr(node.left, local_vars),
                self._eval_expr(node.right, local_vars),
            )
        if isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                for value in node.values:
                    if not self._eval_expr(value, local_vars):
                        return False
                return True
            if isinstance(node.op, ast.Or):
                for value in node.values:
                    if self._eval_expr(value, local_vars):
                        return True
                return False
            self._raise(node, "Unsupported boolean operator")
        if isinstance(node, ast.Compare):
            left = self._eval_expr(node.left, local_vars)
            for op_node, comparator in zip(node.ops, node.comparators):
                op = _CMP_OPS.get(type(op_node))
                if not op:
                    self._raise(node, "Unsupported comparison operator")
                right = self._eval_expr(comparator, local_vars)
                if not op(left, right):
                    return False
                left = right
            return True
        if isinstance(node, ast.IfExp):
            return (
                self._eval_expr(node.body, local_vars)
                if self._eval_expr(node.test, local_vars)
                else self._eval_expr(node.orelse, local_vars)
            )
        if isinstance(node, ast.Subscript):
            value = self._eval_expr(node.value, local_vars)
            slice_val = self._eval_slice(node.slice, local_vars)
            return value[slice_val]
        if isinstance(node, ast.Call):
            return self._eval_call(node, local_vars)
        if isinstance(node, ast.Attribute):
            return self._eval_attribute(node, local_vars)
        if isinstance(node, ast.GeneratorExp):
            return self._eval_generator(node, local_vars)
        if isinstance(node, ast.ListComp):
            return list(self._eval_generator(node, local_vars))
        if isinstance(node, ast.SetComp):
            return set(self._eval_generator(node, local_vars))
        if isinstance(node, ast.DictComp):
            return self._eval_dictcomp(node, local_vars)

        self._raise(node, "Unsupported expression")

    def _eval_slice(self, node, local_vars):
        if isinstance(node, ast.Slice):
            return slice(
                self._eval_expr(node.lower, local_vars) if node.lower else None,
                self._eval_expr(node.upper, local_vars) if node.upper else None,
                self._eval_expr(node.step, local_vars) if node.step else None,
            )
        return self._eval_expr(node, local_vars)

    def _eval_call(self, node, local_vars):
        func = None
        if isinstance(node.func, ast.Name):
            func = self._eval_expr(node.func, local_vars)
            if func not in self._allowed_callables and node.func.id not in _SAFE_BUILTINS:
                self._raise(node, f"Call not allowed: {node.func.id}")
        elif isinstance(node.func, ast.Attribute):
            # Only allow calls on whitelisted modules, strings, or dicts.
            value = self._eval_expr(node.func.value, local_vars)
            attr = node.func.attr
            if attr.startswith("_"):
                self._raise(node, "Private attribute access is not allowed")
            if isinstance(value, types.ModuleType) and value in self._allowed_modules:
                func = getattr(value, attr)
                if not self._callable_from_allowed_module(func):
                    self._raise(node, "Call not allowed")
            elif isinstance(value, str):
                if attr not in _SAFE_STR_ATTRS:
                    self._raise(node, "Attribute access is restricted")
                func = getattr(value, attr)
            elif isinstance(value, dict):
                if attr not in _SAFE_DICT_ATTRS:
                    self._raise(node, "Attribute access is restricted")
                func = getattr(value, attr)
            else:
                self._raise(node, "Attribute access is restricted")
        else:
            self._raise(node, "Unsupported call target")

        args = [self._eval_expr(a, local_vars) for a in node.args]
        kwargs = {}
        for kw in node.keywords:
            if kw.arg is None:
                self._raise(node, "**kwargs is not allowed")
            kwargs[kw.arg] = self._eval_expr(kw.value, local_vars)
        return func(*args, **kwargs)

    def _eval_attribute(self, node, local_vars):
        value = self._eval_expr(node.value, local_vars)
        if node.attr.startswith("_"):
            self._raise(node, "Private attribute access is not allowed")
        if isinstance(value, types.ModuleType) and value in self._allowed_modules:
            return getattr(value, node.attr)
        if isinstance(value, str):
            if node.attr not in _SAFE_STR_ATTRS:
                self._raise(node, "Attribute access is restricted")
            return getattr(value, node.attr)
        if isinstance(value, dict):
            if node.attr not in _SAFE_DICT_ATTRS:
                self._raise(node, "Attribute access is restricted")
            return getattr(value, node.attr)
        self._raise(node, "Attribute access is restricted")

    def _eval_generator(self, node, local_vars):
        def generator():
            for scope in self._comprehension_scopes(node.generators, dict(local_vars)):
                yield self._eval_expr(node.elt, scope)

        return generator()

    def _eval_dictcomp(self, node, local_vars):
        result = {}
        for scope in self._comprehension_scopes(node.generators, dict(local_vars)):
            key = self._eval_expr(node.key, scope)
            value = self._eval_expr(node.value, scope)
            result[key] = value
        return result

    def _comprehension_scopes(self, generators, local_vars):
        if not generators:
            yield local_vars
            return

        gen = generators[0]
        iterable = self._eval_expr(gen.iter, local_vars)
        for item in iterable:
            scope = dict(local_vars)
            self._assign_comprehension_target(gen.target, item, scope)
            if all(self._eval_expr(cond, scope) for cond in gen.ifs):
                yield from self._comprehension_scopes(generators[1:], scope)

    def _assign_comprehension_target(self, target, value, scope):
        if isinstance(target, ast.Name):
            scope[target.id] = value
            return
        if isinstance(target, (ast.Tuple, ast.List)):
            if not isinstance(value, (tuple, list)):
                self._raise(target, "Can only unpack tuple/list in comprehension")
            if len(target.elts) != len(value):
                self._raise(target, "Comprehension unpack length mismatch")
            for t, v in zip(target.elts, value):
                self._assign_comprehension_target(t, v, scope)
            return
        self._raise(target, "Unsupported comprehension target")

    def _callable_from_allowed_module(self, func):
        mod = getattr(func, "__module__", None)
        name = getattr(func, "__name__", "")
        if not mod or not name:
            return False
        if name.startswith("_"):
            return False
        return mod in self._allowed_module_names

    def _raise(self, node, message):
        lineno = getattr(node, "lineno", 1)
        line = self._lines[lineno - 1].strip() if self._lines else ""
        raise SafeEvalError(f"Line {lineno} `{line}`: {message}")


def safe_eval(code, names, allowed_callables=None, allowed_modules=None):
    """
    Convenience wrapper around SafeEvaluator.eval().

    `names` is the evaluation namespace. Only functions in `allowed_callables`
    and modules in `allowed_modules` can be called/accessed.
    """
    evaluator = SafeEvaluator(
        names, allowed_callables=allowed_callables, allowed_modules=allowed_modules
    )
    return evaluator.eval(code)
