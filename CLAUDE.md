# CLAUDE.md

This file provides context, conventions, and workflow guidance for AI assistants (e.g., Claude Code) working in this repository.

---

## Repository Overview

**Current state:** This repository is newly initialized and contains no application code yet. The only committed file is `.gitkeep`, which exists to initialize the repository.

As the codebase grows, this file should be updated to reflect the actual structure, tooling, and conventions in use.

---

## Git Workflow

### Branches

- `master` — primary integration branch
- `claude/<description>-<session-id>` — AI assistant working branches (auto-created per session)

### Commit Practices

- Write clear, imperative commit messages (e.g., `Add user authentication module`, `Fix null pointer in payment handler`)
- Keep commits focused: one logical change per commit
- Do not commit generated files, build artifacts, secrets, or `.env` files

### Push Protocol

- Always push with: `git push -u origin <branch-name>`
- Branches used by AI assistants must follow the `claude/` prefix convention
- Never force-push to `master`

---

## Development Conventions (to be updated as the project evolves)

### Adding New Code

- Prefer editing existing files over creating new ones
- Delete unused code rather than commenting it out or adding backwards-compatibility stubs
- Avoid premature abstractions — write the simplest code that works for the current requirement
- Do not add docstrings, comments, or type annotations to code you didn't change

### Security

- Never introduce command injection, XSS, SQL injection, or other OWASP Top 10 vulnerabilities
- Validate input only at system boundaries (user input, external APIs); trust internal code
- Never commit credentials, API keys, tokens, or secrets

### Dependencies

- Document any new runtime dependencies in this file once a package manager is set up
- Prefer well-maintained libraries with minimal transitive dependencies

---

## Testing (to be populated once a test framework is chosen)

- Run all tests before committing
- Tests should be deterministic and not rely on external network calls or shared state
- Add tests for new features and bug fixes

---

## AI Assistant Guidelines

### General Behavior

- Read files before modifying them — never propose changes to unseen code
- Use the minimum change necessary to accomplish the task
- Do not over-engineer: avoid extra configurability, feature flags, or hypothetical future requirements
- Do not add unrequested features or refactor surrounding code while fixing a bug

### When the Codebase Grows

Update the following sections of this file as the project matures:

| Section | Update When |
|---|---|
| **Project structure** | Directories and modules are established |
| **Build & run commands** | A build system, package manager, or Makefile is added |
| **Testing commands** | A test framework is configured |
| **Linting / formatting** | Code style tooling is introduced |
| **Environment variables** | A `.env.example` or config schema exists |
| **Deployment** | CI/CD or deployment pipelines are configured |

### Codebase Structure Template

Once source files are added, document the layout here, for example:

```
src/
  core/       # Domain logic
  api/        # HTTP handlers / routes
  db/         # Database access layer
  utils/      # Shared utilities
tests/
  unit/
  integration/
```

---

## Environment Setup (to be populated)

Document the following once the stack is decided:

- **Language / runtime version** (e.g., Node 20, Python 3.12, Go 1.22)
- **Package manager** (e.g., npm, pnpm, pip, cargo)
- **Install command** (e.g., `npm install`)
- **Run command** (e.g., `npm run dev`)
- **Test command** (e.g., `npm test`)
- **Lint command** (e.g., `npm run lint`)
- **Required environment variables** (reference `.env.example` if it exists)

---

## Updating This File

This file should be treated as living documentation. Update it whenever:

- New tooling, frameworks, or significant dependencies are introduced
- Project structure changes substantially
- Conventions are established or changed
- CI/CD or deployment processes are added

Last updated: 2026-02-19
