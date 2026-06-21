#!/usr/bin/env python3
import os
import sys
import re
import time
import datetime
import getpass
import hashlib
import subprocess

START_TIME = time.time()

OS_NAME    = "Bri-ishOS"
OS_VER     = "1.0.0"
FS_DIR     = "/mnt"

# ══════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════

def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def clr():
    print("\033[2J\033[H", end="")

def bold(t):    return f"\033[1m{t}\033[0m"
def dim(t):     return f"\033[2m{t}\033[0m"
def cyan(t):    return f"\033[96m{t}\033[0m"
def green(t):   return f"\033[92m{t}\033[0m"
def yellow(t):  return f"\033[93m{t}\033[0m"
def red(t):     return f"\033[91m{t}\033[0m"
def white(t):   return f"\033[97m{t}\033[0m"

def spinner_task(label, duration):
    frames = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
    end_time = time.time() + duration
    i = 0
    while time.time() < end_time:
        print(f"\r  {cyan(frames[i % len(frames)])} {label}...", end="", flush=True)
        time.sleep(0.08)
        i += 1
    print(f"\r  {green('✓')} {label}            ")

def box(lines, width=64, title=""):
    inner = width - 4
    if title:
        t = f" {title} "
        top = "╔══" + t + "═" * (width - 4 - len(t)) + "╗"
    else:
        top = "╔" + "═" * (width-2) + "╗"
    bot = "╚" + "═" * (width-2) + "╝"
    print(cyan(top))
    for l in lines:
        stripped = re.sub(r'\033\[[0-9;]*m', '', l)
        pad = inner - len(stripped)
        print(cyan("║") + "  " + l + " " * max(0, pad) + "  " + cyan("║"))
    print(cyan(bot))

# ══════════════════════════════════════════════
#  LOGO
# ══════════════════════════════════════════════

LOGO_LINES = [
    r"  ██████╗ ██████╗ ██╗ █████╗ ██╗███████╗██╗  ██╗ ██████╗ ███████╗",
    r"  ██╔══██╗██╔══██╗██║██╔═══╝ ██║██╔════╝██║  ██║██╔═══██╗██╔════╝",
    r"  ██████╔╝██████╔╝██║█████╗  ██║███████╗███████║██║   ██║███████╗",
    r"  ██╔══██╗██╔══██╗██║╚════╝  ██║╚════██║██╔══██║██║   ██║╚════██║",
    r"  ██████╔╝██║  ██║██║        ██║███████║██║  ██║╚██████╔╝███████║",
    r"  ╚══════╝╚═╝  ╚═╝╚═╝        ╚═╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝",
]

def print_logo():
    for line in LOGO_LINES:
        print(cyan(line))
    sep = "  " + "─" * 71
    print(cyan(sep))
    print(cyan("  ") + white(f"  v{OS_VER}") +
          dim("  │  KDE Plasma · Wayland  │  pacman  │  by yosifmoroz"))
    print(cyan(sep))
    print()

# ══════════════════════════════════════════════
#  UI UTILS
# ══════════════════════════════════════════════

def installer_header(step=""):
    clr()
    print_logo()
    if step:
        print(dim(f"  {step}"))
        print()

def choose(prompt, options):
    while True:
        print(f"  {white(bold(prompt))}")
        print()
        for i, opt in enumerate(options, 1):
            label, desc = (opt if isinstance(opt, tuple) else (opt, ""))
            print(f"  {cyan(f'[{i}]')}  {bold(label)}" + (f"  {dim(desc)}" if desc else ""))
        print()
        raw = input(cyan("  › ")).strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return int(raw) - 1
        print(red("  Invalid choice.\n"))

def prompt_str(label, secret=False, default=""):
    fn = getpass.getpass if secret else input
    suffix = f" [{dim(default)}]" if default else ""
    while True:
        val = fn(f"  {white(label)}{suffix}: ").strip()
        if not val and default:
            return default
        if val:
            return val
        print(red("  Cannot be empty.\n"))

def validate_username(v):
    if re.match(r'^[a-z_][a-z0-9_-]{0,31}$', v):
        return True
    print(red("  Use lowercase letters, digits, _ or - only.\n"))
    return False

# ══════════════════════════════════════════════
#  PROFILES & ENGINE
# ══════════════════════════════════════════════

PROFILES = [
    ("Gaming",  "Steam · Lutris · Discord · MangoHud · GameMode · Wine",
     ["steam","lutris","discord","mangohud","gamemode","wine","heroic-games-launcher"]),
    ("Coding",  "VS Code · Git · Python · Node.js · Docker · GitHub CLI",
     ["code","git","python","nodejs","npm","docker","gh","base-devel"]),
    ("Casual",  "Firefox · VLC · Thunderbird · LibreOffice · GIMP",
     ["firefox","vlc","thunderbird","libreoffice-fresh","gimp"]),
    ("Minimal", "Base system only — you install what you want",
     []),
]

