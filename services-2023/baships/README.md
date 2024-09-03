# service02 - BaShips
 - Category: misc
 - Difficulty: medium

## Platform Description
*In far far sea our heroes are set on mission to find traces of lost civilizations... Our heroes are equiped with ship and prehistoric technology called "radio". All they really need is some bashic knowledge...*

## Administrative Description
Service enables users to operate a ship. Communication is realized through simple text protocol/shell. Upon connection, user is prompted for login and if login is successful, user is given access to "control panel" for its ship. Each ship have ID and name.

Service data are stored as text files in "data" folder (`/opt/baships/data`). Service consists of several components - movement, signals/radio and reports.

There are two flag stores: "Flag ship" and "Reports". "Flag ship" flagstore is name of ship that's far away from origin, "Reports" flagstore have flag stored in certain report.

### Movement
Ships can move around via command `move <X> <Y>`. There is 2D map with origin <0,0> where all ships start. There is limitation for how big distance can ship travel in one move. Move is not instant and user have to wait for `move` command to finish.

User can decide to "adrift" via command `adrift`. This drifts ship back to origin if its not already there and far away from origin if it is already at origin.

User can also decide to scuttle the ship. It changes ship status to "not operational" and disables it. Ship will sink and will be left where it is. Session/Connection is closed after scuttle and futher attempts to connect back will fail.

### Signals/Radio
Ships are equiped with radio. Radio can be activated/used with command `radio <COUNT> <MODULATION>` - `COUNT` is requested number of signals to receive and `MODULATION` (= string) is modulation that should be used.

`radio` command gives back (after some time) hexencoded data. Data have custom encoding that needs to be reversed (or decode function needs to be scraped from application). Data have specified format in which is encapsulated information about "interferences" and "signals". "Interferences" are other ships at same place - this contains info about ship (ID and name). "Signals" are randomly generated captured signals consisting of "source" (= identificator) and its "signature" (= random data).

*Note: Modulation isn't really used anywhere. Originally there was idea to place flag "into modulation" but that somehow didn't happened because report system was intended in different way than it is now.*

#### Signal data specification
```
   Byte: 00000000 11111111 22222222 33333333 44444444 55555555 66666666 77777777 88888888
    Bit: 76543210 76543210 76543210 76543210 76543210 76543210 76543210 76543210 76543210
Meaning: x####### #x###### ##x##### ###x#### !!!!!!!! ####x### #####x## ######x# #######x
         ↑      ↑                               ↑
        MSB    LSB                         Parity block
Meanings:
    # = original data
    x = modulated bits = XOR with modulation string
    ! = parity bit = original byte parity (0 = even, 1 = odd)

"Parity block" consists of parity bits of other blocks ("parity bit" = bit in "parity block"):
+-----------------+-----------------------+
| Nth parity bit  | Parity for Nth block  |
+-----------------+-----------------------+
|        7        |           0           |
|        6        |           1           |
|        5        |           2           |
|        4        |           3           |
|        3        |           5           |
|        2        |           6           |
|        1        |           7           |
|        0        |           8           |
+-----------------+-----------------------+

=> One encoded block has 9 bytes (= 4B data + 1B parity + 4B data)
=> Original data are grouped into groups by 8B, each group is "modulated" with one byte, one byte in group is modulated by one bit

Group is modulated with "GROUP_NUM % MODULATION_LEN" byte from modulation.
```

##### Example
```
Data:       01111110 01100000 01011101 00001100 11101001 00100011 00100101 00001010
Modulation: 11011110

Parity:
   Data:       01111110 01100000 01011101 00001100 11101001 00100011 00100101 00001010
=> Bit count:     6        2        5        2        5        3        3        2
=> Parity:        0        0        1        0        1        1        1        0
=> Parity block: 00101110

Modulation:
   Data:       01111110 01100000 01011101 00001100 11101001 00100011 00100101 00001010
   Modulation: 1         1         0         1         1         1         1         0
=> Modulated:  11111110 00100000 01011101 00011100 11100001 00100111 00100111 00001010

Result:
   11111110 00100000 01011101 00011100 00101110 11100001 00100111 00100111 00001010
   |---------------------------------| |------| |---------------------------------|
                Modulated               Parity               Modulated
```

### Reports
Radio output can be reported/submited to generate "report" via command `report <HEX_ENCODED_RADIO_DATA>`. This parses data and transforms them into report which will be saved. Output of command is report password and ID.

We need to know ID of report that we want to access and its password. If we know both of these values, we can obtain report with `retrieve <REPORT_PASSWORD> <REPORT_ID>`.

Report contains summary of gathered signals and also information about in which other reports have current/our signal sources appered.

We can search reports by signal source with `find <SOURCE>` - it returns list of report IDs which contains given source.

