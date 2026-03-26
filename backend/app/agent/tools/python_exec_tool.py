"""
Python Execution Tool - Executes Python code in a restricted environment.
"""
from typing import Any, Dict
import sys
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr

from app.agent.tools.base_tool import BaseTool
from app.models.permission import PermissionContext
from app.models.tool import ToolResult


class PythonExecTool(BaseTool):
    """
    Tool for executing Python code with restricted capabilities.
    """

    @property
    def name(self) -> str:
        return "python_exec"

    @property
    def description(self) -> str:
        return "Execute Python code for mathematical calculations and data processing. Use this for arithmetic operations, statistical analysis, and data transformations."

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute. The result should be assigned to a variable named 'result'.",
                },
                "context": {
                    "type": "object",
                    "description": "Variables to inject into execution context (optional)",
                },
            },
            "required": ["code"],
        }

    async def execute(
        self,
        params: Dict[str, Any],
        permission: PermissionContext,
    ) -> ToolResult:
        """
        Execute Python code in a restricted environment.

        Args:
            params: Dict with 'code' and optional 'context'
            permission: Permission context (unused for python_exec)

        Returns:
            ToolResult with execution result
        """
        try:
            self.validate_params(params)

            code = params.get("code", "")
            context = params.get("context", {})

            # Create execution namespace
            exec_globals = {
                "__builtins__": {
                    "abs": abs,
                    "round": round,
                    "sum": sum,
                    "len": len,
                    "min": min,
                    "max": max,
                    "sorted": sorted,
                    "enumerate": enumerate,
                    "zip": zip,
                    "map": map,
                    "filter": filter,
                    "list": list,
                    "dict": dict,
                    "set": set,
                    "tuple": tuple,
                    "str": str,
                    "int": int,
                    "float": float,
                    "bool": bool,
                    "range": range,
                    "print": print,
                }
            }
            exec_locals = {**context}

            # Capture stdout/stderr
            stdout_capture = StringIO()
            stderr_capture = StringIO()

            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                exec(code, exec_globals, exec_locals)

            # Extract result
            result = exec_locals.get("result")
            stdout_text = stdout_capture.getvalue()
            stderr_text = stderr_capture.getvalue()

            return self._success(
                data={
                    "result": result,
                    "stdout": stdout_text,
                    "stderr": stderr_text,
                },
                metadata={"code_length": len(code)},
            )

        except SyntaxError as e:
            return self._error(f"Syntax error: {str(e)}")
        except NameError as e:
            return self._error(f"Name error: {str(e)}")
        except Exception as e:
            return self._error(f"Execution failed: {str(e)}")


# Global instance
_python_exec_tool: PythonExecTool = PythonExecTool()


def get_python_exec_tool() -> PythonExecTool:
    """Get Python execution tool instance."""
    return _python_exec_tool
