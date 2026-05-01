# **just-for-agents**

**just-for-agents** turns your Justfiles into the API for the agentic era. It treats documentation comments as the source of truth for tool-use instructions, allowing agents to "self-skill" by reading and maintaining their own command interfaces.  
It is designed to be model-agnostic: use heavy-duty LLMs to architect your workflows and lightweight local models to execute them. If it’s a tool for a human in the CLI, just-for-agents makes it a building block for an agent.

## **⚡️ The Core Philosophy**

Traditional agentic tool-use often requires heavy JSON schemas, brittle API wrappers, or complex MCP (Model Context Protocol) implementations. just-for-agents suggests a simpler way:

1. **Documentation is Data:** The comments above your just recipes aren't just for humans; they are the "Description" field for the agent's tool-call.  
2. **The Justfile is the Manifest:** A single file defines the entire capability surface of a project.  
3. **Self-Skilling:** Agents can be tasked not just with *using* the file, but with *extending* it—adding new recipes to solve new problems as they encounter them.

## **🛠 How It Works**

### **1\. The Multi-Directional Workflow**

* **Architectural Maintenance:** High-capacity coding agents (e.g., Claude 3.5 Sonnet, GPT-4o) are used to create, refactor, and maintain the Justfile. They ensure recipes are idempotent, safe, and well-documented.  
* **Intent Execution:** Lightweight, local tool-using models (e.g., Llama 3, Mistral, Phi-3) parse the Justfile to understand user intent. Because just handles the shell complexity, the model only needs to map intent to the correct recipe and arguments.

### **2\. The Documentation Standard**

just-for-agents treats the just comment syntax as a formal schema.  
\# List all active database migrations  
\# @param target: The environment to check (default: 'dev')  
\# @usage: Use this when you need to verify if the schema is up to date.  
list-migrations target="dev":  
    echo "Checking migrations for {{target}}..."  
    ./scripts/db-check.sh {{target}}

## **🚀 Getting Started**

### **Prerequisites**

* [just](https://github.com/casey/just) installed on your system.  
* An agent or LLM interface capable of reading local files and executing shell commands.

### **Installation**

*(To be completed: Installation steps for the just-for-agents parser/utility)*  
\# Example installation  
pip install just-for-agents

### **Basic Usage**

*(To be completed: Detailed CLI or Library usage examples)*  
\# Instruct an agent to learn the local environment  
just-for-agents \--summarize

### **Operational Helpers**

For tmux-backed research runs, use the built-in runtime helpers instead of ad-hoc shell inspection:

```bash
just research-status subject_id='ways-to-improve-the-research-tool'
just research-reset
```

If you use local Ollama aliases, keep the **consumer** and **research** roles separate. A chat-oriented Consumer model can power Pi, while `just research` can prefer a dedicated research-tuned model such as `just-research-qwen3.6:latest`.

### **Managed Recipe Queue**

Managed non-core recipe mutations now stage through the quarantined queue instead of publishing directly into the live Just surface.

```bash
just managed-bootstrap
just managed-new recipe_name='hello' command='echo hi' desc='Say hi'
just managed-edit recipe_name='hello'
just managed-delete recipe_name='hello'
just managed-queue
just managed-inspect req-20260501-001
just managed-dry-run req-20260501-001
just managed-review req-20260501-001
just managed-dashboard
just managed-approve req-20260501-001 operator='you' rationale='reviewed'
```

`just managed-bootstrap` only creates the governed overlay and keeps the workspace in a **quarantine-first** posture. Until a request is approved, it stays under `.just-for-agents/managed/quarantine/requests/` and does **not** appear in `just schema` or `just --list`.

`just managed-dashboard` reports whether the managed-history-backed approved surface is `uninitialized`, `clean`, or `drifted`. Direct edits under `.just-for-agents/managed/approved/` are treated as drift, and `managed-approve` / `managed-render-include` refuse to overwrite that state until the operator restores it from managed history or imports it into a formal request. `just escalate` follows the same quarantined path, so escalated capability work lands in the review queue first.

### **Versioning**

The canonical project version lives in the root `VERSION` file and follows semantic versioning.

```bash
just version
```

Release notes live in `CHANGELOG.md`, and git tags use the matching `vX.Y.Z` format.

## **📋 Standardized Instruction Set (Spec)**

To ensure interoperability, just-for-agents follows these conventions:

* **The Discovery Pattern:** Agents should always run just \--list or just-for-agents \--scan upon entering a directory.  
* **The Argument Contract:** All variables in recipes should have sensible defaults or clear descriptions in the comments.  
* **Safety First:** Destructive commands (e.g., rm, drop-db) must be explicitly tagged with @danger in the comments to trigger agent confirmation.

## **🗺 Roadmap**

* \[ \] **Automated Tool-Calling Bridge:** Auto-generate JSON schemas from Justfiles for OpenAI/Anthropic tool-use formats.  
* \[ \] **Local LLM Integration:** Optimized prompts for small models to parse Justfiles without context overflow.  
* \[ \] **Self-Mutation Logic:** Patterns for agents to safely "write back" to the Justfile to add new skills.  
* \[ \] **Validation Suite:** A linter to ensure Justfile comments meet the just-for-agents spec.

## **🤝 Contributing**

We welcome contributions\! If you have ideas for making CLI tools more agent-friendly, please open an issue or a PR.

## **📄 License**

*(To be completed: e.g., MIT or Apache 2.0)*  
**just-for-agents** — *Because your CLI is already an API, your agent just doesn't know it yet.*
