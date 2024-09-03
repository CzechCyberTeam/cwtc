#!/usr/bin/env python3

from __future__ import annotations

import logging
import random

from baship import RadioData, Report, Session
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
from util import Conn, Point, checkStatusWrapper, randbool, randstr, randstrl


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

        for _ in range(random.randint(1, 2)):
            sess.move_futher_from(Point(0, 0), False)

        data = sess.radio(random.randint(3, 5), randstr(10).encode())
        index = random.randint(0, 4)
        data.signatures[index] = (data.signatures[index][0], get_flag(tick))

        report = sess.report(data.encode())

        set_flagid(f"Report={report.id};Source={data.signatures[index][0]}")
        store_state(f"{tick}_report_pass", report.password)
        store_state(f"{tick}_report_radio", data)

        return (CheckResult.OK, "")

    @checkStatusWrapper
    def check_service(self):
        sess = Session.make_session(self.make_conn(), *self.rand_user())
        sess.move_around(random.randint(0, 1))

        # Signals
        sess.move_futher_from(Point(0, 0), False)
        data0 = sess.radio(random.randint(1, 3), randstrl(1, 15).encode())
        if randbool():
            sess.move_futher_from(Point(0, 0), False)
            data1 = sess.radio(random.randint(0, 2), randstrl(1, 15).encode())
            data1.modulation = randstrl(1, 20).encode()
        else:
            data1 = RadioData([], [], randstrl(1, 5).encode())
        logging.info("Signal gathering verified")

        # Reports 1
        rep0 = sess.retrieve(
            sess.report(
                data0.add_random_interference(random.randint(0, 3))
                .add_random_signature(random.randint(0, 3))
                .shuffle()
                .encode()
            ),
            True,
        )
        rep0.verify_radio(data0)
        rep1 = sess.retrieve(
            sess.report(
                data1.add_random_interference(random.randint(1, 5))
                .add_random_signature(random.randint(1, 5))
                .shuffle()
                .encode()
            ),
            True,
        )
        rep1.verify_radio(data1)
        rep1.verify_cross(rep0)
        logging.info("Reporting stage 1 verified")

        # Find 1
        test_source = random.choice(list(rep1.counts.keys())).decode()
        found0 = set(sess.find(test_source))
        if rep1.id not in found0:
            logging.error("Report %s was not found in find query output", rep1.id)
            logging.error("Find query output: %s", found0)
            return (CheckResult.FAULTY, "Expected reports not in find query result")
        sess.disconnect()
        logging.info("Find query stage 1 verified")

        # Reports 2
        sess = Session.make_session(self.make_conn(), *self.rand_user())
        sess.move_futher_from(Point(0, 0), True)
        data2 = sess.radio(random.randint(0, 2), randstrl(1, 15).encode())
        data2.signatures.extend(data1.signatures)
        rep2 = sess.retrieve(sess.report(data2.encode()), True)
        rep2.verify_radio(data2)
        rep2.verify_cross(rep1)
        rep2.verify_cross(rep0)
        logging.info("Reporting stage 2 verified")

        # Find 2
        found1 = set(sess.find(test_source))
        if len(found0 - found1) != 0 or rep2.id not in found1:
            logging.error("Find query stage 2 verification failed")
            logging.error("Find query output: %s", found0)
            return (CheckResult.FAULTY, "Expected reports not in find query result")
        sess.disconnect()
        logging.info("Find query stage 2 verified")

        return (CheckResult.OK, "")

    @checkStatusWrapper
    def check_flag(self, tick):
        flag_id = get_flagid(tick)
        if not flag_id:
            return (CheckResult.FLAG_NOT_FOUND, "Flag wasn't placed")
        report_id, source = [x[7:] for x in flag_id.split(";", 1)]

        sess = Session.make_session(self.make_conn(), *self.rand_user())
        sess.move_around(random.randint(0, 1))

        if report_id not in sess.find(source):
            return (CheckResult.FLAG_NOT_FOUND, "Report missing in find query result")

        sess.move_around(random.randint(0, 1))

        retrieved = sess.retrieve(
            Report(report_id, load_state(f"{tick}_report_pass")),
            False,  # We will check it here to supply more specific message
        )

        if retrieved is None:
            return (CheckResult.FLAG_NOT_FOUND, "Report cannot be retrieved")

        retrieved.verify_radio(load_state(f"{tick}_report_radio"))

        if get_flag(tick).encode() not in retrieved.signatures[source.encode()]:
            return (CheckResult.FLAG_NOT_FOUND, "Flag missing from report")

        return (CheckResult.OK, "")


if __name__ == "__main__":
    run_check(FlagShipChecker)
