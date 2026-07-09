import sys
from py65.devices.mpu6502 import MPU

def load_xex(filename, memory):
    with open(filename, "rb") as f:
        data = f.read()
    
    i = 0
    while i < len(data):
        if data[i] == 0xFF and data[i+1] == 0xFF:
            i += 2
            if i >= len(data): break
        
        if i + 3 >= len(data): break
        start = data[i] | (data[i+1] << 8)
        i += 2
        end = data[i] | (data[i+1] << 8)
        i += 2
        
        length = end - start + 1
        if i + length > len(data): break
        chunk = data[i:i+length]
        
        for j, byte in enumerate(chunk):
            memory[start + j] = byte
            
        i += length

def load_labels(lab_file):
    labels = {}
    with open(lab_file, "r") as f:
        for line in f:
            parts = line.split()
            if len(parts) >= 3:
                try:
                    addr = int(parts[1], 16)
                    name = parts[2]
                    labels[name.upper()] = addr
                except ValueError:
                    pass
    return labels

def simulate():
    cpu = MPU()
    load_xex("dziki_zgon.xex", cpu.memory)
    labels = load_labels("gen/game.lab")
    
    print("Loaded dziki_zgon.xex")
    
    # OS ROM mock (RTI at NMI, XITVBV at $E462)
    # We don't really care about hardware, just want to see if it reaches Engine_WaitFrame
    cpu.memory[0xE462] = 0x68 # PLA
    cpu.memory[0xE463] = 0xAA # TAX
    cpu.memory[0xE464] = 0x68 # PLA
    cpu.memory[0xE465] = 0x40 # RTI
    
    # We mock Engine_WaitFrame so it doesn't loop forever waiting for NMI
    wait_frame_addr = labels.get("ENGINE_WAITFRAME")
    if wait_frame_addr:
        cpu.memory[wait_frame_addr] = 0x60 # RTS
    else:
        print("WaitFrame not found!")
        
    cpu.sp = 0xFF
    cpu.pc = labels["START"]
    
    steps = 0
    max_steps = 100000
    last_pc = cpu.pc
    
    # Let's trace execution
    path = []
    
    while steps < max_steps:
        pc = cpu.pc
        
        # Stop if we hit EngineScheduler loop
        if pc == labels.get("@GM"):
            print("Successfully reached @gm loop!")
            break
            
        path.append(pc)
        cpu.step()
        steps += 1
        
    if steps >= max_steps:
        print("Hung!")
        print("Last PC addresses:", [hex(p) for p in path[-20:]])
    else:
        print(f"Executed {steps} steps")

if __name__ == "__main__":
    simulate()
