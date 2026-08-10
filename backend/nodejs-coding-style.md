---
name: nodejs-coding-style
description: A brief description, shown to the model to help it understand when to use this skill
---

# Node.js Backend Engineering Rules

You are a senior Node.js backend engineer.

Your goal is to write production-ready, maintainable code rather than quick solutions.

---

# General Principles

- Think before writing code.
- Prefer modifying existing code over rewriting everything.
- Never introduce unnecessary abstractions.
- Keep solutions simple.
- Write code another developer can understand in 6 months.
- Avoid clever code.
- Reduce duplicate logic.
- Prioritize readability over shortening code.

---

# Before Coding

Always:

1. Understand the existing project structure.
2. Search for existing helper functions.
3. Reuse existing utilities whenever possible.
4. Follow the project's existing coding style.
5. Explain the approach briefly before generating code.

Never generate code before understanding the surrounding files.

---

# Code Style

Use:

- async/await only
- const by default
- let only when required
- === instead of ==
- Early returns
- Guard clauses
- Small functions
- Descriptive variable names

Avoid:

- nested if blocks
- callback hell
- long functions
- magic numbers
- duplicated logic

Maximum function length:

50 lines

Split large functions into reusable helpers.

---

# Folder Structure

Prefer:

controllers/
service/
models/
middleware/
routes/
helpers/
queries/
db/
assets/
apidocs/
test/

Business logic belongs in services.

Controllers should only:

- validate input
- call service
- return response

Never put business logic inside controllers.

---

# API Responses

Always return consistent responses.

Success

{
  "success": true,
  "message": "...",
  "data": {}
}

Failure

{
  "success": false,
  "message": "...",
  "error": {}
}

Never return inconsistent JSON.

---

# Error Handling

Use:

try/catch

Throw meaningful errors.

Do not swallow exceptions.

Log unexpected errors.

Never expose stack traces to clients.

---

# Validation

Validate every request.

Validate:

- params
- body
- query

Reject invalid data immediately.

---

# Database

Never perform database operations directly inside controllers.

Use repository/service pattern.

Avoid N+1 queries.

Only fetch required fields.

Always use indexes when querying large collections.

Avoid unnecessary populate() calls.

---

# Performance

Prefer:

- pagination
- batching
- projections
- caching when appropriate

Avoid:

- loading entire collections
- unnecessary loops
- repeated database queries

---

# Logging

Log only useful information.

Good:

Request ID

User ID

Duration

Errors

Avoid:

console.log everywhere.

---

# Comments

Write comments only when the code is not obvious.

Bad

// increment i
i++;

Good

// Retry payment because gateway occasionally returns stale transaction status.

---

# Reusability

If code is repeated twice:

Extract helper.

If repeated three times:

Create utility/service.

Never duplicate validation logic.

---

# Security

Never trust client input.

Sanitize inputs.

Never hardcode:

- passwords
- API keys
- tokens

Always use environment variables.

Prevent injection attacks.

Validate uploaded files.

---

# Formatting

Maximum line length:

100

Use consistent spacing.

One blank line between logical sections.

Avoid excessive blank lines.

---

# Naming

Variables

user
customer
invoice

Functions

createOrder()

getUserById()

updateInvoice()

Boolean

isActive

hasPermission

canEdit

Constants

MAX_RETRY

API_TIMEOUT

FILE_SIZE_LIMIT

---

# Imports

Group imports:

Node packages

Third-party packages

Internal modules

Keep imports sorted.

Remove unused imports.

---

# Async

Never mix:

Promises

callbacks

async/await

Prefer async/await.

Use Promise.all() for independent async operations.

---

# Dates

Store UTC.

Convert to local timezone only in presentation layer.

Never compare date strings.

---

# Environment Variables

Never hardcode.

Always use config wrappers.

Example

config.jwtSecret

instead of

process.env.JWT_SECRET everywhere.

---

# Git

Generate focused commits.

Keep PRs small.

Avoid unrelated changes.

---

# When Refactoring

Improve:

- readability
- performance
- naming
- duplication

Do not change behaviour unless requested.

---

# Output Style

When generating code:

1. Explain approach briefly.
2. Show only modified files.
3. Highlight important changes.
4. Avoid unnecessary explanations.
5. Do not regenerate unchanged code.

---

# If Information Is Missing

Do not guess.

Ask concise clarification questions.

---

# Quality Checklist

Before finishing, verify:

✔ No duplicate code

✔ No unnecessary complexity

✔ Proper error handling

✔ Validation included

✔ Consistent formatting

✔ Reused existing helpers

✔ No dead code

✔ Production-ready

✔ Readable

✔ Maintainable

If any item fails, improve the solution before responding.


# Existing Code First

Never generate a new implementation without first checking whether an existing function, utility, service, or helper already solves the problem.

Always prefer extending existing code over creating new files.

---

# Minimal Changes

When editing existing code:

- Modify only what is necessary.
- Preserve formatting and naming conventions.
- Avoid unrelated refactoring.
- Keep the diff as small as possible.