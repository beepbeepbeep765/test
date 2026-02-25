# CLAUDE.md

This file provides context and guidance for AI assistants (Claude and others) working in this repository.

## Repository Overview

**Repository:** beepbeepbeep765/test
**Status:** Newly initialized — no source code has been added yet.

This repository was initialized with a single `.gitkeep` file. As the project grows, this file should be updated to reflect the actual codebase structure, conventions, and workflows.

---

## Current Repository Structure

```
/
└── .gitkeep    # Placeholder to initialize the repository
```

---

## Git Workflow

### Branches

- `master` — primary branch
- Feature/task branches follow the pattern: `claude/<description>-<session-id>`

### Standard Workflow

```bash
# Create and switch to a feature branch
git checkout -b <branch-name>

# Stage and commit changes
git add <files>
git commit -m "descriptive commit message"

# Push branch to remote
git push -u origin <branch-name>
```

### Commit Message Conventions

- Use the imperative mood: "Add feature" not "Added feature"
- Keep the subject line concise (under 72 characters)
- Describe *what* and *why*, not *how*

---

## Development Setup

> This section should be updated once the project has a defined tech stack, dependencies, and build system.

Typical setup steps to document here:
- Language/runtime version requirements
- Dependency installation commands (e.g., `npm install`, `pip install -r requirements.txt`)
- Environment variable configuration (e.g., `.env` file setup)
- Database or service initialization steps

---

## Build, Test, and Lint Commands

> Update these once the project tooling is established.

Document commands such as:

```bash
# Install dependencies
<install command>

# Run tests
<test command>

# Run linter / formatter
<lint command>

# Build / compile
<build command>
```

---

## Code Conventions

> Update this section as conventions are established.

### General

- Prefer clear, readable code over clever one-liners
- Delete unused code rather than commenting it out
- Keep functions small and focused on a single responsibility
- Avoid premature abstraction — only generalize when there are multiple concrete use cases

### File Naming

> Document file/directory naming conventions here (e.g., `kebab-case`, `PascalCase`, `snake_case`).

### Testing

> Document testing philosophy and requirements (e.g., unit vs. integration tests, coverage targets).

---

## AI Assistant Guidelines

When working in this repository, AI assistants should:

1. **Read before editing** — always read a file before modifying it.
2. **Minimal changes** — only change what is necessary for the task at hand; avoid refactoring unrelated code.
3. **No unnecessary files** — do not create documentation, READMEs, or helper files unless explicitly requested.
4. **Branch discipline** — always develop on the designated feature branch; never push directly to `master` without explicit permission.
5. **Clear commits** — write descriptive commit messages that explain the purpose of the change.
6. **Security** — do not introduce command injection, XSS, SQL injection, or other OWASP Top 10 vulnerabilities; validate input at system boundaries.
7. **Update this file** — if significant structural or workflow changes are made to the project, update `CLAUDE.md` to keep it current.

---

## Maintenance

This file should be updated whenever:
- A new tech stack, framework, or major dependency is introduced
- Build, test, or lint commands change
- New code conventions or style guides are adopted
- The project directory structure changes significantly
