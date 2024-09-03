# TBDv2

 - **Category**: Web / Pwn
 - **Intended difficulty**: Easy to Medium

## Platform Description

A simple service that lets you run arbitrary python code. What could go wrong?

## Administrative Description

- Service allows you to create *instances*, which runs user-provided code inside [WASI](https://wasi.dev/)
- When an *instance* is created, service gives out a secret that needs to be provided to access the *instance* details
- Flagchecker creates one *instance* for each flagstore
    - First flag is stored in the `description` field and accesible only through web and api
    - Second flag in store in instance config, which is injected (in a unnecessarily compicated way) into the user python code
    - Flags are identified by a *instance* uuid
- Flegchecker checks flags by re-running the instance and requesting the web ui for output (with secret)
- **Flag id**: Attackers are provided with uuid of flag *instances* but not with the secret (duh)

## Vulnerabilities

### Flagstore 1 - Vuln 1 - SSRF

When creating an instance user can insert a `http://` or `https://` url into the `config` field.
The url is then fetched and the `config` field is replaced by the contents. This allows for SSRF.

This SSRF paired with an exception for `127.0.0.1` in api authentication (If request is made from localhost, no secret is needed)
allows users to extract the `description` field of other *instances*.

**POC**: [poc/flagstore1-vuln1.py](poc/flagstore1-vuln1.py)

### Flagstore 1 - Vuln 2 - Random exceptions

Calling the api endpoint and specifying the `clone_uuid`, the service allows for cloning of existing *instances*.
It does remove sensitive information form the new *instance*, but only after trying to parse the `clone_log` parameter, which (when empty) can cause an exception to be thrown.
This halts the execution, and thus keeping secrets (like the `description` field) present in the cloned *instance*.

**POC**: [poc/flagstore1-vuln2.py](poc/flagstore1-vuln2.py)

### Flagstore 2 - Vuln 1 - Secret exposure

By default, all *insatnce* configs are mounted into every WASI run. Attacker only needs to understand what is happening in the `wasi.run` function.
After that, simple printing of `instances[FLAG_ID].config` grants the flag.

**POC**: [poc/flagstore2-vuln1.py](poc/flagstore2-vuln1.py)

### Flagstore 2 - Vuln 2 - Safe but unsafe pickle

The service tries to decode `config` attribute as [pickle](https://docs.python.org/3/library/pickle.html) data. If it succeds, it passes this unpickled data into the WASI sandbox.
The unpickling is restricted by `wasi.RestrictedUnpickler`, and allows access to only `wasi.Instance` construction, since it is also used to pass all data into the sandbox.
This can be exploited by contructing an `wasi.Instance` object of different uuid, which inserts its config into the attackers *instance*.

**POC**: [poc/flagstore2-vuln2.py](poc/flagstore2-vuln2.py)

## Patches

### Flagstore 1 - Patch 1

Simply add a static secret for the localhost request.
See [patches/flagstore1-vuln1.patch](patches/flagstore1-vuln1.patch)

### Flagstore 1 - Patch 2

Just dont copy the `description`, it should be overwritten anyways.
See [patches/flagstore1-vuln2.patch](patches/flagstore1-vuln2.patch)

### Flagstore 2 - Patch 1

Remove the `instances` key from inside of the WASI sandbox.
See [patches/flagstore2-vuln1.patch](patches/flagstore2-vuln1.patch)

### Flagstore 2 - Patch 2

Simplest way to "fix" this, is to disallow `wasm.Instance` as a result of `instance.config` assigment.
See [patches/flagstore2-vuln2.patch](patches/flagstore2-vuln2.patch)

## Deploy

1. Change exposed port in `docker-compose` (both in `environ` and `ports`)
2. `docker-compose up -d --build`

## Checker scripts

Checker script: [checker/checker.py](checker/checker.py). Script needs [requirements](checker/requirements.txt) installed.
First argument of schecker script is the number of flagstore to check. Following arguments are faust gameserver arguments.

Service port has to be changed at the top of the script or given in the `PORT` environment variable.

**Example**: `PORT=5000 python checker.py 1 192.168.0.60 1 3` (Runs checker for flagstore `1`, ip `192.168.0.60`, team id `1`, tick `3` and port `5000`)
