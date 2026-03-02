import ast
import os

PROJECT_ROOT = "."

SAFE_FUNCS = {"url_for", "redirect_back"}  # اعتبرها آمنة
DANGEROUS_ATTRS = {
    ("request", "referrer"),
}
DANGEROUS_CALLS = {
    ("request", "args", "get"),
    ("request", "form", "get"),
}

def get_attr_chain(node):
    """Return attribute chain as tuple, e.g. request.args.get -> ('request','args','get')"""
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return tuple(reversed(parts))
    return None

def is_call_name(node, names):
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in names

def is_call_attr(node, chain_set):
    if not isinstance(node, ast.Call):
        return False
    chain = get_attr_chain(node.func)
    return chain in chain_set

def is_attr(node, chain_set):
    chain = get_attr_chain(node)
    return chain in chain_set

class RedirectScanner(ast.NodeVisitor):
    def __init__(self, filename, lines):
        self.filename = filename
        self.lines = lines
        self.findings = []
        self.assignments = {}  # var -> (risk, lineno, reason)

    def visit_FunctionDef(self, node):
        # reset per function scope (simpler + less noise)
        old_assign = self.assignments
        self.assignments = {}
        self.generic_visit(node)
        self.assignments = old_assign

    def visit_Assign(self, node):
        # Track simple assignments: x = request.args.get(...), x = request.referrer
        try:
            value = node.value
            risk = None
            reason = None

            if is_call_attr(value, DANGEROUS_CALLS):
                risk = "HIGH"
                reason = "assigned from request.args.get / request.form.get"
            elif is_attr(value, DANGEROUS_ATTRS):
                risk = "HIGH"
                reason = "assigned from request.referrer"

            if risk:
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        self.assignments[t.id] = (risk, node.lineno, reason)
        except Exception:
            pass

        self.generic_visit(node)

    def visit_Call(self, node):
        # Detect redirect(...)
        if isinstance(node.func, ast.Name) and node.func.id == "redirect" and node.args:
            arg = node.args[0]
            risk, reason = self.classify_target(arg)
            self.findings.append((risk, node.lineno, reason))
        self.generic_visit(node)

    def classify_target(self, arg):
        # SAFE patterns
        if is_call_name(arg, SAFE_FUNCS):
            return "SAFE", "redirect to internal helper/url_for"

        # redirect(url_for(...)) safe
        if is_call_name(arg, {"url_for"}):
            return "SAFE", "redirect(url_for(...))"

        # HIGH patterns
        if is_call_attr(arg, DANGEROUS_CALLS):
            return "HIGH", "redirect uses direct request.args/form.get"
        if is_attr(arg, DANGEROUS_ATTRS):
            return "HIGH", "redirect uses request.referrer"

        # redirect("/path") likely safe
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            s = arg.value.strip()
            if s.startswith("/") and not s.startswith("//"):
                return "SAFE", "redirect to absolute internal path string"
            return "MEDIUM", "redirect to constant string (check if external)"

        # redirect(variable) => try resolve
        if isinstance(arg, ast.Name):
            info = self.assignments.get(arg.id)
            if info:
                return info[0], f"redirect({arg.id}) {info[2]} at line {info[1]}"
            return "MEDIUM", f"redirect({arg.id}) variable not resolved (review manually)"

        # default
        return "MEDIUM", "redirect target is complex expression (review manually)"

def scan_file(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        src = f.read()
    lines = src.splitlines()
    try:
        tree = ast.parse(src, filename=path)
    except SyntaxError:
        return []

    scanner = RedirectScanner(path, lines)
    scanner.visit(tree)
    return scanner.findings

def main():
    print("\n🔍 Scanning project (AST) for potential Open Redirect vulnerabilities...\n")
    total = 0
    for root, _, files in os.walk(PROJECT_ROOT):
        for fn in files:
            if fn.endswith(".py"):
                path = os.path.join(root, fn)
                findings = scan_file(path)
                for risk, lineno, reason in findings:
                    total += 1
                    print(f"{'❗' if risk=='HIGH' else '⚠️' if risk=='MEDIUM' else '✅'} {risk} in {path}:{lineno}")
                    print(f"    → {reason}\n")
    print(f"Done. Findings: {total}\n")

if __name__ == "__main__":
    main()