EXTRAS = [
    ("OBS Studio",      "Screen recording & streaming"),
    ("KeePassXC",       "Password manager"),
    ("Spotify",         "Music player (AUR)"),
    ("Neovim",          "Terminal text editor"),
    ("btop",            "Resource monitor (prettier htop)"),
    ("zsh + oh-my-zsh", "Better shell with themes & plugins"),
    ("Flatpak + Flathub","Flatpak app support"),
    ("Timeshift",       "System snapshot & restore"),
]

def main():
    # ── Step 1: Disk Scan ───────────────────────────
    installer_header("Step 1 / 5  ─  Disk Storage Allocation")
    
    disk_options = []
    try:
        disks_raw = subprocess.check_output("lsblk -dno NAME,SIZE", shell=True).decode().splitlines()
        for d in disks_raw:
            parts = d.split()
            if parts:
                disk_options.append((f"/dev/{parts[0]}", parts[1]))
    except Exception:
        pass
        
    if not disk_options:
        disk_options = [("/dev/sda", "500 GB (Virtual Drive Layout)")]
        
    disk_options.append(("Custom", "Enter manual partition handle"))
    
    disk_idx = choose("Select disk deployment target:", disk_options)
    disk = prompt_str("Disk path") if disk_idx == len(disk_options) - 1 else disk_options[disk_idx][0]

    # ── Step 2: System Profile ──────────────────────
    installer_header("Step 2 / 5  ─  Environment Presets")
    box([
        dim("Choose a preset desktop profile configuration blueprint."),
    ], width=64, title="Installation Profile")
    print()
    profile_idx = choose("Select deployment focus:", [(p[0], p[1]) for p in PROFILES])
    chosen_pkgs = list(PROFILES[profile_idx][2])

    # ── Step 3: Software Additions ──────────────────
    installer_header("Step 3 / 5  ─  Optional Feature Additions")
    for i, (name, desc) in enumerate(EXTRAS, 1):
        print(f"  {cyan(f'[{i}]')}  {bold(name)}  {dim(desc)}")
    print()
    print(dim("  Enter sequence numbers separated by spaces (or press Enter to skip)"))
    raw = input(cyan("  › ")).strip()
    for tok in raw.split():
        if tok.isdigit() and 1 <= int(tok) <= len(EXTRAS):
            chosen_pkgs.append(EXTRAS[int(tok)-1][0])

    # ── Step 4: System Identity ─────────────────────
    installer_header("Step 4 / 5  ─  Authentication & Host Parameters")
    while True:
        username = prompt_str("Administrator Username")
        if validate_username(username): break
    password = prompt_str("User Account Password", secret=True)
    while True:
        confirm = prompt_str("Confirm Account Password", secret=True)
        if password == confirm: break
        print(red("  Passwords mismatch error.\n"))
    hostname = prompt_str("System Local Hostname", default="bri-ishos")

    # ── Step 5: Master Commit Execution ─────────────
    installer_header("Step 5 / 5  ─  Verification Summary")
    box([
        f"  {dim('Target Drive :')}  {white(disk)}",
        f"  {dim('Profile Base :')}  {white(PROFILES[profile_idx][0])}",
        f"  {dim('Package Size :')}  {white(str(len(chosen_pkgs)) + ' customized targets loaded')}",
        f"  {dim('Primary User :')}  {white(username)}",
        f"  {dim('Target Host   :')}  {white(hostname)}",
        f"  {dim('Display Frame:')}  {white('KDE Plasma Engine (Wayland Master)')}",
    ], width=64, title="Deployment Configuration Map")
    print()
    go = input(f"  {yellow('Commit architecture matrix configuration plans?')} [{green('Y')}/{red('n')}]: ").strip().lower()
    if go == 'n':
        print(red("  Aborted framework initialization.")); time.sleep(1); return

    # ── Compilation Processors ──────────────────────
    clr()
    print_logo()
    print(cyan("  ┌─ Executing System Extraction Sequence ─────────────────────┐"))
    print(cyan("  │") + dim("  Do not detach live image partitions. Media mapping...     ") + cyan("│"))
    print(cyan("  └──────────────────────────────────────────────────────────┘\n"))

    steps = [
        ("Purging sector metadata indices tables", 0.6),
        ("Writing unique GPT hardware tracking headers", 0.8),
        ("Formatting EFI system boot layer (vfat)", 0.5),
        ("Allocating dynamic standard ext4 root spaces layout", 1.2),
        ("Mounting active partition directories to core tree", 0.4),
        ("Synchronizing remote secure software mirror links", 1.4),
        ("Injecting kernel package systems binaries targets", 3.0),
        ("Compiling KDE Plasma desktop frame libraries", 2.5),
        ("Generating hardware interface driver matrices", 1.5),
        ("Building local localization configuration definitions", 0.8),
        ("Registering secure credential authentication arrays", 0.7),
        ("Writing master system bootloader configurations (GRUB)", 1.2),
    ]

    for label, duration in steps:
        spinner_task(label, duration)

    print(green("\n  ✓ Bri-ishOS core platform successfully built to target storage drive!"))
    print(dim("  Safe to unmount installer flash storage. Enter 'reboot' to boot into your OS.\n"))

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(red("\n\n  [!] Installation sequence interrupted by user signal."))
