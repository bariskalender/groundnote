# Security Policy

## Supported Version

Security fixes are currently applied to the latest `1.x` version of GroundNote. Older portfolio
snapshots are not maintained.

## Reporting a Vulnerability

Please do not publish exploitable details in a public issue. Use GitHub's private vulnerability
reporting feature for this repository if it is available. If it is not available, contact the
repository maintainer through a private channel already published on their GitHub profile before
sharing technical details. This project does not invent or publish an unverified security email
address.

Include a concise description, affected version, safe reproduction steps, and expected impact.
Never attach a private study document, `.env`, local database, log, prompt, embedding, generated
answer, model file, account screenshot, or secret. Build a minimal synthetic reproduction instead.

## Relevant Issues

Reports are especially useful for:

- path traversal or unsafe managed-file deletion;
- PDF/DOCX resource exhaustion or archive/XML validation bypasses;
- prompt injection that crosses the document-as-untrusted-evidence boundary;
- citation/source spoofing or retrieval of a deleted/incomplete document;
- accidental cloud or non-loopback network traffic;
- document, prompt, vector, path, or secret leakage in UI, logs, diagnostics, or release archives;
- arbitrary code execution through document parsing or setup/launcher scripts;
- broad process termination or launcher token/PID validation bypasses; and
- release archive boundary, symlink, checksum, or private-file inclusion failures.

## Local-Processing Scope

GroundNote is designed to keep application documents, prompts, embeddings, answers, and logs on the
local machine and to use Microsoft Foundry Local for inference. Initial dependency and model
downloads still require external package/model sources. GroundNote cannot protect data from a
compromised operating system, malicious local administrator, unsafe third-party runtime, or user
action outside the application.

The project is a portfolio desktop application, not a certified security product. Users should keep
their operating system and Foundry Local installation current, verify release checksums, protect the
local data directory, and avoid using highly sensitive documents on an untrusted computer.
