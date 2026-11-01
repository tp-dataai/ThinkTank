在 VS Code 里用 `uv` 管理项目，核心逻辑是把“建项目、装依赖、跑代码”这几步用 `uv` 的专属命令串起来，**甚至不需要手动去 `activate` 虚拟环境**。

### 🚀 1. 初始化项目（一切的开端）
在 VS Code 终端中，进入你存放代码的文件夹，运行：
```bash
uv init
```
这会在当前目录生成一个标准的 Python 项目结构，核心是自动创建 **`pyproject.toml`**（项目配置和依赖清单）和 **`README.md`** 等文件。如果只想生成配置文件而不创建示例代码，可以用 `uv init --bare`。

### 📦 2. 创建虚拟环境（其实它自己会做）
其实，**你不需要手动敲 `uv venv`**。
当你第一次执行 `uv add` 或 `uv run` 等操作时，`uv` 会自动在项目根目录下创建一个名为 **`.venv`** 的虚拟环境，并生成 **`uv.lock`** 锁文件。如果你有特殊需求（比如指定 Python 版本或内置 `pip`），才需要手动创建：
*   **创建默认环境**：`uv venv`
*   **指定 Python 版本**：`uv venv --python 3.12`
*   **创建带 `pip` 的环境**：`uv venv --seed`

### ⬇️ 3. 安装、同步和移除依赖
不要用 `pip install`，`uv` 有自己更高效的方式：
*   **添加依赖**：`uv add requests`（会自动更新 `pyproject.toml` 并安装到环境）
*   **添加开发依赖**：`uv add --dev pytest`
*   **同步依赖**：`uv sync`。这是**团队协作或克隆项目后的关键一步**，它会根据 `uv.lock` 精确安装所有依赖，确保环境一致。
*   **移除依赖**：`uv remove requests`
*   **导入 `requirements.txt`**：`uv add -r requirements.txt`

### ▶️ 4. 运行代码（无需手动激活）
这是 `uv` 最爽的地方：**你不需要手动激活 `.venv`**。直接用 `uv run`，它会自动在项目的虚拟环境里执行命令，并确保环境是最新的：
```bash
# 运行脚本
uv run python your_script.py

# 运行测试
uv run pytest
```

### ⚙️ 5. 在 VS Code 中正确选择解释器
虽然 `uv` 在终端里会自动处理，但为了让 VS Code 的**代码提示、调试和 Jupyter Notebook** 正常工作，必须手动选一下解释器：
1. 按下 `Ctrl + Shift + P`（Mac 是 `Cmd + Shift + P`）。
2. 输入并选择 **`Python: Select Interpreter`**。
3. 在列表中选择由 `uv` 创建的 `.venv` 路径。

---

### 💡 常用命令速查表
| 操作 | 命令 |
| :--- | :--- |
| 初始化项目 | `uv init` |
| 添加依赖 | `uv add <包名>` |
| 同步环境（克隆项目后必做） | `uv sync` |
| 运行代码 | `uv run <脚本名>.py` |
| 移除依赖 | `uv remove <包名>` |
| 查看已装包（代替 `pip list`） | `uv pip list` |

如果你在选好解释器后，VS Code 的终端还是没有自动激活环境，可以手动执行一次 `.\.venv\Scripts\Activate.ps1`（Windows PowerShell）。