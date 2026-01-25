"""Workspace scaffolding for different runtimes.

The agent can generate code from scratch, but providing a minimal project scaffold
reduces friction (e.g. Node projects need a package.json and an obvious test
command).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from src.ui.logger import get_logger


SCAFFOLD_MARKER = ".agent_scaffold.json"

# Language to file extension mapping
LANGUAGE_EXTENSIONS = {
    "python": ".py",
    "node": ".js",
    "javascript": ".js",
    "js": ".js",
    "java": ".java",
    "csharp": ".cs",
    "c#": ".cs",
    "go": ".go",
    "golang": ".go",
    "rust": ".rs",
    "ruby": ".rb",
    "php": ".php",
    "swift": ".swift",
    "kotlin": ".kt",
    "elixir": ".ex",
    "typescript": ".ts",
    "ts": ".ts",
}

# Project type to directory structure mapping
PROJECT_STRUCTURES = {
    "general": {"src": [], "test": []},
    "web_app": {"src": [], "public": [], "test": [], "config": []},
    "mobile_app": {"src": [], "assets": [], "test": [], "lib": []},
    "desktop_app": {"src": [], "ui": [], "test": [], "assets": []},
    "api": {"src": [], "routes": [], "models": [], "test": [], "config": []},
    "cli_tool": {"src": [], "commands": [], "test": []},
    "data_pipeline": {"src": [], "etl": [], "test": [], "config": []},
    "ml_model": {"src": [], "data": [], "models": [], "test": [], "notebooks": []},
    "devops": {"scripts": [], "config": [], "test": []},
    "game": {"src": [], "assets": [], "scenes": [], "test": []},
    "embedded": {"src": [], "firmware": [], "test": []},
}


class ProjectScaffolder:
    def __init__(self):
        self.logger = get_logger("project_scaffolder")

    def ensure_scaffold(
        self,
        *,
        workspace: Path,
        language: str,
        project_type: str = "general",
    ) -> Dict[str, Any]:
        """Ensure a workspace has a minimal scaffold.

        Returns a dict with information about scaffold actions.
        """

        workspace.mkdir(parents=True, exist_ok=True)

        marker_path = workspace / SCAFFOLD_MARKER
        if marker_path.exists():
            return {"scaffolded": False, "reason": "already_scaffolded"}

        existing_files = [
            p
            for p in workspace.rglob("*")
            if p.is_file() and p.name != SCAFFOLD_MARKER
        ]
        if existing_files:
            return {"scaffolded": False, "reason": "workspace_not_empty"}

        language_norm = (language or "python").lower()
        # Normalize language variants
        if language_norm in {"node", "javascript", "js", "mjs", "cjs"}:
            language_norm = "node"
        elif language_norm in {"typescript", "ts"}:
            language_norm = "typescript"
        elif language_norm in {"csharp", "c#"}:
            language_norm = "csharp"
        elif language_norm in {"golang", "go"}:
            language_norm = "go"

        # Create project structure based on project type
        self._create_project_structure(workspace, project_type)

        # Create language-specific scaffold
        if language_norm == "node":
            self._scaffold_node(workspace)
        elif language_norm == "typescript":
            self._scaffold_typescript(workspace)
        elif language_norm == "java":
            self._scaffold_java(workspace)
        elif language_norm == "csharp":
            self._scaffold_csharp(workspace)
        elif language_norm == "go":
            self._scaffold_go(workspace)
        elif language_norm == "rust":
            self._scaffold_rust(workspace)
        elif language_norm == "ruby":
            self._scaffold_ruby(workspace)
        elif language_norm == "php":
            self._scaffold_php(workspace)
        elif language_norm == "swift":
            self._scaffold_swift(workspace)
        elif language_norm == "kotlin":
            self._scaffold_kotlin(workspace)
        elif language_norm == "elixir":
            self._scaffold_elixir(workspace)
        else:
            # Default to Python
            self._scaffold_python(workspace)
            language_norm = "python"

        marker_path.write_text(
            json.dumps(
                {
                    "language": language_norm,
                    "project_type": project_type,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        return {"scaffolded": True, "language": language_norm, "project_type": project_type}

    def _create_project_structure(self, workspace: Path, project_type: str):
        """Create directory structure based on project type."""
        structure = PROJECT_STRUCTURES.get(project_type, PROJECT_STRUCTURES["general"])
        
        for directory in structure.keys():
            (workspace / directory).mkdir(parents=True, exist_ok=True)

    def _scaffold_python(self, workspace: Path):
        (workspace / "README.md").write_text(
            "# Agent Workspace (Python)\n\nGenerated by the autonomous coding agent.\n",
            encoding="utf-8",
        )
        
        # Create basic Python project structure
        (workspace / "src" / "main.py").write_text(
            '#!/usr/bin/env python3\n\n"""Main entry point."""\n\n\ndef main():\n    """Main function."""\n    print("Hello from Python!")\n\n\nif __name__ == "__main__":\n    main()\n',
            encoding="utf-8",
        )
        
        # Create requirements.txt
        (workspace / "requirements.txt").write_text(
            "# Python dependencies\n",
            encoding="utf-8",
        )
        
        # Create .gitignore for Python
        (workspace / ".gitignore").write_text(
            "__pycache__/\n*.py[cod]\n*$py.class\n\n# IDE\n.idea/\n.vscode/\n\n# Virtual environment\nvenv/\n.env/\n\n# Test\n.coverage\n.htmlcov/\n",
            encoding="utf-8",
        )

    def _scaffold_node(self, workspace: Path):
        (workspace / "README.md").write_text(
            "# Agent Workspace (Node.js)\n\nGenerated by the autonomous coding agent.\n",
            encoding="utf-8",
        )

        package_json = {
            "name": "agent-workspace",
            "version": "0.0.0",
            "private": True,
            "type": "commonjs",
            "scripts": {
                "test": "node --test",
                "start": "node src/index.js"
            },
            "dependencies": {},
            "devDependencies": {}
        }
        (workspace / "package.json").write_text(
            json.dumps(package_json, indent=2) + "\n",
            encoding="utf-8",
        )

        (workspace / "src").mkdir(parents=True, exist_ok=True)
        (workspace / "src" / "index.js").write_text(
            "'use strict';\n\n/**\n * Main entry point\n */\n\nfunction main() {\n  console.log('Hello from Node.js!');\n}\n\nif (require.main === module) {\n  main();\n}\n\nmodule.exports = { main };\n",
            encoding="utf-8",
        )

        (workspace / "test").mkdir(parents=True, exist_ok=True)
        (workspace / "test" / "smoke.test.js").write_text(
            "const test = require('node:test');\nconst assert = require('node:assert/strict');\n\nconst lib = require('../src/index');\n\ntest('smoke: module loads', () => {\n  assert.equal(typeof lib, 'object');\n});\n\ntest('smoke: main function exists', () => {\n  assert.equal(typeof lib.main, 'function');\n});\n",
            encoding="utf-8",
        )
        
        # Add a .gitignore for Node.js projects
        (workspace / ".gitignore").write_text(
            "node_modules/\n*.log\n.env\n.DS_Store\ndist/\ncoverage/\n",
            encoding="utf-8",
        )

    def _scaffold_typescript(self, workspace: Path):
        (workspace / "README.md").write_text(
            "# Agent Workspace (TypeScript)\n\nGenerated by the autonomous coding agent.\n",
            encoding="utf-8",
        )

        package_json = {
            "name": "agent-workspace",
            "version": "0.0.0",
            "private": True,
            "type": "commonjs",
            "scripts": {
                "build": "tsc",
                "start": "node dist/index.js",
                "test": "node --test"
            },
            "dependencies": {},
            "devDependencies": {
                "typescript": "^5.0.0",
                "@types/node": "^20.0.0"
            }
        }
        (workspace / "package.json").write_text(
            json.dumps(package_json, indent=2) + "\n",
            encoding="utf-8",
        )

        # Create tsconfig.json
        tsconfig = {
            "compilerOptions": {
                "target": "ES2020",
                "module": "commonjs",
                "outDir": "./dist",
                "rootDir": "./src",
                "strict": true,
                "esModuleInterop": true,
                "skipLibCheck": true,
                "forceConsistentCasingInFileNames": true
            },
            "include": ["src/**/*"],
            "exclude": ["node_modules", "dist"]
        }
        (workspace / "tsconfig.json").write_text(
            json.dumps(tsconfig, indent=2) + "\n",
            encoding="utf-8",
        )

        (workspace / "src").mkdir(parents=True, exist_ok=True)
        (workspace / "src" / "index.ts").write_text(
            "'use strict';\n\n/**\n * Main entry point\n */\n\nexport function main(): void {\n  console.log('Hello from TypeScript!');\n}\n\nif (require.main === module) {\n  main();\n}\n",
            encoding="utf-8",
        )

        (workspace / "test").mkdir(parents=True, exist_ok=True)
        (workspace / "test" / "smoke.test.js").write_text(
            "const test = require('node:test');\nconst assert = require('node:assert/strict');\n\nconst lib = require('../dist/index');\n\ntest('smoke: module loads', () => {\n  assert.equal(typeof lib, 'object');\n});\n\ntest('smoke: main function exists', () => {\n  assert.equal(typeof lib.main, 'function');\n});\n",
            encoding="utf-8",
        )
        
        # Add a .gitignore for TypeScript projects
        (workspace / ".gitignore").write_text(
            "node_modules/\ndist/\n*.log\n.env\n.DS_Store\ncoverage/\n",
            encoding="utf-8",
        )

    def _scaffold_java(self, workspace: Path):
        (workspace / "README.md").write_text(
            "# Agent Workspace (Java)\n\nGenerated by the autonomous coding agent.\n",
            encoding="utf-8",
        )
        
        # Create basic Java project structure
        (workspace / "src" / "main" / "java" / "com" / "agent").mkdir(parents=True, exist_ok=True)
        (workspace / "src" / "test" / "java" / "com" / "agent").mkdir(parents=True, exist_ok=True)
        
        # Create Main.java
        (workspace / "src" / "main" / "java" / "com" / "agent" / "Main.java").write_text(
            """package com.agent;

