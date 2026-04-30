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

function runJust(cwd: string, args: string[]) {
	return spawnSync("just", args, {
		cwd,
		encoding: "utf8",
	});
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
		requireSuccess(runJust(cwd, ["bootstrap"]), "just bootstrap");
		const schemaOutput = requireSuccess(runJust(cwd, ["schema"]), "just schema");
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

	pi.registerCommand("consumer-refresh", {
		description: "Refresh just bootstrap instructions and schema",
		handler: async (_args, ctx) => {
			const refreshed = refreshManifest(ctx.cwd);
			setConsumerMode(ctx, true);
			persistState();
			ctx.ui.notify(`Consumer schema refreshed (${(refreshed.tools ?? []).length} tools).`, "info");
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
			persistState();
			return {
				content: [{ type: "text", text: `Refreshed bootstrap instructions and schema.` }],
				details: {
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
			const tool = findTool(params.recipe, currentManifest);
			const args = params.args ?? {};
			if (!tool) {
				throw new Error(`Unknown recipe: ${params.recipe}`);
			}
			validateArgs(tool, args);

			const result = runJust(
				ctx.cwd,
				[params.recipe, ...buildRecipeArguments(tool, args)],
			);
			const output = [result.stdout, result.stderr].filter(Boolean).join("\n").trim() || "(no output)";
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
			const result = runJust(ctx.cwd, ["escalate", params.prompt]);
			requireSuccess(result, "just escalate");
			const output = [result.stdout, result.stderr].filter(Boolean).join("\n").trim();
			const currentManifest = refreshManifest(ctx.cwd);
			persistState();
			const refreshMessage = `Consumer schema refreshed (${(currentManifest.tools ?? []).length} tools).`;
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
		if (!existsSync(join(ctx.cwd, "Justfile"))) return;
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

		setConsumerMode(ctx, true);
		showStartupBranding(ctx);
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
- Pass just_run arguments by schema parameter name, but remember the extension executes just recipe parameters positionally.
- For example, for md5(file), call just_run with args like {"file": "/path/to/file"} and let the extension run \`just md5 /path/to/file\`.
- When keyed args skip an optional parameter that has a schema default, the extension fills that default automatically before executing the positional just recipe.
- For the research recipe, \`rounds\` means how many new rounds to run in this invocation, not a retry count for round 1 and not a total-to-date target.
- If the user asks for one research iteration or one more round, call research with \`{"rounds": "1"}\` and let the recipe append the next round automatically.
- When a research request clearly maps to the existing research recipe, run it directly instead of asking whether the user wants the next numbered round.
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
