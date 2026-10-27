"""Environment and offline readiness verification script.

Run before running tests, demo, or pitch to verify all offline prerequisites.
Usage:
    python -m exporter.check_env
    python exporter/check_env.py
"""

import os
import sys
import shutil
import socket
import subprocess
from pathlib import Path

# Color helpers (ANSI)
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

REPO_ROOT = Path(__file__).resolve().parent.parent

def find_binary(name: str) -> str | None:
    # 1. Standard PATH
    found = shutil.which(name)
    if found:
        return found
    # 2. Check sys.prefix/Scripts
    candidate = Path(sys.prefix) / "Scripts" / (name + ".exe")
    if candidate.exists():
        return str(candidate)
    candidate_unix = Path(sys.prefix) / "bin" / name
    if candidate_unix.exists():
        return str(candidate_unix)
    # 3. Check known Windows paths
    dl_ffmpeg = Path(r"C:\Users\ayush\Downloads\ffmpeg-9.0.2-essentials_build\ffmpeg-9.0.2-essentials_build\bin") / (name + ".exe")
    if dl_ffmpeg.exists():
        return str(dl_ffmpeg)
    return None

def check_python_version() -> tuple[bool, str]:
    v = sys.version_info
    ver_str = f"{v.major}.{v.minor}.{v.micro}"
    if v.major >= 3 and v.minor >= 10:
        return True, f"Python {ver_str}"
    return False, f"Python {ver_str} (< 3.10)"

def check_import(module_name: str) -> tuple[bool, str]:
    try:
        mod = __import__(module_name)
        ver = getattr(mod, "__version__", "installed")
        return True, f"{module_name} ({ver})"
    except Exception as e:
        return False, f"{module_name} ({e.__class__.__name__})"

def check_bin(name: str) -> tuple[bool, str]:
    bin_path = find_binary(name)
    if not bin_path:
        return False, f"{name} not found on PATH or in venv"
    try:
        res = subprocess.run([bin_path, "-version"], capture_output=True, text=True, timeout=5)
        first_line = (res.stdout or res.stderr).splitlines()[0]
        return True, first_line[:40]
    except Exception as e:
        return False, f"Error running {name}: {e}"

def check_chromium() -> tuple[bool, str]:
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("about:blank")
            browser.close()
        return True, "Playwright Chromium launch successful"
    except Exception as e:
        return False, f"Playwright Chromium launch failed: {e}"

def check_ollama() -> tuple[bool, str]:
    import urllib.request
    import json
    url = "http://127.0.0.1:11434/api/tags"
    model_name = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "check_env"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        models = [m.get("name", "") for m in data.get("models", [])]
        model_found = any(model_name in m for m in models)
        if model_found:
            return True, f"Reachable; {model_name} available in {models}"
        else:
            return False, f"Reachable, but {model_name} NOT in {models}"
    except Exception as e:
        return False, f"Ollama unreachable at {url} ({e})"

def check_local_files() -> list[tuple[str, bool, str, bool]]:
    """Checks local model checkpoint directories and font files."""
    results = []
    
    # Fonts
    fonts_dir = REPO_ROOT / "renderer" / "assets" / "fonts"
    has_fonts = fonts_dir.exists() and any(fonts_dir.glob("*.ttf")) or any(fonts_dir.glob("*.otf"))
    results.append((
        "Noto Fonts",
        has_fonts,
        f"{fonts_dir} ({'found' if has_fonts else 'empty or missing'})",
        False # Informational until Farhan/Tarun commit assets
    ))
    
    # Kokoro weights & voices
    kokoro_found = False
    kokoro_dirs = [
        REPO_ROOT / "models" / "kokoro",
        Path.home() / ".cache" / "kokoro",
        Path(r"C:\Users\ayush\Desktop\Hackathon\kokoro")
    ]
    for kd in kokoro_dirs:
        if kd.exists() and (any(kd.glob("*.onnx")) or any(kd.glob("*.pth")) or any(kd.glob("*.bin"))):
            kokoro_found = True
            break
    results.append((
        "Kokoro Weights/Voices",
        kokoro_found,
        "Found in local models/cache" if kokoro_found else "Not found in local cache",
        False
    ))
    
    # IndicTrans2 checkpoint
    it2_found = False
    it2_dirs = [
        REPO_ROOT / "models" / "indictrans2",
        Path.home() / ".cache" / "huggingface" / "hub"
    ]
    for itd in it2_dirs:
        if itd.exists() and any(itd.glob("*indictrans2*")):
            it2_found = True
            break
    results.append((
        "IndicTrans2 Checkpoint",
        it2_found,
        "Found in cache/models" if it2_found else "Not found in cache",
        False
    ))
    
    return results

