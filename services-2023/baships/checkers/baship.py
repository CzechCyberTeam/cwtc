from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from typing import Literal, overload

from ctf_gameserver.checkerlib import CheckResult
from util import CheckStatus, Conn, Point, popcount
from util import random_spaces as rs
from util import randstrl, sgn, timeoutWrapper

MAX_MOVE_DISTANCE = 5
# Yeah, yeah, yeah, I know I should use dbl_epsilon but not going to waste time with this...
# Reps. I never did these (dbl_epsilon) tolerance checks in Python and I don't have mood for
# figuring this out right now... So #TODO: DBL_EPSILON
MOVE_VALIDITY_TOLERANCE = 0.5


def can_offset_move_fail(p: Point) -> bool:
    return p.mag() > MAX_MOVE_DISTANCE - MOVE_VALIDITY_TOLERANCE


def encode_signal_data(data: bytes, modulation: bytes, pad: bytes = b" ") -> bytearray:
    if len(data) % 8 != 0:
        data += (pad * 8)[: 8 - (len(data) % 8)]
    output = bytearray()
    offset = 0
    while len(data) != offset:
        mod = modulation[offset % len(modulation)]
        block = data[offset : offset + 8]
        output.append(block[0] ^ (mod & (1 << 7)))
        output.append(block[1] ^ (mod & (1 << 6)))
        output.append(block[2] ^ (mod & (1 << 5)))
        output.append(block[3] ^ (mod & (1 << 4)))
        output.append(
            ((popcount(block[0]) & 1) << 7)
            | ((popcount(block[1]) & 1) << 6)
            | ((popcount(block[2]) & 1) << 5)
            | ((popcount(block[3]) & 1) << 4)
            | ((popcount(block[4]) & 1) << 3)
            | ((popcount(block[5]) & 1) << 2)
            | ((popcount(block[6]) & 1) << 1)
            | ((popcount(block[7]) & 1) << 0)
        )
        output.append(block[4] ^ (mod & (1 << 3)))
        output.append(block[5] ^ (mod & (1 << 2)))
        output.append(block[6] ^ (mod & (1 << 1)))
        output.append(block[7] ^ (mod & (1 << 0)))
        offset += 8
    return output


def decode_signal_data(data: bytearray) -> tuple[bytes, bytes]:
    # -> [data, modulation]
    if len(data) % 9 != 0:
        raise CheckStatus(CheckResult.FAULTY, "Signal data malformed")
    output = bytearray()
    modulation = bytearray()
    offset = 0
    while len(data) != offset:
        block = data[offset : offset + 9]
        output.append(block[0] ^ ((((block[4] >> 7) ^ popcount(block[0])) & 1) << 7))
        output.append(block[1] ^ ((((block[4] >> 6) ^ popcount(block[1])) & 1) << 6))
        output.append(block[2] ^ ((((block[4] >> 5) ^ popcount(block[2])) & 1) << 5))
        output.append(block[3] ^ ((((block[4] >> 4) ^ popcount(block[3])) & 1) << 4))
        output.append(block[5] ^ ((((block[4] >> 3) ^ popcount(block[5])) & 1) << 3))
        output.append(block[6] ^ ((((block[4] >> 2) ^ popcount(block[6])) & 1) << 2))
        output.append(block[7] ^ ((((block[4] >> 1) ^ popcount(block[7])) & 1) << 1))
        output.append(block[8] ^ ((((block[4] >> 0) ^ popcount(block[8])) & 1) << 0))
        modulation.append(
            ((((block[4] >> 7) ^ popcount(block[0])) & 1) << 7)
            | ((((block[4] >> 6) ^ popcount(block[1])) & 1) << 6)
            | ((((block[4] >> 5) ^ popcount(block[2])) & 1) << 5)
            | ((((block[4] >> 4) ^ popcount(block[3])) & 1) << 4)
            | ((((block[4] >> 3) ^ popcount(block[5])) & 1) << 3)
            | ((((block[4] >> 2) ^ popcount(block[6])) & 1) << 2)
            | ((((block[4] >> 1) ^ popcount(block[7])) & 1) << 1)
            | ((((block[4] >> 0) ^ popcount(block[8])) & 1) << 0)
        )
        offset += 9
    return (output, modulation)


@dataclass
class ShipInfo:
    id: str
    name: str
    pos: Point
    destroyed: bool


