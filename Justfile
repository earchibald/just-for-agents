[doc('@desc Generate a JSON tool schema from the Justfile
@usage Use this to get a machine-readable map of available tools.
@returns json')]
@schema:
    just --justfile ./.just-for-agents/protocol.just schema

[doc('@desc Bootstrap an agent into this workspace
@usage Run this when an agent first enters the project.')]
@bootstrap:
    just --justfile ./.just-for-agents/protocol.just bootstrap

[doc('@desc Print the current project version
@usage Run this to display the current just-for-agents version.')]
@version:
    just --justfile ./.just-for-agents/protocol.just version

[doc("@desc Add a new tool to the Justfile
@param name The name of the new recipe
@param command The shell command to execute
@param desc a short description
@param params Optional parameters (e.g. arg1 arg2=val)
@usage Use this to expand the agent API surface.")]
@add-tool name command desc='' params='':
    just --justfile ./.just-for-agents/protocol.just add-tool "{{name}}" "{{command}}" "{{desc}}" "{{params}}"

[doc('@desc Remove a tool from the Justfile
@param name The name of the recipe to remove
@usage Use this to clean up unused or deprecated tools.')]
@remove-tool name:
    just --justfile ./.just-for-agents/protocol.just remove-tool "{{name}}"

[doc('@desc Install just-lsp for language server support
@usage Agents should run this to enable advanced Justfile analysis. MacOS is preferred; Linux requires documentation review.')]
@install-lsp:
    just --justfile ./.just-for-agents/protocol.just install-lsp

[doc("@desc Run an autonomous agent test in a sandbox
@param name The name of the test scenario
@param prompt The instruction to give the agent
@param agent The agent CLI to use (gemini, copilot, opencode)
@param model Optional model string (e.g. 'ollama/qwen3.6:latest' for opencode)
@usage just test-agent name='qwen-test' prompt='Say hello' agent='opencode' model='ollama/qwen3.6:latest'")]
@test-agent name prompt agent='gemini' model='':
    just --justfile ./.just-for-agents/agent.just test-agent "{{name}}" "{{prompt}}" "{{agent}}" "{{model}}"

[doc('@desc Request a skill upgrade from a Senior Agent
@param prompt The description of the missing capability or tool needed
@usage Use this when you identify a task that cannot be completed with existing tools.')]
@escalate prompt:
    just --justfile ./.just-for-agents/agent.just escalate "{{prompt}}"

[doc("@desc Add an Ollama model to the opencode configuration
@param model The name of the model in ollama (e.g. qwen3.6:latest)
@param display_name Optional display name for the model
@usage just opencode-add-ollama-model qwen3.6:latest 'Qwen 3.6'")]
opencode-add-ollama-model model display_name='':
    just --justfile ./.just-for-agents/research.just opencode-add-ollama-model "{{model}}" "{{display_name}}"

[doc("@desc Configure opencode to use Exa's unauthenticated remote MCP endpoint
@usage just opencode-enable-exa-mcp")]
opencode-enable-exa-mcp:
    just --justfile ./.just-for-agents/research.just opencode-enable-exa-mcp

[doc('@desc Bootstrap the managed recipe governance overlay
@usage Run once to materialize .just-for-agents/managed/. Idempotent.')]
@managed-bootstrap:
    just --justfile ./.just-for-agents/managed.just bootstrap

[doc('@desc List quarantined managed-recipe change requests
@usage just managed-queue
@returns text')]
@managed-queue:
    just --justfile ./.just-for-agents/managed.just queue

[doc("@desc Print one quarantined request as JSON
@param request_id The request id (e.g. req-20260501-001)
@usage just managed-inspect req-20260501-001
@returns json")]
@managed-inspect request_id:
    just --justfile ./.just-for-agents/managed.just inspect "{{request_id}}"

[doc("@desc Find files >1MB in a directory and create a timestamped zip archive.
@param dir The directory to search (defaults to '.')
@usage just archive-large dir='downloads'")]
archive-large dir='.':
    just --justfile ./.just-for-agents/utility.just archive-large "{{dir}}"

[doc("@desc Calculate the MD5 hash of a file (cross-platform)
@param file The path to the file to hash
@usage just md5 path/to/file.txt")]
@md5 file:
    just --justfile ./.just-for-agents/utility.just md5 "{{file}}"

[no-cd]
[doc("@desc Dispatch a research agent for autonomous multi-round research
@param subject_title The title of the research subject
@param rounds Number of new research rounds to run in this invocation (default 3)
@param source Initial source or context
@param subject_id Optional slug for the research directory
@param model Optional provider/model string or Ollama model name. Leave empty to auto-detect a usable local model.
@usage just research subject_title='Edge caching strategies' rounds='10'
@usage just research subject_title='Edge caching strategies' rounds='10' model='qwen3.6:latest'")]
research subject_title rounds='3' source='' subject_id='' model='':
    just --justfile ./.just-for-agents/research.just research "{{subject_title}}" "{{rounds}}" "{{source}}" "{{subject_id}}" "{{model}}"

[doc('@desc List all research subjects')]
list-research:
    just --justfile ./.just-for-agents/research.just list-research

[doc("@desc Show the latest research tmux/log status
@param subject_id Optional subject slug to inspect the latest saved round
@param lines Number of trailing lines to show from logs/output (default 120)
@usage just research-status
@usage just research-status subject_id='ways-to-improve-the-research-tool'")]
research-status subject_id='' lines='120':
    just --justfile ./.just-for-agents/research.just research-status "{{subject_id}}" "{{lines}}"

[doc("@desc Reset the research tmux session
@usage just research-reset")]
research-reset:
    just --justfile ./.just-for-agents/research.just research-reset

[doc("@desc Resolve a usable model for the research recipe
@param requested Optional provider/model string or Ollama model name
@usage just research-model
@usage just research-model requested='qwen3.6:latest'
@usage just research-model requested='openai/gpt-4.1'")]
research-model requested='':
    just --justfile ./.just-for-agents/research.just research-model "{{requested}}"
