# The Personal Power Agent: User Guide

## 🚀 Vision: RADICALLY SIMPLE
`just-for-agents` turns your standard `Justfile` into a personalized, ever-evolving toolset for AI agents. It's the "Root" of your personal automation, allowing lightweight agents to perform complex tasks while high-reasoning agents build the tools they need.

## 💡 Why use this?
- **Inexpensive & Fast**: Use smaller, faster models (like Gemini Flash or local LLMs) for daily tasks.
- **Self-Improving**: When a task is too complex, the agent automatically asks a "Senior Agent" to build a new tool.
- **Zero Config**: Your `Justfile` *is* the configuration. No complex setup, no external databases.

## 🔄 How it Works
The interaction follows a seamless "Escalation Loop":

```mermaid
sequence_diagram
    participant User
    participant Consumer as Consumer Agent (Lightweight)
    participant Justfile as Justfile (The Toolset)
    participant Creator as Senior Creator Agent (Pro)

    User->>Consumer: "Perform task X"
    Consumer->>Justfile: Check tools (just schema)
    alt Tool Exists
        Justfile-->>Consumer: Tool found
        Consumer->>Justfile: Execute tool
        Justfile-->>User: Result
    else Tool Missing
        Consumer->>Justfile: just escalate "Need tool for X"
        Justfile->>Creator: Request skill upgrade
        Creator->>Justfile: just add-tool "new-tool"
        Justfile-->>Consumer: Tool now available
        Consumer->>Justfile: Execute new-tool
        Justfile-->>User: Result
    end
```

## 🛠 Getting Started

1. **Bootstrap**: Ensure your `Justfile` has the `just-for-agents` core.
2. **Interact**: Talk to your preferred agent. Point it to this directory.
3. **Discover**: The agent will run `just bootstrap` and `just schema` to understand its capabilities.
4. **Grow**: Watch your `Justfile` grow as you ask for new things.

## 📖 Annexes
- [Annex A: The Consumer Agent](annexes/consumer_agent.md) - For implementing lightweight chat interfaces.
- [Annex B: The Senior Agent](annexes/senior_agent.md) - For defining the creator contract and safety.