@dataclass
class RadioData:
    interferences: list[tuple[str, str]]
    signatures: list[tuple[str, str]]
    modulation: bytes

    def find_interference(self, id: str) -> str | None:
        for interference in self.interferences:
            if interference[0] == id:
                return interference[1]
        return None

    def check_modulation(self, expected: bytes) -> bool:
        if len(expected) > len(self.modulation):
            return expected.startswith(self.modulation)
        else:
            return self.modulation.startswith(expected)

    def signatures_as_dict(self) -> dict[str, list[str]]:
        output: dict[str, list[str]] = {}
        for signature in self.signatures:
            output.setdefault(signature[0], []).append(signature[1])
        return output

    def as_string(self) -> str:
        output = "%Interference%\n"
        for interference in self.interferences:
            output += f"{interference[0]}${interference[1]}\n"
        output += "%Signals%\n"
        for i, signature in enumerate(self.signatures):
            output += f"!{i}!{signature[0]}:{signature[1]}\n"
        output += "%End%\n"
        return output

    def encode(self) -> bytes:
        return encode_signal_data(self.as_string().encode(), self.modulation)

    @classmethod
    def from_string(cls, data: str, modulation: bytes) -> RadioData:
        interferences: list[tuple[str, str]] = []
        signatures: list[tuple[str, str]] = []
        section = ""
        for line in data.split("\n"):
            line = line.strip()
            if len(line) == 0:
                continue
            if line.startswith("%"):
                section = line[1:-1]
                if section not in ("Interference", "Signals", "End"):
                    logging.error("Encountered unknown section %s", repr(section))
                    raise CheckStatus(
                        CheckResult.FAULTY, "Malformed signal data (uknown section)"
                    )
            elif section == "Interference":
                splited = line.split("$", 1)
                if len(splited) != 2:
                    logging.error('Invalid interference line "%s"', line)
                    raise CheckStatus(
                        CheckResult.FAULTY,
                        "Malformed signal data (interference format)",
                    )
                interferences.append((splited[0], splited[1]))
            elif section == "Signals":
                splited = line[1:].split(":", 1)
                if len(splited) != 2:
                    logging.error('Invalid signal line "%s"', line)
                    raise CheckStatus(
                        CheckResult.FAULTY,
                        "Malformed signal data (signal format)",
                    )
                splited = [*splited[0].split("!", 1), splited[1]]
                try:
                    index = int(splited[0])
                    if index != len(signatures):
                        logging.error(
                            "Signals are not in order (expected %s, got %s)",
                            len(signatures),
                            index,
                        )
                        raise CheckStatus(
                            CheckResult.FAULTY,
                            "Malformed signal data (wrong signal order)",
                        )
                except ValueError:
                    logging.error('Invalid signal line "%s"', line)
                    raise CheckStatus(
                        CheckResult.FAULTY,
                        "Malformed signal data (invalid signal prefix)",
                    )
                signatures.append((splited[1], splited[2]))
        if section != "End":
            raise CheckStatus(
                CheckResult.FAULTY, "Malformed signal data (missing end mark)"
            )
        return RadioData(interferences, signatures, modulation)

    def add_random_signature(self, count: int) -> RadioData:
        source = None
        for _ in range(count):
            if source is None or random.randint(0, 1) == 0:
                while True:
                    source = randstrl(1, 5)
                    for __ in range(random.randint(1, 10)):
                        source += f"{random.choice(' /.')}{randstrl(0,5,'_')}"

                    # Problem strings:
                    #   " a "       - Trailing spaces are stripped, cannot have leading/trailing space
                    #   "ab  cd"    - Spaces are collapsed, cannot have double spaces
                    #   "."         - Sources stored as path, cannot be .
                    #   "/ab/"      - Sources stored as path, cannot have leading/trailing slash
                    #   "./ab/."    - Sources stored as path, cannot start with ./ or end with /.
                    #   "ab//cd"    - Sources stored as path, cannot have //
                    #   "ab/./cd"   - Sources stored as path, cannot have /./
                    #   "ab/../cd"  - Sources stored as path, cannot have /../
                    if (
                        source.startswith(" ")
                        or source.endswith(" ")
                        or "  " in source
                        or source == "."
                        or source.startswith("/")
                        or source.endswith("/")
                        or source.startswith("./")
                        or source.endswith("/.")
                        or "//" in source
                        or "/./" in source
                        or "/../" in source
                    ):
                        continue
                    break
                logging.debug('Generated random source "%s"', source)
            self.signatures.append((source, randstrl(1, 100)))
        return self

    def add_random_interference(self, count: int) -> RadioData:
        self.interferences.extend(
            (randstrl(1, 20), randstrl(5, 30)) for _ in range(count)
        )
        return self

    def shuffle(self) -> RadioData:
        random.shuffle(self.signatures)
        random.shuffle(self.interferences)
        return self