def check_offline_flags() -> tuple[bool, str]:
    hf = os.environ.get("HF_HUB_OFFLINE")
    tf = os.environ.get("TRANSFORMERS_OFFLINE")
    if hf == "1" and tf == "1":
        return True, "HF_HUB_OFFLINE=1 and TRANSFORMERS_OFFLINE=1 set"
    return False, f"Flags not set: HF_HUB_OFFLINE={hf}, TRANSFORMERS_OFFLINE={tf}"

def check_real_offline() -> tuple[bool, str]:
    """Tests if real outbound internet connection is blocked."""
    try:
        # Try pinging Cloudflare DNS
        s = socket.create_connection(("1.1.1.1", 53), timeout=1.5)
        s.close()
        # If connection succeeded, Wi-Fi is still on
        return False, "Outbound network active (Wi-Fi ON - warn for rehearsals/demo)"
    except Exception:
        return True, "Outbound network unreachable (Wi-Fi OFF or air-gapped)"

def check_gpu() -> tuple[bool, str]:
    smi = shutil.which("nvidia-smi") or find_binary("nvidia-smi")
    if not smi:
        return True, "nvidia-smi not found (CPU mode fallback)"
    try:
        res = subprocess.run(
            [smi, "--query-gpu=name,memory.total,memory.free", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5
        )
        if res.returncode == 0 and res.stdout.strip():
            parts = [p.strip() for p in res.stdout.strip().split(",")]
            name = parts[0]
            free_mb = int(parts[2]) if len(parts) > 2 else 0
            if free_mb < 3000:
                return False, f"{name}: {free_mb} MB free (< 3 GB free VRAM)"
            return True, f"{name}: {free_mb} MB free VRAM"
        return True, "nvidia-smi query returned empty"
    except Exception as e:
        return True, f"GPU query error ({e})"

def main() -> int:
    # Auto-enable ANSI colors in Windows console
    if sys.platform == "win32":
        os.system("")

    print(f"\n{BOLD}{CYAN}=== Blue Visual Teacher: Environment & Offline Readiness Check ==={RESET}\n")

    # (Category, Name, Status, Message, Required)
    checks: list[tuple[str, str, bool, str, bool]] = []

    # 1. Python version
    py_ok, py_msg = check_python_version()
    checks.append(("Core", "Python Version", py_ok, py_msg, True))

    # 2. Key imports
    modules_required = [
        ("pydantic", True),
        ("fastapi", True),
        ("uvicorn", True),
        ("playwright", True),
        ("numpy", True),
        ("soundfile", True),
        ("scipy", True),
        ("ollama", True),
        ("torch", False),          # Optional until localization is wired
        ("transformers", False),   # Optional until localization is wired
        ("IndicTransToolkit", False),
        ("kokoro", False),
    ]
    for mod_name, req in modules_required:
        ok, msg = check_import(mod_name)
        checks.append(("Imports", mod_name, ok, msg, req))

    # 3. Binaries
    for b in ["ffmpeg", "ffprobe"]:
        ok, msg = check_bin(b)
        checks.append(("Binaries", b, ok, msg, True))

    # 4. Chromium
    cr_ok, cr_msg = check_chromium()
    checks.append(("Browser", "Playwright Chromium", cr_ok, cr_msg, True))

    # 5. Ollama
    ol_ok, ol_msg = check_ollama()
    checks.append(("Ollama", "Daemon & Model", ol_ok, ol_msg, False))

    # 6. Local files
    for name, ok, msg, req in check_local_files():
        checks.append(("Assets", name, ok, msg, req))

    # 7. Offline Flags
    fl_ok, fl_msg = check_offline_flags()
    checks.append(("Flags", "Offline Envs", fl_ok, fl_msg, False))

    # 8. Real Offline Socket Test
    off_ok, off_msg = check_real_offline()
    checks.append(("Air-gap", "Outbound Network", off_ok, off_msg, False))

    # 9. GPU
    gpu_ok, gpu_msg = check_gpu()
    checks.append(("Hardware", "GPU VRAM", gpu_ok, gpu_msg, False))

    # Print table
    header = f"{'Category':<10} | {'Check':<24} | {'Status':<8} | {'Details'}"
    print(header)
    print("-" * 80)

    any_required_failed = False
    for cat, name, ok, msg, req in checks:
        if ok:
            status_str = f"{GREEN}PASS{RESET}"
        else:
            if req:
                status_str = f"{RED}FAIL{RESET}"
                any_required_failed = True
            else:
                status_str = f"{YELLOW}WARN{RESET}"
        
        req_suffix = " *" if req else "  "
        print(f"{cat:<10} | {name + req_suffix:<24} | {status_str:<17} | {msg}")

    print("-" * 80)
    print("  * = Required for current backend milestone\n")

    if any_required_failed:
        print(f"{RED}{BOLD}[FAIL] Some required checks failed. See details above.{RESET}")
        return 1
    else:
        print(f"{GREEN}{BOLD}[PASS] All required environment checks passed!{RESET}")
        return 0

if __name__ == "__main__":
    sys.exit(main())
