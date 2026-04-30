# Round 3 Strategy: Lower-Intelligence Agent Testing

## Goal
Evaluate the robustness of the `just-for-agents` protocol when used by lightweight, lower-parameter models (e.g., Gemini Flash, Copilot Haiku). These models often have smaller context windows and weaker reasoning capabilities.

## Success Metrics
1. **Instruction Following**: Does the model respect the `GEMINI.md` and `just bootstrap` instructions despite its lower intelligence?
2. **Syntax Accuracy**: Can it correctly generate `[doc()]` attributes and recipe blocks without hallucinating `just` syntax?
3. **Recovery**: If the model makes a syntax error, can it use the CLI output to self-correct?

## Model Selection
- **Gemini 2.5 Flash**: Ultra-fast (1M context) - Quick analysis, simple queries.
- **Gemini 2.0 Flash Lite**: Lightweight fast model, text-only.
- **Copilot (Haiku/Light)**: Specialized for quick coding tasks.
- **Gemma 4-31B (Local/Edge)**: Testing robustness on models designed for local deployment.

## Test Scenarios (Derived from Protocol v1 & v2)
1. **Basic Extension**: `add-tool` a simple `ls` wrapper.
2. **Parameter Passing**: `add-tool` a tool with a default parameter.
3. **Cross-Platform Install**: Run `install-lsp` and see if it correctly identifies the OS and handles the output.
4. **De-skilling**: Use `remove-tool` to delete a tool it just created.
5. **Local/Edge Robustness**: Verify if a local-class model can handle the bootstrap + schema discovery loop.

## Deployment
Tests will be run using `just test-agent` with the model-specific flags where applicable (e.g., `agent='gemini-flash'`).
