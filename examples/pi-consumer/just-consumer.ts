import { spawnSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import type { ExtensionAPI, ExtensionContext } from "@mariozechner/pi-coding-agent";
import { Type } from "typebox";

type ManifestParameter = {
	name: string;
	required?: boolean;
	default?: string;
	description?: string;
};

type ManifestTool = {
	name: string;
	parameters?: ManifestParameter[];
	docs?: {
		desc?: string;
		usage?: string | string[];
	};
};

type Manifest = {
	manifest?: {
		project?: string;
		principle?: string;
		rules_of_engagement?: string[];
	};
	tools?: ManifestTool[];
};

type ConsumerState = {
	manifest?: Manifest;
	consumerMode: boolean;
};

type ConsumerProfile = {
	brandName?: string;
	tagline?: string;
	introduction?: string;
	guidance?: string[];
	personalityAffinity?: {
		tone?: string;
		style?: string;
		relationship?: string;
	};
};

const CONSUMER_TOOLS = ["just_schema", "just_run", "just_escalate", "just_refresh"];
const BLOCKED_TOOLS = new Set(["bash", "edit", "write"]);
const JUSTFILE_CANDIDATES = ["Justfile", "justfile"];

function runJust(cwd: string, args: string[]) {
	return spawnSync("just", args, {
		cwd,
		encoding: "utf8",
	});
}

function workspaceHasJustfile(cwd: string) {
	return JUSTFILE_CANDIDATES.some((name) => existsSync(join(cwd, name)));
}

function emptyManifest(): Manifest {
	return {
		manifest: {
			principle: "RADICALLY SIMPLE",
			rules_of_engagement: [
				"No Justfile was found in this workspace yet. Consumer mode stays active, but just_schema is empty until a Justfile is added.",
			],
		},
		tools: [],
	};
}

function validateRecipeName(recipe: string) {
	const normalized = recipe.trim();
	if (!normalized) {
		throw new Error("Recipe name cannot be empty.");
	}
	if (/\s/.test(normalized)) {
		throw new Error(`Recipe name must be exactly one token, got ${JSON.stringify(recipe)}`);
	}
	return normalized;
}

function runJustRecipe(cwd: string, recipe: string, args: string[] = []) {
	return runJust(cwd, ["--one", validateRecipeName(recipe), ...args]);
}

function hasOwn(object: Record<string, string>, key: string) {
	return Object.prototype.hasOwnProperty.call(object, key);
}

function requireSuccess(result: ReturnType<typeof runJust>, action: string): string {
	if (result.status !== 0) {
		throw new Error(`${action} failed: ${[result.stdout, result.stderr].filter(Boolean).join("\n").trim()}`);
	}
	return result.stdout;
}

function summarizeTools(manifest: Manifest): string {
	const tools = manifest.tools ?? [];
	if (tools.length === 0) return "No tools discovered.";
	return tools
		.map((tool) => {
			const desc = tool.docs?.desc?.trim() || "No description.";
			const params = (tool.parameters ?? []).map((parameter) => parameter.name).join(", ");
			return params ? `- ${tool.name}(${params}): ${desc}` : `- ${tool.name}: ${desc}`;
		})
		.join("\n");
}

function formatToolSlashUsage(tool: ManifestTool): string {
	const parameters = tool.parameters ?? [];
	if (parameters.length === 0) return `/${tool.name}`;
	return `/${tool.name} ${parameters
		.map((parameter) =>
			parameter.required && parameter.default === undefined
				? `${parameter.name}=<value>`
				: `[${parameter.name}=<value>]`,
		)
		.join(" ")}`;
}

function formatToolHelp(tool: ManifestTool): string {
	const usageDocs = tool.docs?.usage
		? Array.isArray(tool.docs.usage)
			? tool.docs.usage
			: [tool.docs.usage]
		: [];
	const lines = [
		tool.docs?.desc?.trim() || `Run the ${tool.name} recipe from the current just schema.`,
		"",
		`Slash usage: ${formatToolSlashUsage(tool)}`,
		"Arguments can be positional in schema order or passed as key=value pairs.",
	];

	if (usageDocs.length > 0) {
		lines.push("", "Recipe docs:", ...usageDocs);
	}

	const parameters = tool.parameters ?? [];
	if (parameters.length > 0) {
		lines.push(
			"",
			"Parameters:",
			...parameters.map((parameter) => {
				const requirement =
					parameter.required && parameter.default === undefined ? "required" : "optional";
				const defaultValue =
					parameter.default !== undefined ? `, default=${parameter.default}` : "";
				const description = parameter.description?.trim() ? ` — ${parameter.description.trim()}` : "";
				return `- ${parameter.name} (${requirement}${defaultValue})${description}`;
			}),
		);
	}

	return lines.join("\n");
}

function renderToolsCommand(manifest: Manifest): string {
	const tools = manifest.tools ?? [];
	if (tools.length === 0) {
		return [
			"Enabled Just tools",
			"",
			"No tools discovered yet. Add or refresh a Justfile-backed schema and rerun /consumer-refresh.",
		].join("\n");
	}

	return [
		`Enabled Just tools (${tools.length})`,
		"",
		...tools.map((tool) => {
			const desc = tool.docs?.desc?.trim() || "No description.";
			return `${formatToolSlashUsage(tool)} — ${desc}`;
		}),
		"",
		"Run a command with positional values in schema order or explicit key=value pairs.",
	].join("\n");
}

function tokenizeCommandArgs(rawArgs: string): string[] {
	const tokens: string[] = [];
	let current = "";
	let quote: "'" | '"' | undefined;
	let escaping = false;

	for (const character of rawArgs) {
		if (escaping) {
			current += character;
			escaping = false;
			continue;
		}
		if (character === "\\") {
			escaping = true;
			continue;
		}
		if (quote) {
			if (character === quote) {
				quote = undefined;
			} else {
				current += character;
			}
			continue;
		}
		if (character === "'" || character === '"') {
			quote = character;
			continue;
		}
		if (/\s/.test(character)) {
			if (current.length > 0) {
				tokens.push(current);
				current = "";
			}
			continue;
		}
		current += character;
	}

	if (escaping) {
		throw new Error("Command arguments cannot end with a trailing backslash.");
	}
	if (quote) {
		throw new Error("Command arguments contain an unterminated quote.");
	}
	if (current.length > 0) {
		tokens.push(current);
	}
	return tokens;
}

function parseCommandArgs(tool: ManifestTool, rawArgs: string): Record<string, string> {
	if (rawArgs.trim().length === 0) {
		return {};
	}

	const tokens = tokenizeCommandArgs(rawArgs.trim());
	const usesNamedArgs = tokens.some((token) => token.includes("="));
	if (usesNamedArgs && tokens.some((token) => !token.includes("="))) {
		throw new Error(`Use either positional arguments or key=value pairs for /${tool.name}, not both.`);
	}

	if (usesNamedArgs) {
		const args: Record<string, string> = {};
		for (const token of tokens) {
			const separatorIndex = token.indexOf("=");
			const name = token.slice(0, separatorIndex);
			const value = token.slice(separatorIndex + 1);
			if (!name) {
				throw new Error(`Invalid argument for /${tool.name}: ${token}`);
			}
			args[name] = value;
		}
		return args;
	}

	const parameters = tool.parameters ?? [];
	if (tokens.length > parameters.length) {
		throw new Error(`Too many arguments for /${tool.name}: expected at most ${parameters.length}, got ${tokens.length}.`);
	}

	return Object.fromEntries(tokens.map((value, index) => [parameters[index].name, value]));
}

function restoreState(ctx: ExtensionContext): ConsumerState | undefined {
	const stateEntry = ctx.sessionManager
		.getEntries()
		.filter((entry: { type: string; customType?: string }) => entry.type === "custom" && entry.customType === "consumer-state")
		.pop() as { data?: ConsumerState } | undefined;

	return stateEntry?.data;
}

function readJsonFile<T>(path: string): T | undefined {
	if (!existsSync(path)) return undefined;
	try {
		return JSON.parse(readFileSync(path, "utf8")) as T;
	} catch (error) {
		throw new Error(`Failed to read ${path}: ${error instanceof Error ? error.message : String(error)}`);
	}
}

function loadProfile(cwd: string): ConsumerProfile {
	const globalProfile = readJsonFile<ConsumerProfile>(join(homedir(), ".pi", "agent", "consumer-profile.json")) ?? {};
	const projectProfile = readJsonFile<ConsumerProfile>(join(cwd, ".pi", "consumer-profile.json")) ?? {};

	return {
		...globalProfile,
		...projectProfile,
		personalityAffinity: {
			...(globalProfile.personalityAffinity ?? {}),
			...(projectProfile.personalityAffinity ?? {}),
		},
		guidance: projectProfile.guidance ?? globalProfile.guidance,
	};
}

export default function justConsumerExtension(pi: ExtensionAPI) {
	let manifest: Manifest | undefined;
	let consumerMode = false;
	let profile: ConsumerProfile = {};

	function getBrandName() {
		return profile.brandName?.trim() || "just-for-agents Consumer";
	}

	function getTagline() {
		return profile.tagline?.trim() || "Local Justfile-first utility chatbot";
	}

	function getGuidance() {
		return (
			profile.guidance ?? [
				"Ask in plain English and I will map your request onto the Justfile API.",
				"My only tools are just_schema, just_run, just_refresh, and just_escalate — the Justfile is the API surface.",
				"If the current API surface is too small, I escalate through just escalate.",
			]
		);
	}

	function showStartupBranding(ctx: ExtensionContext) {
		const brandName = getBrandName();
		const introduction =
			profile.introduction?.trim() || `Hi. ${brandName} is ready for this workspace.`;
		const guidance = getGuidance();
		const separator = ctx.ui.theme.fg("muted", "────────────────────────────────────────");

		ctx.ui.notify(introduction, "info");
		ctx.ui.setWidget("consumer-brand", [
			separator,
			ctx.ui.theme.fg("accent", ctx.ui.theme.bold(brandName)),
			ctx.ui.theme.fg("muted", getTagline()),
			"",
			...guidance.map((line) => `${ctx.ui.theme.fg("accent", "•")} ${line}`),
		]);
	}

	function persistState() {
		pi.appendEntry("consumer-state", {
			manifest,
			consumerMode,
		});
	}

	function setConsumerMode(ctx: ExtensionContext, enabled: boolean) {
		consumerMode = enabled;
		if (enabled) {
			pi.setActiveTools(CONSUMER_TOOLS);
			ctx.ui.setStatus("consumer", ctx.ui.theme.fg("accent", getBrandName()));
		} else {
			ctx.ui.setStatus("consumer", undefined);
		}
	}

	function refreshManifest(cwd: string): Manifest {
		if (!workspaceHasJustfile(cwd)) {
			manifest = emptyManifest();
			return manifest;
		}
		requireSuccess(runJustRecipe(cwd, "bootstrap"), "just bootstrap");
		const schemaOutput = requireSuccess(runJustRecipe(cwd, "schema"), "just schema");
		const parsed = JSON.parse(schemaOutput) as Manifest;
		manifest = parsed;
		return parsed;
	}

	function ensureManifest(ctx: ExtensionContext): Manifest {
		if (manifest) return manifest;
		return refreshManifest(ctx.cwd);
	}

	function findTool(recipe: string, currentManifest: Manifest): ManifestTool | undefined {
		return (currentManifest.tools ?? []).find((tool) => tool.name === recipe);
	}

	function validateArgs(tool: ManifestTool, args: Record<string, string>) {
		const knownParameters = new Set((tool.parameters ?? []).map((parameter) => parameter.name));
		const unknownParameters = Object.keys(args).filter((key) => !knownParameters.has(key));
		if (unknownParameters.length > 0) {
			throw new Error(`Unknown parameters for ${tool.name}: ${unknownParameters.join(", ")}`);
		}

		const missingRequiredParameters = (tool.parameters ?? [])
			.filter((parameter) => parameter.required && parameter.default === undefined)
			.map((parameter) => parameter.name)
			.filter((name) => !(name in args));
		if (missingRequiredParameters.length > 0) {
			throw new Error(`Missing required parameters for ${tool.name}: ${missingRequiredParameters.join(", ")}`);
		}
	}

	function buildRecipeArguments(tool: ManifestTool, args: Record<string, string>) {
		const parameters = tool.parameters ?? [];
		let lastProvidedIndex = -1;

		for (const [index, parameter] of parameters.entries()) {
			if (hasOwn(args, parameter.name)) {
				lastProvidedIndex = index;
			}
		}

		if (lastProvidedIndex === -1) {
			return [];
		}

		return parameters.slice(0, lastProvidedIndex + 1).map((parameter) => {
			if (hasOwn(args, parameter.name)) {
				return args[parameter.name];
			}
			if (parameter.default !== undefined) {
				return parameter.default;
			}
			throw new Error(`Missing required parameter for ${tool.name}: ${parameter.name}`);
		});
	}

	function formatProcessOutput(result: ReturnType<typeof runJust>): string {
		return [result.stdout, result.stderr].filter(Boolean).join("\n").trim() || "(no output)";
	}

	function executeRecipe(tool: ManifestTool, args: Record<string, string>, cwd: string) {
		validateArgs(tool, args);
		return runJustRecipe(cwd, tool.name, buildRecipeArguments(tool, args));
	}

	// Pi commands are additive for the session, so each generated command resolves
	// its tool against the current manifest before executing. If a recipe disappears
	// before the next restart, the stale command fails safely instead of guessing.
	function syncManifestCommands() {
		pi.registerCommand("tools", {
			description: "Show the enabled Just recipe slash commands",
			handler: async (_args, ctx) => {
				await ctx.ui.editor("Enabled Just tools", renderToolsCommand(ensureManifest(ctx)));
			},
		});

		for (const tool of manifest?.tools ?? []) {
			pi.registerCommand(tool.name, {
				description: tool.docs?.desc?.trim() || `Run ${tool.name} from the current just schema`,
				handler: async (rawArgs, ctx) => {
					const currentManifest = ensureManifest(ctx);
					const currentTool = findTool(tool.name, currentManifest);
					if (!currentTool) {
						ctx.ui.notify(`/${tool.name} is no longer available. Run /consumer-refresh to resync the schema.`, "warning");
						return;
					}

					const requiredParameters = (currentTool.parameters ?? []).filter(
						(parameter) => parameter.required && parameter.default === undefined,
					);
					if (rawArgs.trim().length === 0 && requiredParameters.length > 0) {
						await ctx.ui.editor(`/${tool.name} usage`, formatToolHelp(currentTool));
						return;
					}

					try {
						const parsedArgs = parseCommandArgs(currentTool, rawArgs);
						const result = executeRecipe(currentTool, parsedArgs, ctx.cwd);
						const output = formatProcessOutput(result);
						if (result.status !== 0) {
							await ctx.ui.editor(
								`/${tool.name} failed`,
								`${formatToolHelp(currentTool)}\n\nCommand output:\n${output}`,
							);
							ctx.ui.notify(`/${tool.name} failed (${result.status ?? 1}).`, "error");
							return;
						}

						await ctx.ui.editor(`/${tool.name} output`, output);
						ctx.ui.notify(`/${tool.name} completed.`, "info");
					} catch (error) {
						const message = error instanceof Error ? error.message : String(error);
						await ctx.ui.editor(`/${tool.name} usage`, `${formatToolHelp(currentTool)}\n\n${message}`);
						ctx.ui.notify(message, "warning");
					}
				},
			});
		}
	}

	pi.registerCommand("consumer-refresh", {
		description: "Refresh just bootstrap instructions and schema",
		handler: async (_args, ctx) => {
			const refreshed = refreshManifest(ctx.cwd);
			syncManifestCommands();
			setConsumerMode(ctx, true);
			persistState();
			ctx.ui.notify(
				`Consumer schema refreshed (${(refreshed.tools ?? []).length} tools). Slash commands rebuilt; use /tools to inspect them.`,
				"info",
			);
		},
	});

	pi.registerCommand("consumer-brand", {
		description: "Re-show the Consumer Agent introduction and guidance",
		handler: async (_args, ctx) => {
			showStartupBranding(ctx);
		},
	});

	pi.registerTool({
		name: "just_schema",
		label: "Just Schema",
		description: "Return the cached just-for-agents manifest",
		parameters: Type.Object({}),
		async execute(_toolCallId, _params, _signal, _onUpdate, ctx) {
			const currentManifest = ensureManifest(ctx);
			return {
				content: [{ type: "text", text: JSON.stringify(currentManifest, null, 2) }],
				details: {
					hasJustfile: workspaceHasJustfile(ctx.cwd),
					toolCount: (currentManifest.tools ?? []).length,
				},
			};
		},
	});

	pi.registerTool({
		name: "just_refresh",
		label: "Just Refresh",
		description: "Re-run just bootstrap and just schema",
		parameters: Type.Object({}),
		async execute(_toolCallId, _params, _signal, _onUpdate, ctx) {
			const currentManifest = refreshManifest(ctx.cwd);
			syncManifestCommands();
			const hasJustfile = workspaceHasJustfile(ctx.cwd);
			const message = hasJustfile
				? "Refreshed bootstrap instructions, schema, and generated slash commands."
				: "No Justfile found. Consumer mode is active, and the cached schema remains empty until this workspace gets a Justfile.";
			persistState();
			return {
				content: [{ type: "text", text: message }],
				details: {
					hasJustfile,
					toolCount: (currentManifest.tools ?? []).length,
				},
			};
		},
	});

	pi.registerTool({
		name: "just_run",
		label: "Just Run",
		description: "Execute a recipe from the current just schema. For research, rounds means new rounds to append now.",
		parameters: Type.Object({
			recipe: Type.String({ description: "Recipe name from just schema" }),
			args: Type.Optional(
				Type.Record(Type.String(), Type.String(), {
					description: "Recipe arguments keyed by schema parameter name; the extension maps them to positional just arguments",
				}),
			),
		}),
		async execute(_toolCallId, params, _signal, _onUpdate, ctx) {
			const currentManifest = ensureManifest(ctx);
			if (!workspaceHasJustfile(ctx.cwd)) {
				throw new Error(
					"No Justfile found in this workspace, so there are no recipes to run yet.",
				);
			}
			const tool = findTool(params.recipe, currentManifest);
			const args = params.args ?? {};
			if (!tool) {
				throw new Error(`Unknown recipe: ${params.recipe}`);
			}
			const result = executeRecipe(tool, args, ctx.cwd);
			const output = formatProcessOutput(result);
			return {
				content: [{ type: "text", text: output }],
				details: {
					exitCode: result.status ?? 1,
					recipe: params.recipe,
				},
			};
		},
	});

	pi.registerTool({
		name: "just_escalate",
		label: "Just Escalate",
		description: "Ask the Senior Creator Agent for a new capability",
		parameters: Type.Object({
			prompt: Type.String({ description: "Describe the missing capability" }),
		}),
		async execute(_toolCallId, params, _signal, _onUpdate, ctx) {
			if (!workspaceHasJustfile(ctx.cwd)) {
				throw new Error(
					"No Justfile found in this workspace, so just_escalate cannot add or refresh recipes yet.",
				);
			}
			const result = runJustRecipe(ctx.cwd, "escalate", [params.prompt]);
			requireSuccess(result, "just escalate");
			const output = [result.stdout, result.stderr].filter(Boolean).join("\n").trim();
			const currentManifest = refreshManifest(ctx.cwd);
			syncManifestCommands();
			persistState();
			const refreshMessage = `Consumer schema refreshed (${(currentManifest.tools ?? []).length} tools). Slash commands rebuilt; use /tools to inspect them.`;
			return {
				content: [{ type: "text", text: output ? `${output}\n\n${refreshMessage}` : refreshMessage }],
				details: {
					exitCode: result.status ?? 1,
					toolCount: (currentManifest.tools ?? []).length,
				},
			};
		},
	});

	pi.on("session_start", async (_event, ctx) => {
		try {
			profile = loadProfile(ctx.cwd);
		} catch (error) {
			profile = {};
			ctx.ui.notify(
				`Consumer profile could not be loaded: ${error instanceof Error ? error.message : String(error)}`,
				"warning",
			);
		}

		const restored = restoreState(ctx);
		if (restored?.manifest) {
			manifest = restored.manifest;
		}

		try {
			refreshManifest(ctx.cwd);
		} catch (error) {
			if (!manifest) throw error;
			ctx.ui.notify(`Using cached consumer schema: ${error instanceof Error ? error.message : String(error)}`, "warning");
		}

		syncManifestCommands();
		setConsumerMode(ctx, true);
		showStartupBranding(ctx);
		if (!workspaceHasJustfile(ctx.cwd)) {
			ctx.ui.notify(
				"No Justfile found in this workspace yet. Consumer mode is active with only just_* tools, and just_schema will stay empty until a Justfile is added.",
				"info",
			);
		} else {
			ctx.ui.notify(
				`Registered ${(manifest?.tools ?? []).length} Just recipe slash commands. Use /tools to inspect them.`,
				"info",
			);
		}
		persistState();
	});

	pi.on("turn_start", async () => {
		if (consumerMode) {
			persistState();
		}
	});

	pi.on("before_agent_start", async (event, ctx) => {
		if (!consumerMode) return;
		const currentManifest = ensureManifest(ctx);
		const affinityLines = [
			profile.personalityAffinity?.tone ? `- Tone: ${profile.personalityAffinity.tone}` : undefined,
			profile.personalityAffinity?.style ? `- Style: ${profile.personalityAffinity.style}` : undefined,
			profile.personalityAffinity?.relationship
				? `- Relationship frame: ${profile.personalityAffinity.relationship}`
				: undefined,
		]
			.filter(Boolean)
			.join("\n");

		return {
			systemPrompt:
				`${event.systemPrompt}

You are the Consumer Agent for a just-for-agents workspace.

Consumer mode rules:
- Your only tools are just_schema, just_run, just_refresh, and just_escalate. No shell, file-edit, or write tools are available; the Justfile is the entire capability surface.
- Never parse the Justfile source directly — call just_schema instead.
- Treat just schema as the authoritative API surface.
- If just_schema returns no recipes, explain that the workspace has no Justfile yet and do not invent tools.
- Pass just_run arguments by schema parameter name, but remember the extension executes just recipe parameters positionally.
- For example, for md5(file), call just_run with args like {"file": "/path/to/file"} and let the extension run \`just --one md5 /path/to/file\`.
- When keyed args skip an optional parameter that has a schema default, the extension fills that default automatically before executing the positional just recipe.
- For the research recipe, \`rounds\` means how many new rounds to run in this invocation, not a retry count for round 1 and not a total-to-date target.
- If the user asks for one research iteration or one more round, call research with \`{"rounds": "1"}\` and let the recipe append the next round automatically.
- When a research request clearly maps to the existing research recipe, run it directly instead of asking whether the user wants the next numbered round.
- For research requests, always pass the user’s requested subject text as \`subject_title\`; do not substitute \`subject_id\` for the required \`subject_title\` parameter.
- After a successful recipe run, report the result concisely and stop. Do not ask whether the user wants another round or additional follow-up unless they explicitly requested options.
- If no recipe fits, call just_escalate.

Startup UI branding and guidance are for the user interface only and should not be repeated unless relevant.
${affinityLines ? `\nPersonality affinity for user-facing responses:\n${affinityLines}\n` : ""}

Available recipes:
${summarizeTools(currentManifest)}`,
		};
	});

	pi.on("tool_call", async (event) => {
		if (consumerMode && BLOCKED_TOOLS.has(event.toolName)) {
			return {
				block: true,
				reason: "Consumer mode only allows just-for-agents consumer tools.",
			};
		}
	});
}
