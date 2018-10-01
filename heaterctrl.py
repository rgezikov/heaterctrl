#!/usr/bin/env python

import json
import re
import sys
import os
import subprocess
from datetime import datetime, timedelta
import argparse


class HeaterLog(object):
    LOG_FILE=os.path.join(os.path.realpath(os.path.dirname(__file__)), "log.txt")

    @staticmethod
    def write(msg, ce=False):
        timestamp = datetime.now().strftime('%y%m%d-%H%M%S')
        with open(HeaterLog.LOG_FILE, "a") as lf:
            lf.write("{}\t{}\n".format(timestamp, msg))
            if ce:
                sys.stderr.write(msg)
                sys.stderr.write("\n")


class HeaterController(object):
    this_script = os.path.realpath(__file__)
    queues = {'0':'p', '1':'v'}
    task_parse = re.compile(r'(\d+)\t(\w+\s+\w+\s+\d+\s+\d+:\d+:\d+\s+\d+)\s+(\w)\s+\w+')

    def __init__(self, id):
        self.id = id

    def remove_tasks(self):
        # remove all existing tasks from the corresponding queue
        for t in self.list_tasks():
            subprocess.check_output(["atrm", t[0]])

    def set_task(self, time, duration):
        # remove old and possibly running tasks
        self.remove_tasks()
        self.off()

        # set new task
        # command to switch on
        on_cmd  = "{} -o on -i {}".format(HeaterController.this_script, self.id)
        at_cmd = "at -q {} -t {}".format(self.queues[self.id], time)
        p = subprocess.Popen(at_cmd, shell=True, stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
        (p_stdin, p_stdout, p_stderr) = (p.stdin, p.stdout, p.stderr)
        p_stdin.write(on_cmd)

        # command to switch off
        off_cmd = "{} -o off -i {}".format(HeaterController.this_script, self.id)
        time_off = datetime.strptime(time, "%y%m%d%H%M")
        time_off = time_off + timedelta(minutes=duration)
        at_cmd = "at -q {} -t {}".format(self.queues[self.id], time_off.strftime("%y%m%d%H%M"))
        p = subprocess.Popen(at_cmd, shell=True,
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
        (p_stdin, p_stdout, p_stderr) = (p.stdin, p.stdout, p.stderr)
        p_stdin.write(off_cmd)

    def on(self):
        subprocess.check_output(["gpio", "mode", str(self.id), "out"])
        subprocess.check_output(["gpio", "write", str(self.id), "0"])

    def off(self):
        subprocess.check_output(["gpio", "write", str(self.id), "1"])
        subprocess.check_output(["gpio", "mode", str(self.id), "in"])

    def list_tasks(self):
        res = []
        output = subprocess.check_output(["atq", "-q", "{}".format(self.queues[self.id])])
        for t in output.split("\n"):
            m = HeaterController.task_parse.match(t.strip())
            if m is not None:
                time = datetime.strptime(m.group(2), r'%a %b %d %H:%M:%S %Y')
                res.append((m.group(1), time.strftime(r'%y%m%d%H%M')))
        return res

operations = ["set", "on", "off", "remove", "list"]

parser = argparse.ArgumentParser()
parser.add_argument("-o", dest="o", help="operation ({})".format(operations), required=True, default= None, type=str)
parser.add_argument("-i", dest="i", help="heater id (0 or 1)", default= None, type=str)
parser.add_argument("-t", dest="t", help="time (YYMMDDhhmm)", default= None, type=str)
parser.add_argument("-d", dest="d", help="duration, in minutes, 1..120", default= None, type=int)
parser.add_argument("-j", dest="j", help="output list in json format", action="store_true")
args = parser.parse_args()

if args.o not in operations:
    HeaterLog.write("Unknown operation", True)
    sys.exit(1)


if args.o == 'set':
    if args.i is None or args.i not in ["0", "1"]:
        HeaterLog.write("Missing or wrong value for -i parameter", True)
        sys.exit(1)

    if args.t is None:
        HeaterLog.write("Missing -t parameter", True)
        sys.exit(1)

    if args.d is None or args.d < 1 or args.d > 120:
        HeaterLog.write("Missing or wrong value for -d parameter", True)
        sys.exit(1)

    HeaterLog.write("Starting heater {} at {} for {} sec".format(args.i, args.t, args.d))
    hctrl = HeaterController(args.i)
    hctrl.set_task(args.t, args.d)

elif args.o == 'on':
    hctrl = HeaterController(args.i)
    hctrl.on()

elif args.o == 'off':
    hctrl = HeaterController(args.i)
    hctrl.off()

elif args.o == "remove":
    hctrl = HeaterController(args.i)
    hctrl.remove_tasks()

elif args.o == "list":
    hctrl = HeaterController(args.i)
    tasks = hctrl.list_tasks()
    if args.j:
        print(json.dumps(tasks))
    else:
        for t in tasks:
            print(str(t))




