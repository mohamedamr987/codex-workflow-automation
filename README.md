# codexflow

`codexflow` is a template-driven CLI for automating coding tasks with role-based prompts.

You can define reusable roles like `planning`, `testing`, and `review`, bind each role to a runner profile, and classify each role as `general` or `specific`.

## Features

- Local project config (`.codexflow/config.json`)
- JSON and YAML templates (`.codexflow/templates/*.json|*.yaml`)
- Starter templates for planning, testing, and review
- Template lifecycle commands: create, edit, rename, copy, show, delete, list
- AI-assisted template generation and updates from natural language (`codexflow ai`)
- Role scope metadata: `general` or `specific` with `specific_to`
- Runner profiles (multiple Codex setups)
- Per-template profile binding, with run-time profile override
- Variable placeholders in prompts: `{{task}}`, `{{root}}`, custom vars via `--var`
- Dry-run mode to preview prompts before execution

## Install

```bash
python -m pip install .
```

## Quick start

```bash
codexflow init
codexflow list
codexflow run testing "Add tests for login edge cases" --dry-run
```

## Create roles

General role:

```bash
codexflow create planner \
  --description "Planning specialist" \
  --role "You are a planning specialist for {{task}}." \
  --instructions "Return milestones and risks." \
  --scope general
```

Specific role:

```bash
codexflow create checkout-tester \
  --description "Testing role for checkout" \
  --role "You own test quality for {{specific_to}}." \
  --instructions "Design regression tests for {{task}}." \
  --scope specific \
  --specific-to checkout-service
```

Use YAML format:

```bash
codexflow create triage \
  --description "Bug triage role" \
  --role "Triage {{specific_to}} bugs" \
  --instructions "Classify severity for {{task}}" \
  --scope specific \
  --specific-to payments-api \
  --format yaml
```

## Edit and rename roles

```bash
codexflow edit checkout-tester --description "Checkout QA owner"
codexflow rename checkout-tester checkout-qa --format yaml
```

## AI create/update command

Use your configured runner (for example `codex`) to generate or update a template from plain language:

```bash
codexflow ai "Create a QA role focused on checkout regressions" --name qa-owner --runner-profile default --format yaml
```

- If `--name` is omitted: template name is auto-generated from your request.
- If template does not exist: it is created.
- If template exists: it is updated.

Force metadata while generating:

```bash
codexflow ai "Make this role general and reusable" --name qa-owner --scope general --bind-profile default
```

## Variables

Built-in variables during `run`:

- `{{task}}`
- `{{extra}}`
- `{{template}}`
- `{{description}}`
- `{{profile}}`
- `{{scope}}`
- `{{specific_to}}`
- `{{root}}`

Custom variables:

```bash
codexflow run triage "Investigate timeout" --var owner=qa-team --var priority=high --dry-run
```

Use `--strict-vars` to fail when placeholders are unresolved.

## Runner profiles

List profiles:

```bash
codexflow profile list
```

Add profile:

```bash
codexflow profile add codex-fast \
  --command codex \
  --arg --non-interactive
```

Set default profile:

```bash
codexflow profile default codex-fast
```

Set default template file format:

```bash
codexflow profile default-format yaml
```

## Commands

- `codexflow init [--force]`
- `codexflow list`
- `codexflow show <name>`
- `codexflow create <name> --description ... --role ... --instructions ... [--profile ...] [--scope general|specific] [--specific-to ...] [--format json|yaml] [--force]`
- `codexflow edit <name> [--description ...] [--role ...] [--instructions ...] [--profile ...|--clear-profile] [--scope general|specific] [--specific-to ...|--clear-specific-to]`
- `codexflow rename <source> <target> [--format json|yaml] [--force]`
- `codexflow copy <source> <target> [--format json|yaml] [--force]`
- `codexflow delete <name>`
- `codexflow run <name> <task> [--extra ...] [--profile ...] [--var KEY=VALUE] [--strict-vars] [--dry-run] [--print-command]`
- `codexflow ai <request...> [--name ...] [--runner-profile ...] [--bind-profile ...] [--scope general|specific] [--specific-to ...] [--format json|yaml] [--dry-run] [--print-command]`
- `codexflow profile list`
- `codexflow profile show <name>`
- `codexflow profile add <name> --command ... [--arg ...] [--prompt-mode stdin|arg] [--prompt-flag ...] [--force]`
- `codexflow profile remove <name>`
- `codexflow profile default <name>`
- `codexflow profile default-format <json|yaml>`

## Tests

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```