@dataclass
class Report:
    id: str
    password: str


@dataclass
class ParsedReport:
    id: str
    counts: dict[bytes, int]
    signatures: dict[bytes, list[bytes]]
    cross_references: dict[bytes, dict[bytes, int]]

    @classmethod
    def from_bytes(cls, id: str, data: bytes) -> ParsedReport:
        counts: dict[bytes, int] = {}
        signatures: dict[bytes, list[bytes]] = {}
        cross_references: dict[bytes, dict[bytes, int]] = {}

        if id.count(".") != 2 or "_" not in id:
            logging.error(
                'Detected report ID generation simplification: "%s"',
                id,
            )
            raise CheckStatus(
                CheckResult.FAULTY,
                "Report ID generation simplified",
            )

        section = "header"
        section_transitions = {
            b"Signature count by source:": ("count", "after_header"),
            b"Captured signatures:": ("signatures", "count"),
            b"Cross report source references:": ("cross", "signatures"),
            b"=== Report end ===": ("end", "cross"),
        }

        for line in data.split(b"\n"):
            if len(line) == 0:
                continue

            if line in section_transitions:
                if section != section_transitions[line][1]:
                    logging.error(
                        'Report sections are in wrong order (from "%s" to "%s")',
                        section,
                        line,
                    )
                    raise CheckStatus(
                        CheckResult.FAULTY,
                        "Malformed report (wrong section order)",
                    )
                section = section_transitions[line][0]
            elif section == "header":
                if line != f"=== Report {id} ===".encode():
                    logging.error('Invalid report header line "%s"', line)
                    raise CheckStatus(
                        CheckResult.FAULTY,
                        "Malformed report (invalid header)",
                    )
                section = "after_header"
            elif section == "count":
                splited = line[6:].split(b": ", 1)
                if len(splited) != 2:
                    logging.error('Invalid report count line "%s"', line)
                    raise CheckStatus(
                        CheckResult.FAULTY,
                        "Malformed report (signature count format)",
                    )
                try:
                    count = int(splited[1])
                except ValueError:
                    logging.error('Invalid report count line "%s"', line)
                    raise CheckStatus(
                        CheckResult.FAULTY,
                        "Malformed report (signature count)",
                    )
                counts[splited[0]] = count
            elif section == "signatures":
                splited = line[4:].split(b":", 1)
                if len(splited) != 2:
                    logging.error('Invalid report signature line "%s"', line)
                    raise CheckStatus(
                        CheckResult.FAULTY,
                        "Malformed report (signature data format)",
                    )
                signatures.setdefault(splited[0], []).append(splited[1])
            elif section == "cross":
                splited = line[4:].split(b":", 2)
                if len(splited) != 3:
                    logging.error('Invalid report cross reference line "%s"', line)
                    raise CheckStatus(
                        CheckResult.FAULTY,
                        "Malformed report (cross reference format)",
                    )
                try:
                    count = int(splited[2])
                except ValueError:
                    logging.error('Invalid report cross reference line "%s"', line)
                    raise CheckStatus(
                        CheckResult.FAULTY,
                        "Malformed report (cross reference count)",
                    )
                cross_references.setdefault(splited[0], {})[splited[1][3:]] = count
            elif section == "end":
                if line != f"=== Report end ===".encode():
                    logging.error('Invalid report end line "%s"', line)
                    raise CheckStatus(
                        CheckResult.FAULTY,
                        "Malformed report (invalid footer)",
                    )
                section = "after_end"
            else:
                logging.error('Found extra data in report: "%s"', line)
                raise CheckStatus(CheckResult.FAULTY, "Malformed report (extra data)")

        for source in counts:
            if counts[source] != len(signatures[source]):
                logging.error(
                    'Wrong count value in report for "%s" (expected %s, got %s)',
                    source,
                    len(signatures[source]),
                    counts[source],
                )
                raise CheckStatus(
                    CheckResult.FAULTY, "Wrong report (counts doesn't match)"
                )
        if id in cross_references:
            logging.error("Self cross reference found in report ", id)
            raise CheckStatus(CheckResult.FAULTY, "Wrong report (self cross reference)")
        for report_id in cross_references:
            for source in cross_references[report_id]:
                if source not in counts:
                    logging.error('Wrong cross report reference for "%s"', source)
                    raise CheckStatus(
                        CheckResult.FAULTY, "Wrong report (redundant cross reference)"
                    )

        return ParsedReport(id, counts, signatures, cross_references)

    def verify_radio(self, radio_data: RadioData):
        signatures = radio_data.signatures_as_dict()
        for source in signatures:
            if source.encode() not in self.counts:
                logging.error('Report is wrong, source "%s" is missing', source)
                raise CheckStatus(CheckResult.FAULTY, "Wrong report (missing source)")
            # This check is redundant as if this fails then next also fails...
            if len(signatures[source]) != self.counts[source.encode()]:
                logging.error(
                    'Report is wrong, source "%s" has wrong count (expected %s, got %s)',
                    source,
                    len(signatures[source]),
                    self.counts[source.encode()],
                )
                raise CheckStatus(CheckResult.FAULTY, "Wrong report (wrong count)")
            for signature in signatures[source]:
                if signature.encode() not in self.signatures[source.encode()]:
                    logging.error(
                        'Report is wrong, source "%s" has missing signature %s',
                        source,
                        signature,
                    )
                    raise CheckStatus(
                        CheckResult.FAULTY, "Wrong report (missing signature)"
                    )

    def verify_cross(self, report: ParsedReport):
        intersection = set(self.counts.keys()) & set(report.counts.keys())
        if len(intersection) == 0:
            if report.id in self.cross_references:
                logging.error(
                    "Report is wrong, report %s shouldn't be there", report.id
                )
                raise CheckStatus(
                    CheckResult.FAULTY, "Wrong report (false cross reference)"
                )
            return
        if report.id.encode() not in self.cross_references:
            logging.error("Report is wrong, report %s should be there", report.id)
            raise CheckStatus(
                CheckResult.FAULTY, "Wrong report (missing cross reference)"
            )
        for source in intersection:
            if (
                report.counts[source]
                != self.cross_references[report.id.encode()][source]
            ):
                logging.error(
                    "Report is wrong, cross reference with report %s has count mismatch (expected %s, got %s)",
                    report.id,
                    self.cross_references[report.id.encode()][source],
                    report.counts[source],
                )
                raise CheckStatus(
                    CheckResult.FAULTY, "Wrong report (wrong cross reference)"
                )


