# Foundry Local Setup

GroundNote uses Microsoft Foundry Local for private, on-device chat and embedding inference.
Do not configure Azure OpenAI or another cloud model provider for this project.

## Windows 11

Install the Foundry Local CLI with the official Microsoft winget package:

```powershell
winget install Microsoft.FoundryLocal
```

Verify the CLI:

```powershell
foundry --version
foundry status
foundry server status
```

The installed preview CLI on this development machine is `0.10.2`. Microsoft Learn currently
documents `foundry service status`, but this CLI version exposes the daemon commands under
`foundry server`.

GroundNote uses the Windows ML Python package on Windows:

```powershell
uv sync
```

The Windows dependency is declared as `foundry-local-sdk-winml` with a Windows environment
marker. The cross-platform `foundry-local-sdk` package is declared only for macOS. Do not install
both SDK packages into the same Windows environment.

## macOS

Do not run these commands on Windows. They are provided for future macOS setup only.

```zsh
brew tap microsoft/foundrylocal
brew install foundrylocal
uv sync
```

On macOS, GroundNote should use `foundry-local-sdk`, not `foundry-local-sdk-winml`.

## Offline Behavior

First-time model downloads require internet access. After the required execution providers and
model files are cached locally, inference is expected to work offline.

## Phase 1 Verification Commands

```powershell
uv run python scripts/check_foundry.py
uv run python scripts/benchmark_models.py
```

The benchmark script intentionally loads models sequentially and uses short prompts.
