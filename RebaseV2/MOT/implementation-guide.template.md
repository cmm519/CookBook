# CRITICAL REQUIREMENTS — Implementation guide

### MANDATORY DIRECTIVE ###

You are implementing the project described by the user files and the prompts already generated under `prompts/`.

**CRITICAL**: Read these files before you change the project:

1. `prompts/00-master-context.md`
2. `srs.template.md`
3. `architecture.template.md`
4. `structure.template.md`
5. `prompts/tracking.md`
6. `Module of Thought_instr.md`

**CRITICAL**: If `srs.template.md`, `architecture.template.md`, or `structure.template.md` still contains `{{FILL:`, stop. Do not write application code.

**CRITICAL**: If `prompts/00-master-context.md` or `prompts/tracking.md` is missing, stop. Tell the user to run `prompt-generator.template.md` first.

**CRITICAL**: If `architecture.template.md` names a primary design rule path, read that one `.mini.md` file and apply it while you write code. If the value is `none`, do not load a book rule. Do not open a second book. Do not paste the book file into the prompts.

### CRITICAL ###

Reload `prompts/00-master-context.md` at the start of every session. Then read `prompts/tracking.md` and continue from the first row whose status is not `green`.

## IMPLEMENTATION EXECUTION ORDER

### **CRITICAL**: Execute increment files in filename order

Run every `prompts/NN-*.md` file after `00-master-context.md`, in sort order. `00-master-context.md` is context, not an implementation step.

**MANDATORY**: Follow each increment as written. Do not change a path, a cited SRS statement, or a signature the increment specified. A `derived` signature may be adjusted only when the increment's verification cannot pass without the change, and you record the adjustment in `prompts/tracking.md`.

**MANDATORY**: Do not add a requirement, part, screen, or folder that the user files and the increment do not already name.

### **MANDATORY**: Verification between steps

**CRITICAL**: After each increment:

1. Fix errors from this increment before starting the next file.
2. Check new files sit on paths the increment named, and those paths exist in `structure.template.md`.
3. Check imports and references from this increment resolve.
4. Compare the result to the Green, Yellow, and Red text for this row in `prompts/tracking.md`.
5. Update that row's status to `green`, `yellow`, or `red`.

### **MANDATORY**: Red zone

**CRITICAL**: If a row is `red`, stop the sequence. Follow the degradation steps in `Module of Thought_instr.md`:

1. Isolate: run this increment without the later work.
2. Compare the failing behavior with the verification on the cited SRS IDs.
3. Check intermediate results at the boundary named in the increment.
4. Check the computation or transformation this increment added.
5. Apply the mitigation written on a `CRITICAL` increment, or roll back to the previous increment and set status to `rolled back`.

Do not start the next increment until this row is `green` or the user changes the increment file.

### **MANDATORY**: Final check

**CRITICAL**: After the last increment is `green`:

1. Run the build, run, and extra-check commands from `structure.template.md`. The build command must succeed.
2. Walk every `must` row in `srs.template.md` and confirm its verification holds.
3. Confirm the tree matches `structure.template.md`.
4. Confirm each part in `architecture.template.md` still has the job written there, and the decisions are intact.
5. If the build or run fails, use the failure checks in `structure.template.md` before trying a different fix.

### **MANDATORY**: Success

**CRITICAL**: The project is complete when every tracking row is `green`, the build command succeeds, every `must` requirement verifies, and the layout matches the structure tree.

### CRITICAL REQUIREMENT ###

**MANDATORY**: Later increments depend on earlier increments matching the prompt files. Do not invent features to fill gaps. If a prompt contradicts the SRS, stop and report the contradiction.