/**
 * Main entry point
 */
public class Main {
    public static void main(String[] args) {
        System.out.println("Hello from Java!");
    }
}
""",
            encoding="utf-8",
        )
        
        # Create TestMain.java
        (workspace / "src" / "test" / "java" / "com" / "agent" / "TestMain.java").write_text(
            """package com.agent;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class TestMain {
    @Test
    void testMain() {
        // Basic smoke test
        assertTrue(true);
    }
}
""",
            encoding="utf-8",
        )
        
        # Create build.gradle
        (workspace / "build.gradle").write_text(
            """plugins {
    id 'java'
    id 'application'
}

group 'com.agent'
version '1.0.0'

repositories {
    mavenCentral()
}

dependencies {
    testImplementation 'org.junit.jupiter:junit-jupiter:5.9.2'
}

application {
    mainClass = 'com.agent.Main'
}

test {
    useJUnitPlatform()
}
""",
            encoding="utf-8",
        )
        
        # Create .gitignore for Java
        (workspace / ".gitignore").write_text(
            "build/\n.gradle/\ngradle/\n*.iml\n*.ipr\n*.iws\n.out/\n",
            encoding="utf-8",
        )

    def _scaffold_csharp(self, workspace: Path):
        (workspace / "README.md").write_text(
            "# Agent Workspace (C#)\n\nGenerated by the autonomous coding agent.\n",
            encoding="utf-8",
        )
        
        # Create basic C# project structure
        (workspace / "src").mkdir(parents=True, exist_ok=True)
        (workspace / "test").mkdir(parents=True, exist_ok=True)
        
        # Create Program.cs
        (workspace / "src" / "Program.cs").write_text(
            """using System;

