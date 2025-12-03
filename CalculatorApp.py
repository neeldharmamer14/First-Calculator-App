python
# streamlit_calculator.py
# Simple Calculator Streamlit app (single-file). Drop this on GitHub and deploy to
# https://share.streamlit.io/<username>/<repo>/main/streamlit_calculator.py
#
# Features:
# - Safe expression evaluation (using ast) with math functions
# - Buttons for common operations
# - History preserved in Streamlit session_state
# - Clear history / copy last result
#
# Run locally with: streamlit run streamlit_calculator.py

import ast
import math
import operator as op
import streamlit as st

# -------------------------
# Safe evaluator (AST-based)
# -------------------------
# Whitelisted operators and functions
_OPERATORS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Pow: op.pow,
    ast.Mod: op.mod,
    ast.FloorDiv: op.floordiv,
    ast.USub: op.neg,
    ast.UAdd: op.pos,
    ast.BitXor: op.pow,  # allow ^ as power (handled by parsing replacement)
}

_MATH_FUNCS = {
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "sqrt": math.sqrt,
    "log": math.log,       # natural log: log(x) or log(x, base)
    "log10": math.log10,
    "ln": math.log,
    "exp": math.exp,
    "abs": abs,
    "ceil": math.ceil,
    "floor": math.floor,
    "factorial": math.factorial,
}

_CONSTANTS = {
    "pi": math.pi,
    "e": math.e,
    "tau": math.tau,
    "inf": math.inf,
    "nan": math.nan,
}

_ALLOWED_NAMES = {**_MATH_FUNCS, **_CONSTANTS}

class EvalError(Exception):
    pass

def _eval_ast(node):
    """Recursively evaluate an AST node using the safe whitelist."""
    if isinstance(node, ast.Expression):
        return _eval_ast(node.body)

    if isinstance(node, ast.Num):  # Python <3.8
        return node.n
    if hasattr(ast, "Constant") and isinstance(node, ast.Constant):  # py3.8+
        if isinstance(node.value, (int, float)):
            return node.value
        raise EvalError(f"Unsupported constant type: {type(node.value).__name__}")

    if isinstance(node, ast.BinOp):
        left = _eval_ast(node.left)
        right = _eval_ast(node.right)
        op_type = type(node.op)
        if op_type in _OPERATORS:
            func = _OPERATORS[op_type]
            try:
                return func(left, right)
            except Exception as e:
                raise EvalError(str(e))
        raise EvalError(f"Unsupported binary operator: {op_type.__name__}")

    if isinstance(node, ast.UnaryOp):
        operand = _eval_ast(node.operand)
        op_type = type(node.op)
        if op_type in _OPERATORS:
            func = _OPERATORS[op_type]
            try:
                return func(operand)
            except Exception as e:
                raise EvalError(str(e))
        raise EvalError(f"Unsupported unary operator: {op_type.__name__}")

    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name):
            fname = node.func.id
            if fname not in _MATH_FUNCS:
                raise EvalError(f"Function '{fname}' not allowed")
            func = _MATH_FUNCS[fname]
            args = [_eval_ast(a) for a in node.args]
            try:
                return func(*args)
            except Exception as e:
                raise EvalError(str(e))
        raise EvalError("Only direct math function calls are allowed")

    if isinstance(node, ast.Name):
        if node.id in _CONSTANTS:
            return _CONSTANTS[node.id]
        raise EvalError(f"Name '{node.id}' is not allowed")

    if isinstance(node, ast.Tuple):
        return tuple(_eval_ast(elt) for elt in node.elts)

    raise EvalError(f"Unsupported expression: {type(node).__name__}")

def safe_eval(expr: str):
    """
    Safely evaluate a mathematical expression string and return a numeric result.
    Allowed: numbers, + - * / ** % // unary +/-, math functions listed in _MATH_FUNCS,
    constants in _CONSTANTS.
    Note: '^' is treated as power (**) for convenience.
    """
    if not expr or not expr.strip():
        raise EvalError("Empty expression")

    # Normalize: allow '^' for power, replace with '**'
    expr = expr.replace("^", "**")

    # Reject suspicious characters
    for ch in [';', '__', 'import', 'exec', 'eval', 'os.', 'sys.', 'subprocess']:
        if ch in expr:
            raise EvalError("Invalid token in expression")

    try:
        parsed = ast.parse(expr, mode="eval")
    except Exception as e:
        raise EvalError(f"Parse error: {e}")

    # Walk AST to ensure only allowed nodes are present
    for node in ast.walk(parsed):
        if isinstance(node, ast.BinOp) and type(node.op) not in _OPERATORS:
            raise EvalError(f"Operator not allowed: {type(node.op).__name__}")
        # Permit only specific node types
        if not isinstance(node, (
            ast.Expression, ast.BinOp, ast.UnaryOp, ast.Num, ast.Load,
            ast.Call, ast.Name, ast.Constant, ast.Tuple, ast.Pow, ast.Mod,
            ast.FloorDiv, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.USub, ast.UAdd,
        )):
            # Allow operator classes implicitly included above; otherwise reject
            # (Note: many operator types are subclasses; the checks above catch most)
            # If running into false positives on a Python version, extend allowed types.
            allowed = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Num, ast.Load,
                       ast.Call, ast.Name, ast.Constant, ast.Tuple)
            if not isinstance(node, allowed):
                raise EvalError(f"Disallowed AST node: {type(node).__name__}")

    return _eval_ast(parsed)

# -------------------------
# Streamlit UI
# -------------------------
st.set_page_config(page_title="Simple Calculator", layout="centered")

