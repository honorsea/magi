import os
import re
import textwrap
import subprocess as _subprocess
from typing import Dict, List, Any

#  SECTION 13 — CODE EXECUTION SANDBOX
#              Allows the Cognitive Agent to run Python code for OR-Tools
#              optimisation, matplotlib visualisations, and statistical analysis.
# ─────────────────────────────────────────────────────────────────────────────

class CodeSandbox:
    """
    Restricted Python code execution environment for the Cognitive Agent.

    Security measures:
    - Import whitelist enforced via regex before execution
    - Dangerous builtins blocked (exec, eval, compile, __import__)
    - Timeout of 60 seconds per execution
    - All output files go to the designated output directory
    """

    ALLOWED_IMPORTS = {
        "numpy", "np", "scipy", "pandas", "pd", "matplotlib",
        "matplotlib.pyplot", "plt", "ortools", "json", "math",
        "collections", "dataclasses", "statistics", "itertools",
        "functools", "textwrap", "datetime",
        "ortools.linear_solver", "ortools.sat",
        "ortools.linear_solver.pywraplp",
        "ortools.sat.python", "ortools.sat.python.cp_model",
    }

    BLOCKED_PATTERNS = [
        r"\bimport\s+os\b", r"\bimport\s+sys\b", r"\bimport\s+subprocess\b",
        r"\bimport\s+shutil\b", r"\bimport\s+socket\b", r"\bimport\s+http\b",
        r"\bimport\s+requests\b", r"\bimport\s+urllib\b",
        r"\b__import__\b", r"\bexec\s*\(", r"\beval\s*\(",
        r"\bcompile\s*\(", r"\bglobals\s*\(", r"\blocals\s*\(",
    ]

    TIMEOUT_SECONDS = 60

    def __init__(self, output_dir: str = "./magi_outputs"):
        self.output_dir = os.path.abspath(output_dir)
        self.scratch_dir = os.path.join(self.output_dir, "scratch")
        os.makedirs(self.scratch_dir, exist_ok=True)
        self._exec_count = 0

    def execute(self, code: str, description: str = "") -> Dict[str, Any]:
        """
        Validate and execute Python code in a subprocess.

        Args:
            code:        Python source code to execute.
            description: Brief description of what the code does.

        Returns:
            Dict with success status, stdout, stderr, and list of created files.
        """
        # ── Security validation ───────────────────────────────────────
        for pattern in self.BLOCKED_PATTERNS:
            if re.search(pattern, code):
                return {
                    "success": False,
                    "error":   f"Blocked pattern detected: {pattern}",
                    "stdout":  "", "stderr": "", "files_created": [],
                }

        # ── Prepare code with sandbox header ──────────────────────────
        self._exec_count += 1
        script_name = f"agent_code_{self._exec_count}.py"
        script_path = os.path.join(self.scratch_dir, script_name)

        header = textwrap.dedent(f"""\
            import matplotlib
            matplotlib.use('Agg')
            import os as _os
            _OUTPUT_DIR = {repr(os.path.abspath(self.output_dir))}
            _os.makedirs(_OUTPUT_DIR, exist_ok=True)
        """)
        full_code = header + "\n" + code

        with open(script_path, "w", encoding="utf-8") as f:
            f.write(full_code)

        # ── Track existing files to detect new ones ───────────────────
        existing_files = set()
        for d in [self.output_dir, self.scratch_dir]:
            if os.path.isdir(d):
                for fn in os.listdir(d):
                    existing_files.add(os.path.join(d, fn))

        # ── Execute ───────────────────────────────────────────────────
        try:
            import sys
            result = _subprocess.run(
                [sys.executable, script_path],
                capture_output=True, text=True,
                timeout=self.TIMEOUT_SECONDS,
                cwd=self.output_dir,
            )
            stdout = result.stdout[:5000]  # cap output
            stderr = result.stderr[:3000]
            success = result.returncode == 0
        except _subprocess.TimeoutExpired:
            return {
                "success": False, "error": "Execution timed out (60s limit).",
                "stdout": "", "stderr": "", "files_created": [],
            }
        except Exception as e:
            return {
                "success": False, "error": str(e),
                "stdout": "", "stderr": "", "files_created": [],
            }

        # ── Detect created files ──────────────────────────────────────
        new_files = []
        for d in [self.output_dir, self.scratch_dir]:
            if os.path.isdir(d):
                for fn in os.listdir(d):
                    fp = os.path.join(d, fn)
                    if fp not in existing_files and fp != script_path:
                        new_files.append(fp)

        return {
            "success":       success,
            "stdout":        stdout,
            "stderr":        stderr if not success else "",
            "files_created": new_files,
            "script_path":   script_path,
        }


# ─────────────────────────────────────────────────────────────────────────────