namespace AgentWorkspace
{
    /// <summary>
    /// Main entry point
    /// </summary>
    public class Program
    {
        public static void Main(string[] args)
        {
            Console.WriteLine("Hello from C#!");
        }
    }
}
""",
            encoding="utf-8",
        )
        
        # Create AgentWorkspace.csproj
        (workspace / "AgentWorkspace.csproj").write_text(
            """<Project Sdk="Microsoft.NET.Sdk">

  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net8.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
  </PropertyGroup>

</Project>
""",
            encoding="utf-8",
        )
        
        # Create .gitignore for C#
        (workspace / ".gitignore").write_text(
            "bin/\nobj/\n*.user\n*.suo\n*.cache\n*.opensdf\n*.sdf\n",
            encoding="utf-8",
        )

    def _scaffold_go(self, workspace: Path):
        (workspace / "README.md").write_text(
            "# Agent Workspace (Go)\n\nGenerated by the autonomous coding agent.\n",
            encoding="utf-8",
        )
        
        # Create basic Go project structure
        (workspace / "cmd").mkdir(parents=True, exist_ok=True)
        (workspace / "internal").mkdir(parents=True, exist_ok=True)
        (workspace / "pkg").mkdir(parents=True, exist_ok=True)
        (workspace / "test").mkdir(parents=True, exist_ok=True)
        
        # Create main.go
        (workspace / "cmd" / "main.go").write_text(
            """package main

