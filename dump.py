import sys
with open('dziki_zgon.xex','rb') as f:
    d=f.read()
i=0
while i<len(d):
    if d[i:i+2]==b'\xff\xff': i+=2
    if i+4>len(d): break
    s=d[i]+(d[i+1]<<8)
    e=d[i+2]+(d[i+3]<<8)
    print(hex(s), hex(e))
    i+=4+(e-s+1)
