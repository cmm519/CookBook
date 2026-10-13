# prompts

Generated Module of Thought files go here. This folder starts with this README only.

Fill the three user files in order (`srs.template.md`, `architecture.template.md`, `structure.template.md`). Then run `prompt-generator.template.md` in Cursor Agent. The generator writes:

```
00-master-context.md
01-project-setup.md
02-dependencies.md
03-first-capability.md
tracking.md
```

`00-master-context.md` is Prompt 0. Reload it at the start of each implementation session. It is not an implementation step.

Numbered files are one capability each. Filename order is execution order. The names above are the pattern, not a required set. The generator chooses the names from your SRS, architecture, and structure.

`tracking.md` is the status matrix. The implementation guide updates it after each increment. Status values are `not started`, `green`, `yellow`, `red`, and `rolled back`.

Before stage 6, read the increment list. Every SRS ID from `srs.template.md` should appear on at least one increment, and the files should not add a part you did not name in `architecture.template.md`.

Do not put application code or leftover notes from an earlier product in this folder. When you reuse the template, delete the generated files and keep this README.
