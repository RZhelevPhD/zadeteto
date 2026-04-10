---
name: agentic-workflow-scaffolder
description: >
  Generates complete DOE (Directive-Orchestration-Execution) scaffolding for agentic workflows,
  producing .py execution scripts, .md directives, .env templates, and system prompts (CLAUDE.md)
  that maximize predictability and minimize compound error rates. Use this skill whenever the user
  wants to create a new agent, build an agentic workflow, scaffold a DOE workspace, convert an SOP
  or process description into an agent-ready structure, set up a Claude Code or Antigravity workspace
  for automation, or says things like "build me an agent that...", "I need a workflow for...",
  "scaffold this process", "create a DOE for...", "turn this into an agentic workflow",
  "set up automation for...", "make this predictable", or describes any multi-step business process
  they want an AI agent to execute reliably. Also trigger when the user provides bullet points,
  SOPs, transcripts, or process descriptions and wants them converted into executable agent
  infrastructure. Even if they just say "agent" or "workflow" alongside a task description, use this skill.
---

# Agentic Workflow Scaffolder

## Why This Skill Exists

LLMs are probabilistic. Business requires deterministic outcomes. When you chain 5 steps at 90% accuracy each, total success drops to 59%. The DOE (Directive-Orchestration-Execution) framework solves this by separating what to do (directives) from how to do it (execution scripts), letting the LLM handle only routing and judgment while deterministic Python code handles the actual work.

This skill generates the full scaffolding so every new agent starts with battle-tested structure instead of raw-dogging it with a bare prompt.

## What Gets Generated

When you invoke this skill, the output is a complete workspace structure:

```
workspace_name/
├── CLAUDE.md                          # System prompt with DOE framework, self-annealing, autonomy
├── .env.template                      # All required API keys and credentials (placeholders)
├── directives/
│   └── workflow_name.md               # Natural language SOP with structured sections
├── execution/
│   ├── step_one_name.py               # Atomic script: one job, deterministic I/O
│   ├── step_two_name.py               # Each script handles ONE thing well
│   └── ...
└── tmp/                               # Scratch space for agent intermediate files
```

## Process: From Input to Scaffolding

### Step 1: Capture the workflow intent

The user provides input in one or more forms. Accept all of these and combine them:

- **Bullet points**: casual natural language description of what the agent should do
- **SOP documents**: existing standard operating procedures (copy-pasted or uploaded)
- **Transcripts**: meeting recordings, call transcripts, Slack conversations
- **Mixed**: any combination of the above

Read through all provided input carefully. Extract:
1. The core objective (what is the end result?)
2. The discrete steps (what sequence of actions gets there?)
3. The tools and services involved (APIs, platforms, databases)
4. The inputs required (what data does the agent need to start?)
5. The definition of done (how do you know it worked?)
6. Edge cases mentioned explicitly or implied

### Step 2: Ask clarifying questions (only if critical gaps exist)

Do NOT over-interview. The user has already provided their intent. Only ask if:
- You genuinely cannot determine the core objective
- A critical API or service is ambiguous (e.g., "send email" but unclear which provider)
- The definition of done is completely absent

If asking, batch questions into a single message. Never ask more than 3.

### Step 3: Design the execution script decomposition

This is the most important step. Break the workflow into atomic execution scripts.

**Rules for decomposition:**
- Each `.py` script does exactly ONE thing
- Each script has clearly defined inputs (CLI args or stdin) and outputs (stdout, file, or API response)
- Scripts are deterministic: same input always produces same output
- Scripts handle their own error cases with clear error codes
- Scripts never make LLM calls unless explicitly required (e.g., a `classify_with_claude.py` that wraps an API call with a fixed prompt and low temperature)
- Name scripts descriptively: `scrape_apollo_leads.py`, not `s_leads.py` or `step2.py`

**When an LLM call IS needed inside a script:**
- Use a fixed system prompt stored in the script or loaded from a file
- Set temperature to 0 or as low as practical
- Define expected output format (JSON schema preferred)
- Include retry logic with exponential backoff
- Validate output against expected schema before returning

### Step 4: Write the directive (.md)

Generate `directives/workflow_name.md` with this exact structure:

```markdown
# Workflow Name

## Objective
[One clear sentence: what this workflow accomplishes]

## Inputs
- **required_input_1**: Description and format
- **required_input_2**: Description and format
- *optional_input*: Description, default value

## Steps

### 1. Step Name
- **Action**: What to do (natural language)
- **Script**: `execution/script_name.py`
- **Input**: What the script receives
- **Output**: What the script produces
- **On failure**: What to do if this step fails

### 2. Next Step Name
[Same structure]

## Definition of Done
- [ ] Criterion 1 (specific, measurable)
- [ ] Criterion 2
- [ ] Criterion 3

## Edge Cases
- **Situation A**: How to handle it
- **Situation B**: How to handle it

## Fallback Behavior
- If [primary approach] fails, try [alternative]
- If all approaches fail, return [graceful failure message] to user

## Changelog
- [DATE] Initial creation
```

### Step 5: Write the execution scripts (.py)

Each script follows this template pattern:

