import os, secrets, random


def generateRandomString() -> str:
    return secrets.token_urlsafe(random.randint(10, 20))

template = open("template.c", "r").read()

for i in range(250):
    gener = generateRandomString()
    out = template.replace("{CONTENT}", gener).replace("{LENGTH}", str(len(gener)))

    open(f"shellcode.c", "w").write(out)

    os.system("/home/sijisu/binaryninja/plugins/scc --polymorph --arch x64 --pad --max-length 250 shellcode.c -o generated/"+gener)
