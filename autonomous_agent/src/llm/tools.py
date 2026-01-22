"""Tool definitions for LLM function calling."""

from typing import List, Dict, Any


def get_coding_tools() -> List[Dict[str, Any]]:
    """Get tool definitions for the coding agent.

    Returns:
        List of tool definition dictionaries
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "create_file",
                "description": "Create a new file with the specified content",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "File path relative to workspace (e.g., 'app.py', 'src/utils.py')"
                        },
                        "content": {
                            "type": "string",
                            "description": "Complete file content"
                        }
                    },
                    "required": ["path", "content"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read the contents of a file",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "File path relative to workspace"
                        }
                    },
                    "required": ["path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "list_files",
                "description": "List all files in the workspace",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
    ]


def get_testing_tools() -> List[Dict[str, Any]]:
    """Get tool definitions for the testing agent.

    Returns:
        List of tool definition dictionaries
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "create_test_file",
                "description": "Create a test file for the appropriate runtime",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Test file path (e.g., 'test_app.py', 'test/app.test.js')"
                        },
                        "content": {
                            "type": "string",
                            "description": "Complete test file content with proper assertions for the runtime"
                        }
                    },
                    "required": ["path", "content"]
                }
            }
        }
    ]