import (
    "fmt"
)

// main is the entry point of the application.
func main() {
    fmt.Println("Hello from Go!")
}
""",
            encoding="utf-8",
        )
        
        # Create go.mod
        (workspace / "go.mod").write_text(
            "module agentworkspace\n\ngo 1.21\n",
            encoding="utf-8",
        )
        
        # Create .gitignore for Go
        (workspace / ".gitignore").write_text(
            "/bin/\n/pkg/\n*.exe\n*.test\n*.out\n",
            encoding="utf-8",
        )

    def _scaffold_rust(self, workspace: Path):
        (workspace / "README.md").write_text(
            "# Agent Workspace (Rust)\n\nGenerated by the autonomous coding agent.\n",
            encoding="utf-8",
        )
        
        # Create basic Rust project structure
        (workspace / "src").mkdir(parents=True, exist_ok=True)
        (workspace / "tests").mkdir(parents=True, exist_ok=True)
        
        # Create main.rs
        (workspace / "src" / "main.rs").write_text(
            """/// Main entry point
fn main() {
    println!("Hello from Rust!");
}

#[cfg(test)]
mod tests {
    #[test]
    fn test_main() {
        // Basic smoke test
        assert!(true);
    }
}
""",
            encoding="utf-8",
        )
        
        # Create Cargo.toml
        (workspace / "Cargo.toml").write_text(
            """[package]
name = "agent-workspace"
version = "0.1.0"
edition = "2021"

[dependencies]
""",
            encoding="utf-8",
        )
        
        # Create .gitignore for Rust
        (workspace / ".gitignore").write_text(
            "target/\nCargo.lock\n*.rs.bk\n",
            encoding="utf-8",
        )

    def _scaffold_ruby(self, workspace: Path):
        (workspace / "README.md").write_text(
            "# Agent Workspace (Ruby)\n\nGenerated by the autonomous coding agent.\n",
            encoding="utf-8",
        )
        
        # Create basic Ruby project structure
        (workspace / "lib").mkdir(parents=True, exist_ok=True)
        (workspace / "spec").mkdir(parents=True, exist_ok=True)
        
        # Create main.rb
        (workspace / "lib" / "main.rb").write_text(
            """# frozen_string_literal: true

# Main entry point
class Main
  def self.run
    puts "Hello from Ruby!"
  end
end

Main.run if __FILE__ == $PROGRAM_NAME
""",
            encoding="utf-8",
        )
        
        # Create Gemfile
        (workspace / "Gemfile").write_text(
            """source "https://rubygems.org"

ruby "3.2.2"

# gem "rails"
""",
            encoding="utf-8",
        )
        
        # Create .gitignore for Ruby
        (workspace / ".gitignore").write_text(
            "*.gem\n*.rbc\n*.sassc\n*.o\n*.so\n*.bundle\n.bundle\n",
            encoding="utf-8",
        )

    def _scaffold_php(self, workspace: Path):
        (workspace / "README.md").write_text(
            "# Agent Workspace (PHP)\n\nGenerated by the autonomous coding agent.\n",
            encoding="utf-8",
        )
        
        # Create basic PHP project structure
        (workspace / "src").mkdir(parents=True, exist_ok=True)
        (workspace / "tests").mkdir(parents=True, exist_ok=True)
        (workspace / "public").mkdir(parents=True, exist_ok=True)
        
        # Create index.php
        (workspace / "public" / "index.php").write_text(
            """<?php

/**
 * Main entry point
 */

echo "Hello from PHP!";
""",
            encoding="utf-8",
        )
        
        # Create composer.json
        (workspace / "composer.json").write_text(
            """{
    "name": "agent/workspace",
    "type": "project",
    "require": {
        "php": ">=8.1"
    },
    "autoload": {
        "psr-4": {
            "Agent\\": "src/"
        }
    }
}
""",
            encoding="utf-8",
        )
        
        # Create .gitignore for PHP
        (workspace / ".gitignore").write_text(
            "/vendor/\n*.log\n*.sql\n*.sqlite\n",
            encoding="utf-8",
        )

    def _scaffold_swift(self, workspace: Path):
        (workspace / "README.md").write_text(
            "# Agent Workspace (Swift)\n\nGenerated by the autonomous coding agent.\n",
            encoding="utf-8",
        )
        
        # Create basic Swift project structure
        (workspace / "Sources").mkdir(parents=True, exist_ok=True)
        (workspace / "Tests").mkdir(parents=True, exist_ok=True)
        
        # Create main.swift
        (workspace / "Sources" / "main.swift").write_text(
            """/// Main entry point
