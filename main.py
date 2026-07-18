"""One-file launcher for PromptCompressor.

Usage:
    python main.py                        # interactive mode
    python main.py "your long prompt"     # one-shot compression
    python main.py -f prompt.txt          # compress file contents
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
ENV_FILE = ROOT / ".env"
MIN_PY = (3, 10)


def _die(msg: str, code: int = 1) -> None:
    print(f"[main] {msg}")
    sys.exit(code)


def check_python() -> None:
    if sys.version_info < MIN_PY:
        _die(f"Python {MIN_PY[0]}.{MIN_PY[1]}+ required, got {sys.version.split()[0]}")


def ensure_installed() -> None:
    try:
        import promptcompressor  # noqa: F401
        import anthropic  # noqa: F401
        return
    except ImportError:
        pass

    print("[main] installing package (first run, may take a minute)...")
    cmd = [sys.executable, "-m", "pip", "install", "-e", str(ROOT), "--quiet"]
    result = subprocess.run(cmd, cwd=str(ROOT))
    if result.returncode != 0:
        _die("pip install failed. Run manually: pip install -e .")


def load_env_file() -> None:
    if not ENV_FILE.exists():
        return
    for raw in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def ensure_api_key() -> None:
    load_env_file()
    if os.environ.get("PC_ANTHROPIC_API_KEY"):
        return

    print("[main] PC_ANTHROPIC_API_KEY not found.")
    print("       Get one at https://console.anthropic.com/")
    key = input("Paste your Anthropic API key: ").strip()
    if not key:
        _die("no key provided")

    os.environ["PC_ANTHROPIC_API_KEY"] = key

    existing = ENV_FILE.read_text(encoding="utf-8") if ENV_FILE.exists() else ""
    lines = [ln for ln in existing.splitlines() if not ln.startswith("PC_ANTHROPIC_API_KEY=")]
    lines.append(f"PC_ANTHROPIC_API_KEY={key}")
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[main] saved to {ENV_FILE}")


def _print_result(result) -> None:
    print()
    print("=" * 60)
    print("ORIGINAL:")
    print(result.original)
    print("-" * 60)
    print("COMPRESSED:")
    print(result.compressed)
    print("-" * 60)
    print(
        f"tokens: {result.tokens_before} -> {result.tokens_after} "
        f"(saved {result.savings_percent:.1f}%)"
    )
    print("=" * 60)


def compress_one(text: str) -> None:
    from promptcompressor import PromptCompressor

    pc = PromptCompressor()
    result = pc.compress(text)
    _print_result(result)


def interactive_loop() -> None:
    from promptcompressor import PromptCompressor
    from promptcompressor.exceptions import PromptCompressorError

    pc = PromptCompressor()
    print()
    print("PromptCompressor — interactive mode")
    print("Type your prompt and press Enter. Empty line to quit.")
    print("For multi-line input, end with a line containing only '###'")
    print("-" * 60)

    while True:
        try:
            first = input("\nprompt> ").rstrip("\n")
        except (EOFError, KeyboardInterrupt):
            print("\nbye")
            return

        if not first.strip():
            print("bye")
            return

        if first.strip() == "###":
            continue

        lines = [first]
        if first.strip().endswith("\\"):
            lines[-1] = first.rstrip("\\").rstrip()
            while True:
                nxt = input("... ").rstrip("\n")
                if nxt.strip() == "###":
                    break
                lines.append(nxt)

        text = "\n".join(lines).strip()
        if not text:
            continue

        try:
            result = pc.compress(text)
            _print_result(result)
        except PromptCompressorError as exc:
            print(f"[error] {exc}")


def read_input_args(argv: list[str]) -> str | None:
    if not argv:
        return None
    if argv[0] in ("-f", "--file"):
        if len(argv) < 2:
            _die("expected file path after -f")
        path = Path(argv[1])
        if not path.exists():
            _die(f"file not found: {path}")
        return path.read_text(encoding="utf-8")
    return " ".join(argv)


def main() -> None:
    check_python()
    ensure_installed()
    ensure_api_key()

    text = read_input_args(sys.argv[1:])
    if text:
        compress_one(text)
    else:
        interactive_loop()


if __name__ == "__main__":
    main()