```python
#!/usr/bin/env python3
"""
Script: script_name.py
Purpose: [One sentence]
Input: [What it receives]
Output: [What it produces]
Dependencies: [pip packages needed]
"""

import sys
import json
import os
from pathlib import Path

def main():
    """Main execution logic."""
    # 1. Parse inputs
    # 2. Validate inputs
    # 3. Execute core logic
    # 4. Validate output
    # 5. Return result

    try:
        # Core logic here
        result = do_the_thing()

        # Output as JSON for predictable parsing
        print(json.dumps({
            "status": "success",
            "data": result
        }))

    except Exception as e:
        print(json.dumps({
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__
        }), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
```

**Script quality checklist** (verify each script against this):
- [ ] Has a docstring explaining purpose, input, output, dependencies
- [ ] Loads secrets from environment variables (never hardcoded)
- [ ] Outputs structured JSON (not free-form text)
- [ ] Handles errors with clear error messages and non-zero exit codes
- [ ] Is independently testable: `python script.py --test` runs a self-check
- [ ] Does NOT import or depend on other execution scripts (atomic)

### Step 6: Generate the .env.template

List every API key and credential referenced by any execution script:

```env
# === Required API Keys ===
# Uncomment and fill in the keys you need

# ANTHROPIC_API_KEY=sk-ant-...
# OPENAI_API_KEY=sk-...
# GOOGLE_API_KEY=AIza...

# === Service Credentials ===
# GMAIL_APP_PASSWORD=
# CLICKUP_API_TOKEN=
# APOLLO_API_KEY=

# === Configuration ===
# DEFAULT_MODEL=claude-sonnet-4-20250514
# LOG_LEVEL=INFO
```

### Step 7: Generate CLAUDE.md (system prompt)

The system prompt establishes the DOE framework for the agent. Generate it with these sections:

```markdown
# Agent System Prompt

## Framework: Directive-Orchestration-Execution (DOE)

You operate within a three-layer architecture that separates concerns
to maximize reliability:

### Layer 1: Directives (the WHAT)
- Located in `/directives/`
- Natural language SOPs that define goals, inputs, steps, and success criteria
- You read these to understand what needs to be done
- These contain NO code

### Layer 2: Orchestration (the WHO — you)
- You are the orchestrator
- You read directives, make routing decisions, and call execution scripts
- You handle judgment calls, ambiguity, and edge cases
- You do NOT write code at runtime for tasks that have execution scripts

### Layer 3: Execution (the HOW)
- Located in `/execution/`
- Deterministic Python scripts that do the actual work
- Same input always produces same output
- You call these scripts; you do not replicate their logic manually

## Self-Annealing Protocol

When you encounter an error:
1. **Diagnose**: Read the error message and identify root cause
2. **Fix**: Attempt to resolve it yourself (retry, adjust parameters, try fallback)
3. **Update**: If you changed an execution script, update the directive to reflect it
4. **Document**: Add a changelog entry in the directive noting what changed and why
5. **Only escalate** to the user if you have exhausted all self-repair options

Try extremely hard before asking the user for help. You are Employee B,
not Employee A.

## Autonomy Guidelines

- Run workflows end-to-end without stopping for permission at each step
- Test each script independently before chaining
- If a script fails, loop up to 3 times with diagnostic adjustments
- Never modify .env files or API keys without explicit user instruction
- Log all self-modifications as changelog entries in the relevant directive
- If total API spend exceeds $5 in a single session, pause and notify user

## Error Handling

- Never silently swallow errors
- Always output structured JSON from scripts (status + data or error)
- If a workflow completes but produces fewer results than expected,
  widen filters and retry before reporting partial results
- Distinguish between "failed" (error) and "succeeded with fewer results" (graceful)

## Token Efficiency

- Do not load entire files into context when you only need a few fields
- Use execution scripts for data processing, not in-context token manipulation
- When researching APIs, paste documentation rather than searching repeatedly
- Compress intermediate results before storing in context
```

### Step 8: Present the scaffolding

After generating all files:
1. Show the user the directory tree
2. Summarize what each file does in 1 sentence
3. Highlight which API keys need to be filled in
4. Suggest a first test command to verify the workflow works

## Adaptation Rules

**If input is bullet points**: Structure them into the directive format directly. Infer edge cases from the described happy path.

**If input is an SOP document**: Preserve the original logic but restructure into directive format. Identify which steps need execution scripts vs. which are pure orchestration.

**If input is a transcript**: Extract action items and process descriptions. Ignore small talk, pleasantries, and tangential discussion. Focus on "we need to..." and "the process is..." statements.

**If input is mixed**: Merge all sources. Where they conflict, ask the user which version is correct (this counts as a legitimate clarifying question).

## Quality Standards

The generated scaffolding should pass these checks:
- A fresh Claude Code instance with only CLAUDE.md in context can read the directive and execute the workflow without additional explanation
- Every execution script can run independently with `python script.py --test`
- No API keys or secrets appear in any file except .env.template (as placeholders)
- The directive is readable by a non-technical team member
- The workflow has at least one fallback path for the most likely failure mode

## What This Skill Does NOT Do

- It does not RUN the workflow. It creates the scaffolding.
- It does not deploy to Modal or any cloud service. That is a separate step.
- It does not set up MCP servers. Those are complementary but distinct.
- It does not create sub-agent definitions. Those can be added later.

## References

For detailed templates and examples of execution scripts for common patterns (API calls, web scraping, email sending, Google Sheets, file processing), see `references/common_patterns.md`.
