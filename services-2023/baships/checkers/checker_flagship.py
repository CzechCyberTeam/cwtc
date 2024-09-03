#!/usr/bin/env python3

from __future__ import annotations

import logging
import random

from baship import Session
from ctf_gameserver.checkerlib import (
    BaseChecker,
    CheckResult,
    get_flag,
    get_flagid,
    load_state,
    run_check,
    set_flagid,
    store_state,
)
from util import (
    CheckStatus,
    Conn,
    Point,
    checkStatusWrapper,
    randbool,
    randstr,
    randstrl,
)


class FlagShipChecker(BaseChecker):
    def make_conn(self) -> Conn:
        return Conn(self.ip, 9999)

    def rand_user(self) -> tuple[str, str]:
        username = randstrl(15, 25)
        password = randstrl(15, 25)
        return (username, password)

    @checkStatusWrapper
    def place_flag(self, tick):
        sess = Session.make_session(self.make_conn(), *self.rand_user())

        sess.adrift()
        sess.move_around()

        sess.rename(f"Flag ship {get_flag(tick)}")
        if randbool():
            sess.scuttle()

        set_flagid(f"x={sess.ship.pos.x};y={sess.ship.pos.y}")
        store_state(f"{tick}_flagship_user", sess.username)
        store_state(f"{tick}_flagship_pass", sess.password)
        store_state(f"{tick}_flagship_ship", sess.ship)

        return (CheckResult.OK, "")

    @checkStatusWrapper
    def check_service(self):
        sess0 = Session.make_session(self.make_conn(), *self.rand_user())

        # Movement test
        sess0.move_around(random.randint(0, 2))
        sess0.move_futher_from(Point(0, 0), True)
        logging.info("Ship movement verified")

        # Reconnect
        sess0.rename(randstr(5) + " (" + sess0.ship.name + ")")
        sess0.disconnect()
        sess0.c.open()
        sess0.login(sess0.ship)
        logging.info("Reconnection verified")

        # Scuttle
        if randbool(0.2):
            if randbool():
                sess0.rename(randstrl(8, 13))
            sess0.scuttle()
            sess0.c.open()
            sess0.login(sess0.ship)
            logging.info("Scuttle verified")

        # Radio test
        sess1 = Session.make_session(self.make_conn(), *self.rand_user())
        sess1.move_to(sess0.ship.pos, False)
        logging.info("Second ship arrived to target location")

        data = sess1.radio(0, randstrl(1, 5).encode())
        found = data.find_interference(sess0.ship.id)
        if found is None:
            return (CheckResult.FAULTY, "Ship signals doesn't interfere")
        if found != sess0.ship.name:
            return (CheckResult.FAULTY, "Reported interference is incorrect")
        logging.info("Radio interference verified")

        # Adrift
        if randbool(0.3):
            sess1.adrift()
            sess1.adrift()
            sess1.move_around(1, True)
            logging.info("Adrift verified")

        sess1.disconnect()

        return (CheckResult.OK, "")

    @checkStatusWrapper
    def check_flag(self, tick):
        if not get_flagid(tick):
            return (CheckResult.FLAG_NOT_FOUND, "Flag wasn't placed")

        try:
            Session.make_session(
                self.make_conn(),
                load_state(f"{tick}_flagship_user"),
                load_state(f"{tick}_flagship_pass"),
                load_state(f"{tick}_flagship_ship"),
            )
        except CheckStatus:
            return (CheckResult.FLAG_NOT_FOUND, "Flag ship differs")

        return (CheckResult.OK, "")


if __name__ == "__main__":
    run_check(FlagShipChecker)
