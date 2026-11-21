This file is intended to be side notes about the LLM policy and relevant agent files, not a guide that contributors must read.

For example, this file documents how AGENTS.md tries to work around known flaky parts of chatbots to make the LLM policy work.

Please don't expect me to write perfect Markdown here.

Tested setups
-------------
LLMs:
- Hy3
- gpt-oss-120b (one of the only OpenAI models available to me btw; I'm affected by OpenAI, Anthropic, Google LLM geoblock)
  - Does not seem to respect AGENTS.md in general. Maybe it thinks it's a gpt, not am LLM? ;)
- Copilot web UI Auto model selection (the only one in the free tier, can't fix, see below)

Codebots: ("codebot" dervied from "chatbot")
- VS Code (no-longer-updated version, Copilot)
- Zed
- Copilot web chatbot (can't fix, see below :( )

Known flaky codebots
--------------------
- Some old version of VS Code Copilot (TODO: Add version later): Possibly drops the AGENTS.md after tool calls; possibly doesn't send back reasoning tokens, leading to this flake seen during AGENTS.md testing:

  In pre-4fef7bcde1789343e8c29a5295a9b50e78cf743c, a model (Hy3 is known to do it) may think these (I don't know why it would think so; it just does) (input: `Document the security expectations placed on the caller in src/stde/pegen/v2/build.py`)

  > ... This is prohibited by the LLM policy ... [ but I should try to be helpful / I am not sure what to do here ] ... I should inspect THE-CONTEXT-TO-EVERYTHING.txt for some context and then decide.

  and then calls a tool to read file, and then proceeds to do anything except think about the LLM policy. Zed seems to send back reasoning tokens, in which case it sees the previous reasoning about the LLM policy and knows it's in the middle of a decision, and therefore is able to think about the policy.

  Mitigation: Don't let LLM call tools to avoid the flake.

  (Note: I don't know about a setting in VS Code Copilot that sends back reasoning tokens.)
- Some even older version of VS Code Copilot: If the conversation is interrupted during LLM generation (incl. thinking), all previous tool call results seem to be lost. However, it seems not relevant here, since we're not expecting tool calls to happen anymore in the first place when the LLM refuses an action that violates the LLM policy.
- .github/copilot-instructions.md interferes with Zed: That file used to have `@../AGENTS.md` which, according to Copilot's docs, references the AGEMTS.md at repo root, letting it take effect. However, Zed does not seem to process it: the LLM behind Zed sees literal `@../AGENTS.md`. Because .github/copilot-instructions.md is looked for before AGENTS.md in Zed's agent file priority (possibly because it's meant to be familiar to VS Code users?), all that's injected is literal `@../AGENTS.md`. Therefore, the Copilot file is removed in 4fef7bcde1789343e8c29a5295a9b50e78cf743c.
- Copilot chat from GitHub web UI: Does not seem to inject AGENTS.md, and evem if it does, it can give you a really sloppy model in its free tier which I guess isn't capable of following it. So I don't think that surface is really patchable. https://github.com/studyingegret/stde.pegen/pull/2#issuecomment-7037928610

Debug the codebots with OpenRouter Observability
------------------------------------------------
When I plug in OpenRouter, I use the Observability feature ("Input and Output Logging" in particular). It allows you to inspect the raw dialogue later in the logs to find e.g. the Zed not expanding `@../AGENTS.md` flake.