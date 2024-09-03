# Progcodex
 - web/pwn
 - medium

## Platform Description
We desperately needed a new platform for our students' coding assignments. So we asked the best experts in the nation to create it for us. They say nowadays you don't need anything else than assembly. I guess they know what they are doing.

## Administrative Description
Service modeling a student assignment platform (like ReCodex or Progtest). The submission is a base64 encoded shell code that is then ran in sandbox. The sandbox utilizes base seccomp rules to block the most dangerous syscalls. The platform also allows sharing of submissions (sharetokens or usernames) and commenting on them.

## Vulnerabilities
flagstore1 - output of a submission
flagstore2 - comment on a submission

### Flagstore 1&2 - vuln 1 - Hardcoded secret
The server secret is hardcoded which allows for generation of arbitrary session JWT.

### Flagstore 1&2 - vuln 2 - Insecure sharetoken generation
The sharetoken is generated with simple xor with the server secret allowing for server secret exfiltration.

### Flagstore 1&2 - vuln 3 - Incorrect implementation of sharetoken
The sharetoken is incorrectly checked - `||` is used in place of `&&`, so all that is required to access is to for the parameter to be present.

### Flagstore 1&2 - vuln 4 - Broken UUID regex enabled RCE
The regex matching the UUIDs of the submission is missing the start and end characters, meaning that a RCE is possible through the run submission endpoint.

### Flagstore 1 - vuln 5 - Open and other unneeded syscalls allowed
The intended usage is just reading from a fd and writing output, so there is no need for those other syscalls as they can be misused - ie. open.

### Flagstore 1 - vuln 6 - x86 32bit mode is not forbidden
This allow for a seccomp bypass and allows to execute any syscall.

### Flagstore 2 - vuln 7 - noSQLi in the `/api/submissions/stats` endpoint
This allows to byte by byte leak a flag given flagID, like: `http://SERVICE:4567/api/submissions/stats?query={%22id%22:%22asdf%22,%22comments.comment%22:%20{%22$regex%22:%22not%20.*%22}}`.

## Patches
### Vuln 1
Change the secret in the configuration at the beginning of `main.rb` to something unguessable.

### Vuln 2
Change the share token generation, ie generate a random UUID.

### Vuln 3
Change the access check so it allows only valid sharetokens - in get submission, run submission and comment on submission.

### Vuln 4
Sanitize the uuid properly.

### Vuln 5
Change the model to allowlist and allow only the needed syscalls for reading and writing already open files - `read`, `write`, `sendfile`. Or at least block the most obvious ones, ie. open:
```
      BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, __NR_open, 0, 1),
      BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_KILL),
```

### Vuln 6
Block 32bit syscalls completely, ie like this:
```
      BPF_STMT(BPF_LD | BPF_W | BPF_ABS, (offsetof(struct seccomp_data, arch))),
      BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, AUDIT_ARCH_X86_64, 1, 0),
      BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_KILL),
```

### Vuln 7
Don't allow keys starting with `$` or similar fix.

## Deploy
The deployment is straight forward docker-compose.

Checker scripts are included in the `checkers` directory. One for each flagstore.
