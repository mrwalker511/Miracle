# User Guide: Configuring for External Projects

This guide explains how to use the Autonomous Coding Agent with your own existing projects, rather than the default sandbox workspace.

## ⚠️ Important Safety Warning

**BEFORE YOU BEGIN:**

The agent modifies files **in-place**. There is no "undo" button other than your version control system.
*   **ALWAYS** commit your changes to git before running the agent on your codebase.
*   ensure you have a clean working tree so you can easily discard changes (`git checkout .`) if the agent hallucinates or deletes code.

## 1. Using the CLI Argument (Recommended)

The easiest way to run the agent on your project is to use the `--workspace` (or `-w`) argument interactively or via command line.

**No configuration changes required.**

```bash
# Point to your project folder
python -m src.main run --workspace "C:/Users/Matt Walker/Desktop/TargetProject"
```

## 2. Default Configuration (Optional)

If you prefer to set a permanent default so you don't have to type the path every time:

1.  Open `config/settings.yaml`.
2.  Locate the `sandbox` section.
3.  Change `workspace_root` to the **absolute path** of your target project.

**Example `config/settings.yaml`:**

```yaml
sandbox:
  engine: "docker"
  # CHANGE THIS PATH to your project's root directory
  workspace_root: "C:/Users/Matt Walker/Desktop/TargetProject" 
```

> [!NOTE]
> The `--workspace` CLI argument always overrides this setting.

## 2. Docker Permissions (Windows/Mac)

If you are using Docker Desktop on Windows or Mac, you may need to allow file sharing for the directory where your project lives.
*   **Docker Desktop Settings** -> **Resources** -> **File Sharing**
*   Add the path to your project folder if it's not already covered.

## 3. Running the Agent

Once configured, run the agent as usual. It will now operate on your specified folder.

### Interactive Mode
```bash
python -m src.main run
```

### Command Line Mode
Pass your task directly. Be specific about filenames if possible to help the agent orient itself.

```bash
# Example: Adding a feature to an existing Flask app
python -m src.main run --task "Add a new route /health in app.py that returns status 200"

# Example: Fixing a bug
python -m src.main run --task "Fix the TypeError in src/utils/calculator.py line 45"
```

## 4. Tips for Existing Codebases

*   **"List Files" First**: When the agent starts, it might not know the layout. A good first prompt in interactive mode is "Explore the file structure", but the agent usually does this partially on its own.
*   **Be Specific**: The agent searches for files, but giving it the exact path in the prompt (e.g., `src/components/Button.tsx`) saves time and tokens.
*   **Context**: If your project is large, the agent won't read every file. It relies on vector search and your instructions. If a task depends on a specific library wrapper you wrote, mention it: "Use the database wrapper in `lib/db.js`".