print("Hello from Swift!")
""",
            encoding="utf-8",
        )
        
        # Create Package.swift
        (workspace / "Package.swift").write_text(
            """// swift-tools-version:5.7
import PackageDescription

let package = Package(
    name: "AgentWorkspace",
    products: [
        .executable(name: "AgentWorkspace", targets: ["AgentWorkspace"])
    ],
    dependencies: [],
    targets: [
        .executableTarget(
            name: "AgentWorkspace",
            dependencies: [],
            path: "Sources"
        ),
        .testTarget(
            name: "AgentWorkspaceTests",
            dependencies: ["AgentWorkspace"],
            path: "Tests"
        )
    ]
)
""",
            encoding="utf-8",
        )
        
        # Create .gitignore for Swift
        (workspace / ".gitignore").write_text(
            ".build/\nPackages/\n*.xcodeproj\n*.xcworkspace\n",
            encoding="utf-8",
        )

    def _scaffold_kotlin(self, workspace: Path):
        (workspace / "README.md").write_text(
            "# Agent Workspace (Kotlin)\n\nGenerated by the autonomous coding agent.\n",
            encoding="utf-8",
        )
        
        # Create basic Kotlin project structure
        (workspace / "src" / "main" / "kotlin" / "com" / "agent").mkdir(parents=True, exist_ok=True)
        (workspace / "src" / "test" / "kotlin" / "com" / "agent").mkdir(parents=True, exist_ok=True)
        
        # Create Main.kt
        (workspace / "src" / "main" / "kotlin" / "com" / "agent" / "Main.kt").write_text(
            """package com.agent

/**
 * Main entry point
 */
fun main() {
    println("Hello from Kotlin!")
}
""",
            encoding="utf-8",
        )
        
        # Create build.gradle.kts
        (workspace / "build.gradle.kts").write_text(
            """plugins {
    kotlin("jvm") version "1.9.0"
    application
}

group = "com.agent"
version = "1.0.0"

repositories {
    mavenCentral()
}

dependencies {
    testImplementation(kotlin("test"))
}

application {
    mainClass.set("com.agent.MainKt")
}
""",
            encoding="utf-8",
        )
        
        # Create .gitignore for Kotlin
        (workspace / ".gitignore").write_text(
            "build/\n.gradle/\ngradle/\n*.iml\n*.ipr\n*.iws\n",
            encoding="utf-8",
        )

    def _scaffold_elixir(self, workspace: Path):
        (workspace / "README.md").write_text(
            "# Agent Workspace (Elixir)\n\nGenerated by the autonomous coding agent.\n",
            encoding="utf-8",
        )
        
        # Create basic Elixir project structure
        (workspace / "lib").mkdir(parents=True, exist_ok=True)
        (workspace / "test").mkdir(parents=True, exist_ok=True)
        
        # Create main.ex
        (workspace / "lib" / "agent_workspace.ex").write_text(
            'defmodule AgentWorkspace do\n'
            '  @moduledoc """\n'
            '  Main module for the agent workspace.\n'
            '  """\n\n'
            '  @doc """\n'
            '  Main entry point.\n'
            '  """\n'
            '  def run do\n'
            '    IO.puts("Hello from Elixir!")\n'
            '  end\n'
            'end\n',
            encoding="utf-8",
        )
        
        # Create mix.exs
        (workspace / "mix.exs").write_text(
            """defmodule AgentWorkspace.MixProject do
  use Mix.Project

  def project do
    [
      app: :agent_workspace,
      version: "0.1.0",
      elixir: "~> 1.14",
      start_permanent: Mix.env() == :prod,
      deps: deps()
    ]
  end

  def application do
    [
      extra_applications: [:logger]
    ]
  end

  defp deps do
    []
  end
end
""",
            encoding="utf-8",
        )
        
        # Create .gitignore for Elixir
        (workspace / ".gitignore").write_text(
            "_build/\ndep/\n*.beam\n*.exs\n",
            encoding="utf-8",
        )
