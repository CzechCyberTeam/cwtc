from __future__ import annotations

import logging
import math
import random
import socket
import string
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, TypeVar

from ctf_gameserver.checkerlib import CheckResult

try:
    from typing import ParamSpec
except ImportError:
    try:
        from typing_extensions import ParamSpec
    except ImportError:
        if not TYPE_CHECKING:

            class ParamSpec:
                args = tuple
                kwargs = tuple

                def __init__(self, name):
                    self.name = name


P = ParamSpec("P")
T = TypeVar("T")


def randstr(
    length: int, extra: str = "", chars: str = string.ascii_letters + string.digits
) -> str:
    return "".join(random.choices(chars + extra, k=length))


def randstrl(
    min: int,
    max: int,
    extra: str = "",
    chars: str = string.ascii_letters + string.digits,
) -> str:
    return randstr(random.randint(min, max), extra, chars)


def random_spaces(min: int = 1, max: int = 3):
    return " " * random.randint(min, max)


def randbool(chance: float = 0.5) -> bool:
    return random.random() < chance


def sgn(x: int | float) -> int:
    if x == 0:
        return 0
    return 1 if x > 0 else -1


def popcount(x: int) -> int:
    return bin(x).count("1")


@dataclass
class Point:
    x: int
    y: int

    def __add__(self, other: Point) -> Point:
        return Point(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Point) -> Point:
        return Point(self.x - other.x, self.y - other.y)

    def sqr_mag(self) -> int:
        return self.x**2 + self.y**2

    def mag(self) -> float:
        return math.sqrt(self.sqr_mag())


@dataclass
class CheckStatus(Exception):
    result: CheckResult
    info: str


def checkStatusWrapper(
    f: Callable[P, tuple[CheckResult, str]]
) -> Callable[P, tuple[CheckResult, str]]:
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> tuple[CheckResult, str]:
        try:
            return f(*args, **kwargs)
        except CheckStatus as e:
            return (e.result, e.info)

    return wrapped


def timeoutWrapper(cmd: str = ""):
    def wrapper(f: Callable[P, T]) -> Callable[P, T]:
        msg = f'Communication error in "{cmd or f.__name__}"'

        def wrapped(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                return f(*args, **kwargs)
            except (socket.timeout, EOFError):
                raise CheckStatus(CheckResult.FAULTY, msg)

        return wrapped

    return wrapper


class Conn:
    def __init__(self, ip: str, port: int, recv_size: int = 1024):
        self.ip = ip
        self.port = port
        self.buffer = bytearray()
        self.RECV_SIZE = recv_size
        self.open()

    def open(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.connect((self.ip, self.port))

    def close(self):
        self.s.close()

    def _recv(self, timeout: float | None = None) -> bytes:
        if timeout is None:
            x = self.s.recv(self.RECV_SIZE)
        else:
            original = self.s.timeout
            self.s.settimeout(timeout)
            x = self.s.recv(self.RECV_SIZE)
            self.s.settimeout(original)
        logging.debug("Received %s bytes: %s", len(x), repr(x))
        return x

    def _recv_eof_check(self, timeout: float | None = None) -> bytes:
        x = self._recv(timeout)
        if len(x) == 0:
            raise EOFError(f"Unexpected connection EOF")
        return x

    def peek(self, timeout: float | None = None) -> bytes:
        if len(self.buffer) == 0:
            self.buffer += self._recv_eof_check(timeout)
        return bytes(self.buffer)

    def recv(self, timeout: float | None = None) -> bytes:
        """Receives *some* data. No gurantee about size of received data."""
        if len(self.buffer) == 0:
            return self._recv_eof_check(timeout)
        output = self.buffer
        self.buffer = bytearray()
        return bytes(output)

    def recv_until(
        self, target: bytes | str, drop: bool = True, timeout: float | None = None
    ) -> bytes:
        if isinstance(target, str):
            target = target.encode()
        logging.debug(
            "recv_until(%s); Current buffer: %s", repr(target), repr(self.buffer)
        )
        while True:
            index = self.buffer.find(target)
            if index != -1:
                output = self.buffer[0 : index + (0 if drop else len(target))]
                self.buffer = self.buffer[index + len(target) :]
                return bytes(output)
            self.buffer += self._recv_eof_check(timeout)

    def recv_line(self, drop: bool = True, timeout: float | None = None) -> bytes:
        return self.recv_until(b"\n", drop, timeout)

    def send(self, data: bytes | str):
        if isinstance(data, str):
            data = data.encode()
        logging.debug("Sending %s bytes: %s", len(data), repr(data))
        self.s.send(data)

    def send_line(self, data: bytes | str):
        if isinstance(data, str):
            self.send(data + "\n")
        else:
            self.send(data + b"\n")