st.title("🧮 Simple Calculator")
st.caption("Safe expression evaluation with math functions. Deploy on share.streamlit.io by pushing this file to GitHub.")

# Initialize history in session state
if "history" not in st.session_state:
    st.session_state.history = []  # list of tuples: (expression, result or error)

col_expr, col_buttons = st.columns([3, 1])

with col_expr:
    expr = st.text_input(
        "Enter expression",
        value="",
        placeholder="e.g. 2+2, 3*sin(pi/4), sqrt(16), log(100,10), 2^8",
        key="expr_input",
    )

with col_buttons:
    st.write("")  # spacing
    st.write("")  # spacing
    if st.button("Calculate"):
        # We'll handle below outside the column to allow pressing Enter (form not used)
        pass

# Quick-operation buttons (append to expression)
ops = [
    ("+", "+"), ("-", "-"), ("×", "*"), ("÷", "/"),
    ("^", "^"), ("%", "%"), ("(", "("), (")", ")")
]
funcs = ["sin(", "cos(", "tan(", "sqrt(", "log(", "log10(", "exp(", "abs("]

op_cols = st.columns(len(ops))
for c, (label, to_append) in zip(op_cols, ops):
    if c.button(label):
        st.session_state.expr_input = st.session_state.get("expr_input", "") + to_append

func_cols = st.columns(len(funcs))
for c, label in zip(func_cols, funcs):
    if c.button(label):
        st.session_state.expr_input = st.session_state.get("expr_input", "") + label

# keyboard 'Enter' also triggers, but we handle evaluate when user clicks Calculate or presses Enter:
evaluate = st.button("Evaluate")  # duplicate main action (convenience)

if st.session_state.get("expr_input", "").strip() and (st.session_state.get("_button") or evaluate):
    # this branch won't be used because we didn't set _button; instead evaluate on below click handling
    pass

# Evaluate when user clicks either "Calculate" or "Evaluate" or presses Enter (i.e. text_input changed with key)
# Because streamlit re-runs top to bottom, detect button press via st.session_state from buttons:
# Simple approach: if either of the two buttons was pressed in this run, evaluate:
if st.button("Compute (perform evaluation)"):
    # additional compute button to ensure response on click
    pass

# To reliably capture the "Calculate" or "Evaluate" press, inspect streamlit's runtime:
# We'll evaluate if either button was clicked (clicked status returned above)
# But since the previous button() calls returned values that were not stored, re-create buttons with state:
# Simpler approach: provide an explicit "Compute" button at end and use that.
compute = st.button("Compute")

if compute:
    expression = st.session_state.get("expr_input", "").strip()
    if not expression:
        st.warning("Please enter an expression.")
    else:
        try:
            result = safe_eval(expression)
            # Format result: show ints without .0 when appropriate
            if isinstance(result, float):
                # show up to 12 significant digits to avoid long floats
                result_display = float(f"{result:.12g}")
            else:
                result_display = result
            st.success(f"{expression} = {result_display}")
            st.session_state.history.insert(0, (expression, result_display))
        except EvalError as ee:
            st.error(f"Error: {ee}")
            st.session_state.history.insert(0, (expression, f"Error: {ee}"))
        except Exception as e:
            st.error(f"Unexpected error: {e}")
            st.session_state.history.insert(0, (expression, f"Error: {e}"))

# Provide a compact evaluator that runs when user presses Enter in the text_input:
# Detect change compared to previous expression in session_state
prev_expr = st.session_state.get("_prev_expr", "")
current_expr = st.session_state.get("expr_input", "")
if current_expr != prev_expr:
    # update prev expr
    st.session_state["_prev_expr"] = current_expr
    # If the user cleared or typed a new expression, do not auto-evaluate.
    # To avoid surprising evaluations, we won't auto-evaluate on typing; user must press Compute.

# History panel
st.markdown("---")
st.subheader("History")
if st.session_state.history:
    # show last 12 entries
    for i, (e, r) in enumerate(st.session_state.history[:12], start=1):
        st.write(f"**{i}.** `{e}`  →  `{r}`")
else:
    st.write("No history yet. Evaluate an expression to see it appear here.")

# History controls
hcol1, hcol2, hcol3 = st.columns([1,1,1])
with hcol1:
    if st.button("Clear history"):
        st.session_state.history = []
with hcol2:
    if st.session_state.history:
        last_expr, last_res = st.session_state.history[0]
        if st.button("Copy last result to input"):
            # put the last result into input for further operations
            st.session_state.expr_input = str(last_res)
with hcol3:
    if st.session_state.history:
        if st.button("Copy last expression to input"):
            st.session_state.expr_input = st.session_state.history[0][0]

# Reference panel
st.markdown("---")
st.subheader("Reference / Allowed functions")
st.write(
    "You may use numbers, `+ - * / ^ % //` and parentheses. Use math functions like "
    + ", ".join(sorted(_MATH_FUNCS.keys()))
    + ". Constants: " + ", ".join(sorted(_CONSTANTS.keys()))
)
st.caption("Examples: `2+2`, `3*sin(pi/4)`, `sqrt(16)`, `log(100,10)`, `2^8`, `factorial(5)`")

# Footer small help
with st.expander("Why AST-based evaluation?"):
    st.write(
        "This app uses Python's AST (abstract syntax tree) parsing and a whitelist of "
        "safe operators and math functions to avoid executing arbitrary code. That makes "
        "it safer than using plain eval()."
    )

# Small credits
st.markdown("---")
st.write("Made with ❤️ — drop this file into a GitHub repo and use share.streamlit.io to deploy.")
```