@dataclass
class Session:
    c: Conn
    username: str
    password: str
    ship: ShipInfo = field(init=False)

    @timeoutWrapper("status")
    def parse_status_info(self) -> tuple[bool, Point]:
        """-> [is_operational, position]"""
        self.c.recv_until("Operational:  ")
        operational = self.c.recv_line()
        self.c.recv_until("Location:     x=")
        x = self.c.recv_until(" ")
        self.c.recv_until("y=")
        y = self.c.recv_line()
        try:
            return (bool(int(operational)), Point(int(x), int(y)))
        except ValueError:
            logging.error(
                "Unable to parse ship status values: %s, %s, %s",
                operational,
                x,
                y,
            )
            raise CheckStatus(CheckResult.FAULTY, "Cannot parse status info")

    @timeoutWrapper()
    def login(self, expected: ShipInfo | None = None) -> ShipInfo:
        logging.info("Logging in as %s:%s", self.username, self.password)
        self.c.recv_line()
        self.c.send_line(self.username)
        self.c.recv_line()
        self.c.send_line(self.password)

        self.c.recv_until("Connecting to: ")
        ship_id = self.c.recv_line().decode()
        logging.info("Got ship ID: %s", ship_id)
        self.c.recv_until("Received name: ")
        ship_name = self.c.recv_line().decode()
        logging.info("Got ship name: %s", ship_name)
        status = self.parse_status_info()

        logging.info("Got initial status info: %s", status)

        next_word = self.c.recv_until(" ")
        # Sunk => "Ship not operational, connection cannot be made"
        # Operational => "Connection established..."
        if (next_word == b"Connection") ^ status[0]:
            raise CheckStatus(
                CheckResult.FAULTY,
                "Ship operational status doesn't match inital messages",
            )

        if not status[0]:
            self.c.recv_until("Session closed\n")
            ship = ShipInfo(ship_id, ship_name, status[1], True)
        else:
            self.c.recv_until("Control interface active, ship is accepting commands:\n")
            ship = ShipInfo(ship_id, ship_name, status[1], False)

        if expected is not None and ship != expected:
            logging.error("Ship info differs (expected %s, got %s)", expected, ship)
            raise CheckStatus(
                CheckResult.FAULTY, "Ship status changed since last login"
            )
        return ship

    @classmethod
    def make_session(
        cls, conn: Conn, username: str, password: str, expected: ShipInfo | None = None
    ) -> Session:
        session = Session(conn, username, password)
        session.ship = session.login(expected)
        logging.info("Logged successfully")
        return session

    ################
    ### COMMANDS ###
    ################

    @timeoutWrapper()
    def adrift(self):
        logging.info("Doing adrift")
        self.c.send_line("adrift")
        self.c.recv_until("...\n")
        self.c.send_line("status")
        parsed = self.parse_status_info()
        if not parsed[0]:
            raise CheckStatus(CheckResult.FAULTY, "Ship not operational after adrift")
        if self.ship.pos == Point(0, 0):
            if parsed[1] == Point(0, 0):
                raise CheckStatus(
                    CheckResult.FAULTY, "Ship still at origin after adrift"
                )
        else:
            if parsed[1] != Point(0, 0):
                raise CheckStatus(CheckResult.FAULTY, "Ship not at origin after adrift")
        self.ship.pos = parsed[1]

    @timeoutWrapper()
    def disconnect(self):
        logging.info("Disconnecting")
        self.c.send_line("disconnect")
        self.c.recv_until("Session closed\n")
        self.c.close()

    @timeoutWrapper()
    def find(self, source: str) -> list[str]:
        logging.info('Performing find query for source "%s"', source)
        self.c.send_line(f"find{rs()}{source}")
        line = self.c.recv_line()
        if line == b"Requested source signature was not captured":
            return []
        if line != b"Reports with this source signature:":
            logging.error("Unexpected line in find query output: %s", repr(line))
            raise CheckStatus(CheckResult.FAULTY, "Wrong find output")
        output = []
        while True:
            line = self.c.recv_line()
            if line.startswith(b"(") and line.endswith(b")"):
                if line != f"(Total {len(output)} reports)".encode():
                    logging.error(
                        "Unexpected line in find query output: %s", repr(line)
                    )
                    raise CheckStatus(CheckResult.FAULTY, "Wrong find output")
                return output
            output.append(line.decode())

    @timeoutWrapper()
    def move(self, target: Point, verify: bool) -> bool:
        """Tries to move to target position. Returns `True` if success, `False` otherwise.
        If `verify` is `True`, then addination `status` command is send to verify move
        correctness.
        """
        logging.info("Doing move to %s", target)
        self.c.send_line(f"move{rs()}{target.x}{rs()}{target.y}")
        can_fail = can_offset_move_fail(self.ship.pos - target)
        # We don't really care if it makes valid move when it shouldn't as
        # it is actually bad for them (because then it allows to do bigger moves
        # and so it gives potencially enough time to arrive at target location
        # without adrift).
        # can_pass = mag < MAX_MOVE_DISTANCE + MOVE_VALIDITY_TOLERANCE
        next_word = self.c.recv_until(" ").decode()
        self.c.recv_line()
        # Success => "Ship relocated"
        # Fail => "Relocation failed"
        if next_word not in ("Relocation", "Ship"):
            logging.error("Unexpected next word after move: %s", next_word)
            raise CheckStatus(CheckResult.FAULTY, "Relocation failed")
        failed = next_word == "Relocation"
        if failed:
            if can_fail:
                return False
            logging.error("Ship relocation failed and not in tolerance")
            raise CheckStatus(CheckResult.FAULTY, "Relocation failed")

        if verify:
            self.c.send_line("status")
            parsed = self.parse_status_info()
            if not parsed[0]:
                raise CheckStatus(
                    CheckResult.FAULTY, "Ship not operational after relocation"
                )
            if parsed[1] != target:
                logging.error(
                    "Ship not at expected location after move (expected %s, got %s)",
                    target,
                    parsed[1],
                )
                raise CheckStatus(
                    CheckResult.FAULTY, "Ship not at expected position after relocation"
                )

        self.ship.pos = target
        return True

    @timeoutWrapper()
    def radio(self, count: int, modulation: bytes) -> RadioData:
        logging.info("Gathering radio data (count = %s)", count)
        self.c.send_line(f"radio{rs()}{count}{rs()}".encode() + modulation)
        self.c.recv_until(f"({count})...\n")
        decoded = decode_signal_data(
            bytearray.fromhex(
                self.c.recv_line(timeout=None if count == 0 else count * 2).decode()
            )
        )
        data = RadioData.from_string(decoded[0].decode(), decoded[1])
        if len(data.signatures) != count:
            logging.error(
                "Wrong radio signature count (expected %s, got %s)",
                count,
                len(data.signatures),
            )
            raise CheckStatus(CheckResult.FAULTY, "Wrong radio signature count")
        if not data.check_modulation(modulation):
            raise CheckStatus(CheckResult.FAULTY, "Wrong radio modulation")
        return data

    @timeoutWrapper()
    def rename(self, name: str):
        logging.info('Doing rename to "%s"', name)
        self.c.send_line(f"rename{rs()}{name}")
        self.c.recv_line()
        self.ship.name = name

    @timeoutWrapper()
    def report(self, data: bytes) -> Report:
        logging.info("Submitting report")
        self.c.send_line(f"report{rs()}{data.hex()}")
        self.c.recv_until("Generated report: Key=")
        password = self.c.recv_until(" ").decode()
        self.c.recv_until("ID=")
        id = self.c.recv_line().decode()
        return Report(id, password)

    @overload
    def retrieve(
        self, report: Report, must_succeed: Literal[False]
    ) -> ParsedReport | None: ...

    @overload
    def retrieve(self, report: Report, must_succeed: Literal[True]) -> ParsedReport: ...

    @timeoutWrapper()
    def retrieve(self, report: Report, must_succeed: bool) -> ParsedReport | None:
        logging.info("Retrieving report %s", report)
        self.c.send_line(f"retrieve{rs()}{report.password}{rs()}{report.id}")
        next_line = self.c.recv_line()
        if next_line in (
            b"Report not found",
            b"Unauthorized for report access",
        ):
            if must_succeed:
                logging.error("Report retrieve failed but it should succeed")
                raise CheckStatus(CheckResult.FAULTY, "Wrong retrieve output")
            else:
                return None
        elif next_line != b"Successfully authorized for report access":
            raise CheckStatus(CheckResult.FAULTY, "Invalid retrieve output")
        data = self.c.recv_until("=== Report end ===\n", False)
        return ParsedReport.from_bytes(report.id, data)

    @timeoutWrapper()
    def scuttle(self):
        logging.info("Doing scuttle")
        self.c.send_line("scuttle")
        self.c.recv_line()
        self.c.recv_until("last info:\n")
        parsed = self.parse_status_info()
        if parsed[1] != self.ship.pos:
            logging.error("Ship was moved after scuttle (shipe moved to %s)", parsed[1])
            raise CheckStatus(CheckResult.FAULTY, "Ship moved after scuttle")
        self.ship.destroyed = True

    ###############
    ### HELPERS ###
    ###############

    def random_point_around(self) -> Point:
        while True:
            offset = Point(
                random.randint(-MAX_MOVE_DISTANCE, MAX_MOVE_DISTANCE),
                random.randint(-MAX_MOVE_DISTANCE, MAX_MOVE_DISTANCE),
            )
            if offset == Point(0, 0):
                continue
            if not can_offset_move_fail(offset):
                break
        return self.ship.pos + offset

    def move_around(self, moves: int = 1, verify: bool = False):
        logging.info("Moving around (%sx), starting pos is %s...", moves, self.ship.pos)
        for _ in range(moves):
            self.move(self.random_point_around(), verify)

    def move_towards_to(self, target: Point, verify: bool):
        logging.info("Moving towards to %s", target)
        offset = target - self.ship.pos

        # Too lazy to do "euclid" so I'm doing "manhattan" KEKW
        # Well actually "manhattan" will be faster I guess because it will always
        # move by max "safe" distance while "euclid" could decide to do smaller
        # steps to keep it safe.
        if offset.x != 0:
            offset.x = min(abs(offset.x), MAX_MOVE_DISTANCE - 1) * sgn(offset.x)
            offset.y = 0
        else:
            offset.y = min(abs(offset.y), MAX_MOVE_DISTANCE - 1) * sgn(offset.y)

        self.move(self.ship.pos + offset, verify)

    def move_to(self, target: Point, verify: bool):
        while self.ship.pos != target:
            self.move_towards_to(target, verify)

    def move_futher_from(self, target: Point, verify: bool):
        logging.info("Moving futher from %s", target)
        original_mag = (self.ship.pos - target).sqr_mag()
        while True:
            next = self.random_point_around()
            if (next - target).sqr_mag() > original_mag:
                break
        self.move(next, verify)
