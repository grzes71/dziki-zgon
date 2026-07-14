import subprocess
import time
import os

script_content = """
.logopen "c:/Users/grzes/Documents/Projects/witcher-atari-game/help_debug.txt"
.help
.logclose
.quit
"""

with open("temp_help.atdbg", "w") as f:
    f.write(script_content)

cmd = [
    "C:/Apps/Altirra-4.40/Altirra64.exe",
    "/debug",
    "/debugcmd",
    ".source c:/Users/grzes/Documents/Projects/witcher-atari-game/temp_help.atdbg",
    "dziki_zgon.xex"
]

print("Launching Altirra...")
proc = subprocess.Popen(cmd)

print("Waiting for process to exit naturally...")
try:
    proc.wait(timeout=10)
except subprocess.TimeoutExpired:
    print("Timeout! Killing...")
    proc.kill()

log_path = "c:/Users/grzes/Documents/Projects/witcher-atari-game/help_debug.txt"
if os.path.exists(log_path):
    print("Log created successfully!")
    with open(log_path, "r") as f:
        content = f.read()
        print(content[:1000])
        if ".saveimage" in content.lower():
            print("FOUND .saveimage!")
        if ".screenshot" in content.lower():
            print("FOUND .screenshot!")
else:
    print("Log not created.")
