"""
代码执行沙箱 — 安全地在子进程中执行 AI 生成的 Python 代码
捕获 stdout/stderr 和 matplotlib 图表为 base64
"""
import sys
import os
import json
import base64
import subprocess
import tempfile
import logging
from pathlib import Path

log = logging.getLogger("Sandbox")

EXECUTION_WRAPPER = '''
import sys, io, os, base64, json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ---- 加载数据文件 ----
DATA_FILE = r"{data_file_path}"
df = None
if DATA_FILE and os.path.exists(DATA_FILE):
    ext = os.path.splitext(DATA_FILE)[1].lower()
    try:
        if ext in (".xlsx", ".xls"):
            df = pd.read_excel(DATA_FILE)
        elif ext == ".csv":
            df = pd.read_csv(DATA_FILE)
        elif ext == ".txt":
            df = pd.read_csv(DATA_FILE, sep="\\t")
    except Exception as e:
        print(f"[DATA_LOAD_ERROR] {{e}}", file=sys.stderr)

# ---- Monkeypatch plt.show ----
_orig_show = plt.show
plt.show = lambda *a, **kw: None

# ---- 执行用户代码 ----
_user_stdout = io.StringIO()
_user_stderr = io.StringIO()
_orig_stdout = sys.stdout
_orig_stderr = sys.stderr

try:
    sys.stdout = _user_stdout
{user_code}
finally:
    sys.stdout = _orig_stdout
    sys.stderr = _orig_stderr

# ---- 收集所有图表 ----
_figures = []
for _i in plt.get_fignums():
    _fig = plt.figure(_i)
    if _fig.get_axes():
        _buf = io.BytesIO()
        _fig.savefig(_buf, format="png", dpi=300)
        _buf.seek(0)
        _figures.append(base64.b64encode(_buf.read()).decode("utf-8"))
        plt.close(_fig)

# ---- 输出结果 ----
print(_user_stdout.getvalue(), end="")
print("__CHARTS_BEGIN__")
print(json.dumps(_figures))
print("__CHARTS_END__")
if _user_stderr.getvalue():
    print(_user_stderr.getvalue(), file=sys.stderr)
'''


def execute_code(code: str, data_file_path: str = "", timeout: int = 30) -> dict:
    """
    在子进程中安全执行 Python 代码。

    Args:
        code: 用户/AI 生成的 Python 代码
        data_file_path: 数据文件路径，代码中可通过 df 变量访问
        timeout: 超时秒数，默认 30

    Returns:
        {
            "success": bool,
            "stdout": str,
            "stderr": str,
            "charts": [{"chart_id":"chart_0","title":"图表 1","base64":"data:image/png;base64,...","description":""}],
            "error": str,
            "exit_code": int,
        }
    """
    log.info(f"[Sandbox] executing code ({len(code)} chars), timeout={timeout}s")

    # 确保 data_file_path 存在（转为绝对路径，正斜杠）
    safe_data_path = ""
    if data_file_path:
        abs_path = os.path.abspath(data_file_path)
        if os.path.isfile(abs_path):
            safe_data_path = abs_path.replace("\\", "/")

    # 用户代码缩进 4 空格（在 try: 块内）
    indented_code = "\n".join("    " + line if line.strip() else ""
                              for line in code.split("\n"))

    wrapper = EXECUTION_WRAPPER.format(
        data_file_path=safe_data_path,
        user_code=indented_code,
    )

    # 写入临时脚本
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", prefix="sandbox_", delete=False, encoding="utf-8"
    ) as f:
        f.write(wrapper)
        script_path = f.name

    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True, text=True, timeout=timeout,
            cwd=os.path.dirname(script_path) or ".",
        )
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "stdout": "",
            "stderr": "",
            "charts": [],
            "error": f"代码执行超时 (>{timeout}s)，请优化代码或增加超时时间",
            "exit_code": -1,
        }
    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": str(e),
            "charts": [],
            "error": f"代码执行异常: {e}",
            "exit_code": -1,
        }
    finally:
        # 清理临时脚本
        try:
            os.unlink(script_path)
        except OSError:
            pass

    stdout_raw = result.stdout or ""
    stderr_raw = result.stderr or ""

    # 解析图表标记
    charts = []
    stdout_clean = stdout_raw
    if "__CHARTS_BEGIN__" in stdout_raw:
        parts = stdout_raw.split("__CHARTS_BEGIN__")
        stdout_clean = parts[0].strip()
        charts_part = parts[1].split("__CHARTS_END__")[0].strip() if len(parts) > 1 else ""
        try:
            chart_b64_list = json.loads(charts_part)
            charts = [
                {
                    "chart_id": f"chart_{i}",
                    "title": f"图表 {i + 1}",
                    "base64": f"data:image/png;base64,{b64}",
                    "description": "",
                }
                for i, b64 in enumerate(chart_b64_list)
            ]
        except (json.JSONDecodeError, ValueError) as e:
            log.warning(f"[Sandbox] failed to parse charts JSON: {e}")

    exit_code = result.returncode
    success = exit_code == 0

    log.info(f"[Sandbox] done: success={success}, charts={len(charts)}, exit={exit_code}")

    return {
        "success": success,
        "stdout": stdout_clean,
        "stderr": stderr_raw,
        "charts": charts,
        "error": stderr_raw if not success and not stderr_raw else "",
        "exit_code": exit_code,
    }
