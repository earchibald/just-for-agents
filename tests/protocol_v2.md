# just-for-agents Test Protocol v2

## Methodology
Testing is now encapsulated directly within the project using the `just test-agent` recipe (Dogfooding). This recipe scaffolds an isolated environment and invokes a `gemini` agent in autonomous (`--yolo`) mode.

To run a test, the user executes:
`just test-agent <test-name> "<prompt>"`

## Success Criteria
1. The agent successfully bootstraps using the provided `Justfile`.
2. The agent fulfills the specific multi-step or complex prompt.
3. The agent validates its own changes by running `just schema`.
4. The test environment's `Justfile` remains valid and parseable.

## Test Cases

### 1. Multi-recipe Workflow (`pipeline-test`)
**Prompt:** "Create three tools: `fetch-data` (echoes 'data1,data2' to data.csv), `process-data` (reads data.csv and replaces commas with spaces, saving to out.txt), and `report-data` (cats out.txt). Execute them in order to produce the final report."
**Objective:** Test the agent's ability to chain multiple new tools together and manage intermediate file state.

### 2. Environment Isolation (`env-test`)
**Prompt:** "Create a tool `setup-env` that writes 'API_KEY=12345' to a `.env` file. Create another tool `read-env` that reads and echoes the API_KEY from the `.env` file. Run both."
**Objective:** Verify the agent can create recipes that interact with hidden files and environment variables, a common pattern in `just`.

### 3. Error Handling (`error-test`)
**Prompt:** "Create a tool `fail-task` that runs an invalid command (like `cat non_existent_file`). Create a tool `diagnose-failure` that adds a file called 'diagnosis.txt' explaining why `fail-task` fails. Run `fail-task`, catch the error, and then run `diagnose-failure`."
**Objective:** Test if the agent can handle non-zero exit codes from recipes and recover gracefully.

### 4. Meta-Extension (`meta-test`)
**Prompt:** "Create a tool called `bootstrap-subtasks` that uses the `add-tool` recipe internally to create two new tools: `subtask-a` and `subtask-b`. Run `bootstrap-subtasks`, then run `subtask-a`."
**Objective:** Test the limits of self-skilling by having an agent create a tool that generates other tools.

### 5. LSP Awareness (`lsp-test`)
**Prompt:** "Read the manifest rules of engagement by running `just`. Identify the recommended tool for advanced Justfile analysis, install it using the provided recipe, and report success."
**Objective:** Ensure the agent correctly interprets the `MANIFEST` and utilizes the newly added `just-lsp` integration.