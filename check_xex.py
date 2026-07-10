import sys

def parse_xex(filename):
    with open(filename, 'rb') as f:
        data = f.read()

    idx = 0
    if data[0] == 0xFF and data[1] == 0xFF:
        idx = 2

    segment_num = 1
    while idx < len(data):
        if idx + 4 > len(data):
            break
        
        # Check for 0xFFFF segment header
        if data[idx] == 0xFF and data[idx+1] == 0xFF:
            idx += 2
            continue

        start_addr = data[idx] | (data[idx+1] << 8)
        end_addr = data[idx+2] | (data[idx+3] << 8)
        idx += 4
        
        size = end_addr - start_addr + 1
        
        if start_addr <= 0xA3AF <= end_addr:
            offset = 0xA3AF - start_addr
            val = data[idx + offset : idx + offset + 4]
            print(f"FOUND at segment {segment_num}, address A3AF: {val.hex()}")
            
        if start_addr <= 0xA01B <= end_addr:
            offset = 0xA01B - start_addr
            val = data[idx + offset : idx + offset + 4]
            print(f"FOUND at segment {segment_num}, address A01B: {val.hex()}")
            
        idx += size
        segment_num += 1

parse_xex("dziki_zgon.xex")
