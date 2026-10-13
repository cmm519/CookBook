### CRITICAL REQUIREMENTS ###

You are generating Module of Thought prompts. You are not implementing the application.

**CRITICAL**: Read these files before you write anything:

1. `srs.template.md`
2. `architecture.template.md`
3. `structure.template.md`
4. `Module of Thought_instr.md`

**CRITICAL**: If any of the three template files still contains the characters `{{FILL:`, stop. Tell the user which file and which section is unfinished. Do not write prompt files.

**CRITICAL**: Create prompts only for the project named in `srs.template.md`. Honor the scope, out-of-scope list, and requirement table in that file. Honor the parts, stack, hard constraints, and decisions in `architecture.template.md`. Honor the tree, ownership table, and commands in `structure.template.md`.

**CRITICAL**: Do not add a requirement, a part, a screen, a folder, or a behavior that those files do not already name.

### What to write ###

**MANDATORY**: Write files only under `prompts/`. Do not create application code.

**MANDATORY**: Follow `Module of Thought_instr.md` for the master context, the one-capability increments, the critical checkpoints, and the tracking matrix.

Write these files:

1. `prompts/00-master-context.md` — Prompt 0. This is the context a later session reloads. Include:
   - Domain background taken from the SRS purpose, scope, users, and assumptions
   - Architecture overview taken from the context diagram, container diagram, parts, and decisions
   - The requirement index: every ID, statement, priority, and verification from the SRS table
   - Technical constraints and stack
   - Dependencies and the directory tree
   - Success metrics: the verification text and the build command that must succeed
2. `prompts/01-....md` onward — one increment per file. Number them so filename order is execution order. The first increments create the project skeleton and the dependencies from `structure.template.md` and the stack. Later increments add one capability each.
3. `prompts/tracking.md` — the matrix below, with one data row per increment and status `not started`.

### Each increment file ###

Sandwich the prompt: critical requirements at the beginning and again at the end.

Use `###` headers. Mark rules with **MANDATORY** and **CRITICAL**. Use bold and code blocks for paths, IDs, and commands.

Selective context: cite SRS IDs and file paths. Do not paste the whole SRS, the whole architecture, or the whole tree into the increment. Include only the IDs, paths, and contracts this increment needs.

Each increment contains:

- Header: increment number, capability name, `Standard` or `CRITICAL`, prior increments it depends on, and the SRS IDs it satisfies
- The one capability being added
- What may change, and what must stay as the earlier increments left it
- Implementation notes: paths taken from `structure.template.md`, integration points with parts from `architecture.template.md`
- Verification: the observation from the SRS verification column, plus any command from `structure.template.md` that applies
- File paths only from the structure tree. Behavior only from the cited SRS IDs
- If the user files do not give a function signature, write the smallest interface that satisfies the cited requirement and mark that interface `derived`. Do not present a derived signature as if the user wrote it

### Critical checkpoints ###

**CRITICAL**: Before you write the increment files, mark about 20 to 40 percent of them `CRITICAL`. Choose them for a real risk: first complex operation, an architectural boundary, conflicting requirements, a complexity jump, or the first integration of two parts.

A `CRITICAL` increment also contains:

- The risk
- How to recognize failure
- An isolation check that runs this increment without the rest of the new behavior
- A rollback to the previous increment file

A `Standard` increment does not contain that block.

### Tracking file ###

`prompts/tracking.md` uses this table. Fill Green from the SRS verification. Set Yellow to a weaker observation that still runs. Set Red to a failed build, a failed verification, or a broken constraint.

| Increment | File | SRS IDs | Status | Metric | Green | Yellow | Red |
| --- | --- | --- | --- | --- | --- | --- | --- |

Status starts as `not started`.

### CRITICAL REQUIREMENTS ###

Do not implement the project. Do not add components, operations, or files that `srs.template.md`, `architecture.template.md`, and `structure.template.md` do not list. Every increment maps to at least one SRS ID, except the skeleton and dependency increments, which map to the structure and the stack. A later agent must be able to implement a file without inventing behavior.