## Vulnerabilities
### Flag ship - Awk "overflow"/big numbers
`move` command checks if move is allowed via `awk` (because computing square root in bash is not really possible) but in way in which it can be exploited. `awk` can be invoked by suppling very large number(s) that `awk` "can't handle" and returns "inf"/"-inf" (or "nan"/"-nan" in some cases). This string gets interpreted as variable in artitmetic context but this results in 0 as there is no varible named "inf" (or "nan"). That means that expression `(( "$distance" < "$max_distance" ))` (=> `(( 0 < 5 ))`) gets evaluated as true (`$distance` is output from `awk`).

Exploit: [flagship_math.py](/exploits/flagship_math.py)

#### Patch
There is no pretty patch but simpliest is probably just to cut number input to e.g. max 30 chars/digits (it can be "easily" done in `process_int` (`input.sh`)) e.g. with `head -c 30`.

#### Exploit
This cannot be exploited "directly" but we must do one extra ~~step~~ `move` because although flag ship is far away it is not that far away to trigger this bug. So we first need to move very very far away and after that move to target location - this way both moves trigger bug and allows us to move where we want. ~160 digits is enough to perform an exploit.

#### Extra notes
`awk` is little bit tricky in this situations and exploit worked little bit different before service started using `awk`s variables. Original exploit worked by overflowing max (float) number and `awk` ended with error which wasn't properly handled by logic and it (wrongly) determinated that move is valid (this logic is now rewrited). This is no longer the case because it appears that `awk` trims(?) input variables.

Similiar "issue" raises when we supply not that big numbers ("only" ~10 digits) as `awk` will output such numbers in sciencific notation (e.g. 1e123) which bash doesn't understands. Bash will complain about "error token 1e" but current logic is written in way in which it gets interpreted as invalid move.

### Flag ship - Rename
Function `read_line` in `input.sh` is flawed. Its goal is to read one line and "normalize" it (= remove extra spaces). Function does this by simply echoing (unquoted) user input (`echo $input`) so that "normalization" is left to bash. However this "exploitable". We can supply `-e` and this gives us ability to add special characters to our input - most important is newline which is otherwise impossible to get. This can be used to exploit `rename` function.

Exploit: [flagship_rename.py](/exploits/flagship_rename.py)

#### Patch
This problem is actually kinda tricky to fix because `echo` doesn't really care about `--` (it will treat it as normal string) and `-E` can be simply overwritten. So we are left with several options. We can either sanitize user input, use something different than `echo` (`printf`), do "normalization" by ourself or sanitize/filter that input somewhere futher by removing newlines. I personally suggest doing normalization by ourself using e.g. `tr` (`tr -s " " " " <<<"$input"`).

Note that first obvious fix would be to quote variable. This is working patch for exploit but it breaks the service - this change removes "normalization" entirely and checker will be sad.

#### Exploit
We can take advantage of newline in input in conjuction with `rename` command. Ship data are stored like this:
```
0
Ship Alfa Bravo Charlie
100 200
```
First line is "boolean" indicating if ship is destroyed or not, second line is ship name and last line is position of ship as "X Y". If we rename our ship to name with newline in it, then string after newline will be where position is expected. This means that we can set our position to any value.

Exploit can look like this: `-e rename My support vessel\\n500 -500`. Double backslash is because we need to escape backslash in `read` command which is using it to escape special characters. We need to save ship after rename and load it back to see some effect so we just disconnect and login again and we should be at our desired location.

I mentioned that `read` uses backslash to escape special characters... and one of these characters is newline. So can we just write/send backslash and newline and be happy? No, because this backslash-newline means line-continuation so it basically acts like nothing. What it is good for? I don't know.

### Reports - Wrong password generation
Reports are protected by passwords. These passwords are based on random ID so nobody can ever break that, right? Right? Well that would be true if that ID wouldn't be public information (flag id).

Exploit: [reports_password.py](/exploits/reports_password.py)

#### Patch
Just do something else. Most obvious fix is probably use same thing like line above for ID generation (`$(generate_id 32)` - you can even pick larger number if you feeling unsafe).

#### Exploit
Exploit this is very easy, just take ID of report you want to access and compute password like application does it: `password=$(echo -n reportID | sha256sum | cut -d " " -f 1 | xxd -ps -r | base64 | head -c 30)`. Now you have password to target report and you can simply retrieve it.

### Reports - Cross report source references
Reports contain info about other reports that includes same signal source(s). This information is obtained with `grep` running on all other reports. User input (signal source from report ← decoded data ← user input) is passed into `grep` pattern without any sanitization.

Exploit: [reports_source_grep.py](/exploits/reports_source_grep.py)

#### Patch
We need to sanitize input, e.g. with `tr -d`. It should be enough to just remove `(` or `)` so simple substitution is all we really need (`${x//(/}`).

#### Exploit
We can exploit this by modifing regex to match on flag format and reject everything else. If our input is be `xxxxx)|(  TARGET_SOURCE[9-;]FLAG_)|(xxxxx`, it will result into following regex pattern: `^    > (xxxxx)|(  TARGET_SOURCE[9-;]FLAG_)|(xxxxx): [0-9]+$`. This matches on signal signatures from target source starting with "FLAG_" (target signal source is known from flag id). `[9-;]` is for matching `:` (we cannot use it directly as it would mess up our input during parsing). Regex could be little bit simplified (e.g. for matching only `FLAG_`: `xxxxx)|(  .*[9-;]FLAG_)|(xxxxx`).

