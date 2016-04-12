#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import argparse
import pjsua as pj
import threading


SERVICE_NAME = 'SIP REGISTRATION CHECKER'
STATUS_OK = 'OK'
STATUS_FAILED = 'CRITICAL'


class MyAccountCallback(pj.AccountCallback):
    sem = None

    def __init__(self, account):
        pj.AccountCallback.__init__(self, account)

    def wait(self):
        self.sem = threading.Semaphore(0)
        self.sem.acquire()

    def on_reg_state(self):
        if self.sem:
            if self.account.info().reg_status >= 200:
                self.sem.release()


class StdoutStderrSuppressor(object):

    def __init__(self):
        self.null_fds = [os.open(os.devnull, os.O_RDWR) for _ in range(2)]
        self.save_fds = (os.dup(1), os.dup(2))

    def __enter__(self):
        os.dup2(self.null_fds[0], 1)
        os.dup2(self.null_fds[1], 2)

    def __exit__(self, *_):
        sys.stdout.flush()
        sys.stderr.flush()
        os.dup2(self.save_fds[0], 1)
        os.dup2(self.save_fds[1], 2)
        os.close(self.null_fds[0])
        os.close(self.null_fds[1])


def on_exit(status):
    switcher = {
        STATUS_OK: 0,
        STATUS_FAILED: 2
    }
    sys.exit(switcher.get(status, 2))


def on_error(e):
    print('%s %s - Failed (exception: %s)' %
          (SERVICE_NAME, STATUS_FAILED, str(e)))
    on_exit(STATUS_FAILED)


def on_done(status_code):
    if status_code == 200:
        print('%s %s - Registration was success' %
              (SERVICE_NAME, STATUS_OK))
        on_exit(STATUS_OK)
    else:
        print('%s %s - Failed (return code: %s)' %
              (SERVICE_NAME, STATUS_FAILED, status_code))
        on_exit(STATUS_FAILED)


def check_registration(args):
    with StdoutStderrSuppressor():
        lib = pj.Lib()
    try:
        ## no need any additional lib output
        lib.init(log_cfg = pj.LogConfig(level = 0))
        lib.create_transport(pj.TransportType.UDP, pj.TransportConfig(5080))
        lib.start()
        acc = lib.create_account(pj.AccountConfig(args.addr,
                                                  args.account_id,
                                                  args.account_password))
        acc_cb = MyAccountCallback(acc)
        acc.set_callback(acc_cb)
        acc_cb.wait()

        status_code = acc.info().reg_status
        lib.destroy()
        lib = None

        on_done(status_code)

    except pj.Error, e:
        on_error(e)
        lib.destroy()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', '--addr', type=str, required=True,
                        help='SIP IP Address')
    parser.add_argument('-i', '--account_id', type=str,
                        required=True, help='Account ID')
    parser.add_argument('-p', '--account_password', type = str,
                        required=True, help='Account password')

    check_registration(parser.parse_args())
