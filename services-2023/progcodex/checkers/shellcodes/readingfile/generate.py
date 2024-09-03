import os, secrets, random

template = open("template.c", "r").read()

# input file: ../../../src/app/sandbox/inputs/graph.txt

for i in range(250):
    gener = random.randint(10, 10000)
    out = template.replace("{LENGTH}", str(gener))

    open(f"shellcode.c", "w").write(out)

    os.system("/home/sijisu/binaryninja/plugins/scc --polymorph --arch x64 --pad --max-length 250 shellcode.c -o generated/"+str(gener))