Note that we need to match **only** at signal signatures (and not counts) because of flag/argument `-m 1` in `grep` command which tells `grep` to find only first match. This is reason why there are "xxxxx" strings at the start and at the end.

### Reports - Unquoted file name
There is an unquoted variable when reading file in one of the final commands of function `report.show` which enables to read multiple files instead of one when input contains space. Also input to `report.show` is not sanitized - this allows arbitrary file read if we know its first line.

This vulnerability comes in second variant in which we can exploit unsanitized signal sources which allows to append some data (report ID) to arbitrary file.

Exploit: [reports_retrieve_unquoted_0.py](/exploits/reports_retrieve_unquoted_0.py) (first variant), [reports_retrieve_unquoted_1.py](/exploits/reports_retrieve_unquoted_1.py) (second variant)

#### Patch
Fix is as simple as to quote `$2` in `tail` command.

If we want patch whole thing (but it shouldn't be exploitable after previous fix), we need to sanitize input (again). We would like to remove all slashes and/or dots from signal sources and/or reports but we can't do that as these are allowed characters (and checker likes them). So we need something (just little) more clever... What we can do is remove (sub)string: `../`. Substring is needed for exploitation so removing it is enough to break exploit. We can achieve this by variable string substituion (`${x/..\//}`) in/for `report.show` input. To fix "second variant" we need to do same thing but for signal sources.

#### Exploit
Idea is to read multiple files at once by requesting to `retrieve SOME_KEY SOMETHING TARGET_REPORT`. Problem is that password check is done "right" (with quoted variable) so we need file `SOMETHING TARGET_REPORT` to exists and we need to know its first line (= `SOME_KEY`). We can create file with space by creating report with signal source "SOMETHING TARGET_REPORT". If we are sure that "SOMETHING TARGET_REPORT" didn't exists before (so it was created when our report was parsed) then first line in that file should be ID of generated report. Now we want to send `retrieve GENERATED_REPORT_ID ../sources/SOMETHING TARGET_REPORT` and we should get report.

There is an alternative way in which we can do exploit other way around - we can introduce signal source "../stored/SOMETHING TARGET_REPORT" and then ask to `retrieve GENERATED_REPORT_ID SOMETHING TARGET_REPORT`.

Side note - shouldn't it be "GENERATED_REPORT_PASSWORD" (instead of ID)? No because application is trying to store information about which report (ID) contains given signal source by simply appending new report ID to target file.

### General - Multiple sessions / Session desync
This is not really a vulnerability but "only" bug. We can open multiple session with same user/ship. This can lead to some interesting consequences as ship/state is saved only after disconnection (and renaming). This means that we can e.g. "save" ship state by openning second session which will be closed after first one (so we end up with original state).

It is not exploitable in any way (atleast as far as I'm aware) so it is just some interesting fact.

## Deploy
This is bash service. It works in its initial state but things can get really messy once somebody tries to change anything as there are some many things that can go wrong... It nearly appears that bash wasn't intended as "language" for writting server applications... :)

Expected bash version is 5.2+. There is RCE in lower versions so make sure that used bash is up-to-date. I know that (atleast [some](https://mywiki.wooledge.org/BashPitfalls#pf61) [variants](https://mywiki.wooledge.org/BashPitfalls#pf62) of) RCE doesn't works in 5.2 and I think that it is [this change](https://git.savannah.gnu.org/cgit/bash.git/tree/NEWS?h=bash-5.2#n40) but I'm not really sure (I spent several hours building and trying older bash versions to find out which are affected and ended up my search with 5.2 which appears to be first not affected version).

There is still [one similar issue](https://mywiki.wooledge.org/BashPitfalls#pf46) (`x='something[$(date 1>&2)]'; echo $((x+1))`) that works but I don't think that it can be exploited here. Note that even after that I wrote this whole monstrosity I'm still not really sure that it can't be exploited - this bash functionality is so tricky and there are so many caveats/edge-cases that could be there and I just don't see them. 

Service expects to run `./handle.sh` script inside of "service" directory for every user/connecion. There is `start.sh` script (for local testing) that sets up `socat` on port 9999 - it can be running in terminal or as a daemon (`start.sh TERMINAL` or `start.sh DAEMON`). There is also a `client.sh` script which can be used for testing (it only connects to running server using `nc`).

As service does "signal corellation" (= finding same signal source in other reports) it scans through all reports that were submitted. This becames a problem in longterm as this operation is resource heavy. Solution is to set up a periodic cleanup (e.g. command `find service/data -mmin +10 -delete` to run in cron job every minute ("+10" should be replaced according to tick length and flag lifetime + some margin)) - this cron job is already prepared in docker.
