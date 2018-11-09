#!/usr/bin/env python

import json
import re
import sys
import os
import subprocess
from datetime import datetime, timedelta
import argparse
import time


class HeaterLog(object):
    LOG_FILE="/tmp/heater-log.txt"
    ENABLED = False
    @staticmethod
    def write(msg):
        # if HeaterLog.ENABLED:
        #     timestamp = datetime.now().strftime('%y%m%d-%H%M%S')
        #     with open(HeaterLog.LOG_FILE, "a") as lf:
        #         lf.write("{}\t{}\n".format(timestamp, msg))
        #     # print(msg)
        pass


class HeaterController(object):
    this_script = os.path.realpath(__file__)
    queues = {'0':'p', '1':'v'}
    pin_ids = {'p':'0', 'v':'1'}
                             # 120	Tue Nov  6 07:15:00 2018 v www-data
                             # 121	Tue Nov  6 08:20:00 2018 v www-data
    task_parse = re.compile(r'(\d+)\t(\w+\s+\w+\s+\d+\s+\d+:\d+:\d+\s+\d+)\s+(\w)\s+\w+')
    #/home/pi/heaterctrl/heaterctrl.py -o on -i 1
    cmd_parse = re.compile(r'[/\\a-zA-Z.]+heaterctrl\.py.+-o\s+(\w+).*')

    def __init__(self, id):
        self.id = id

    def remove_tasks(self):
        # remove all existing tasks from the corresponding queue
        qid = HeaterController.queues[self.id]
        t = HeaterController.list_tasks(q=qid)["tasks"][qid]
        if len(t["on_id"]) > 0:
            HeaterLog.write("Removing task {} for heater {}".format(t["on_id"], self.id))
            subprocess.check_output(["atrm", t["on_id"]])
        if len(t["off_id"]) > 0:
            HeaterLog.write("Removing task {} for heater {}".format(t["off_id"], self.id))
            subprocess.check_output(["atrm", t["off_id"]])

    def set_task(self, time, duration):
        HeaterLog.write("HeaterController.set_task('{}', {})".format(time, duration))
        # remove old and possibly running tasks
        self.remove_tasks()
        self.off()

        # set new task
        HeaterLog.write("Starting heater {} at {} for {} min".format(self.id, time, duration))
        # command to switch on
        on_cmd  = "{} -o on -i {}".format(HeaterController.this_script, self.id)
        HeaterLog.write("on_cmd = '{}'".format(on_cmd))
        at_cmd = "at -q {} -t {}".format(self.queues[self.id], time)
        HeaterLog.write("at_cmd = '{}'".format(at_cmd))
        p = subprocess.Popen(at_cmd, shell=True, stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
        (p_stdin, p_stdout, p_stderr) = (p.stdin, p.stdout, p.stderr)
        p_stdin.write(on_cmd)

        # command to switch off
        off_cmd = "{} -o off -i {}".format(HeaterController.this_script, self.id)
        HeaterLog.write("off_cmd = '{}'".format(off_cmd))
        time_off = datetime.strptime(time, "%y%m%d%H%M")
        time_off = time_off + timedelta(minutes=int(duration))
        at_cmd = "at -q {} -t {}".format(self.queues[self.id], time_off.strftime("%y%m%d%H%M"))
        HeaterLog.write("at_cmd = '{}'".format(at_cmd))
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

    @staticmethod
    def list_tasks(q = None):
        """
        Return list of tasks assigned by current user
        :param q: Specifies queue (one letter), refer to 'man at' for details
        :return: an object of the following structure:

        # {
        #     "tasks": {
        #         "p": {
        #             "state": "off",
        #             "on_id": "10",
        #             "on_time": "1811060715",
        #             "off_id": "11",
        #             "off_time": "1811060820",
        #         },
        #         "v": {
        #             "state":"off",
        #             "on_id": "20",
        #             "on_time":"1811060715",
        #             "off_id": "21",
        #             "off_time":"1811060820",
        #         }
        #     }
        # }
        time value and id are empty strings if corresponding task is missing
        """
        to = {"p":{}, "v":{}}
        for k, v in to.items():
            pin = HeaterController.pin_ids[k]
            state = subprocess.check_output(["gpio", 'read', pin]).strip()
            to[k]["state"] = "on" if state=="0" else "off"
            to[k]["on_id"]  = ""
            to[k]["on_time"]  = ""
            to[k]["off_id"] = ""
            to[k]["off_time"] = ""

        tasks = []
        if q is None:
            output = subprocess.check_output(["atq"])
        else:
            output = subprocess.check_output(["atq", "-q", q])
        for t in output.split("\n"):
            m = HeaterController.task_parse.match(t.strip())
            if m is not None:
                task_id = m.group(1)
                task_time = datetime.strptime(m.group(2), r'%a %b %d %H:%M:%S %Y').strftime(r'%y%m%d%H%M')
                q_name = m.group(3)
                tasks.append((task_id, task_time, q_name))
        tasks = sorted(tasks, key=lambda x: x[2] + x[1])
        while len(tasks):
            task_id, task_time, q_name = tasks.pop(0)
            output = subprocess.check_output(["at", "-c", task_id])
            # get last line of the output
            lines = output.strip().split("\n")
            # find value of -o parameter that specifies operation
            m = HeaterController.cmd_parse.match(lines[-1].strip())
            if m is not None:
                cmd = m.group(1)
                if cmd == r'on':
                    to[q_name]["on_id"] = task_id
                    to[q_name]["on_time"] = task_time
                elif cmd == r'off':
                    to[q_name]["off_id"] = task_id
                    to[q_name]["off_time"] = task_time
                else:
                    assert False, "Unexpected value of -o parameter: {}".format(cmd)

        return {"tasks":to}


if __name__ == "__main__":
    start_time = time.time()
    operations = ["set", "on", "off", "remove", "list"]

    parser = argparse.ArgumentParser()
    parser.add_argument("-o", dest="o", help="operation ({})".format(operations), required=True, default= None, type=str)
    parser.add_argument("-i", dest="i", help="heater id (0 or 1)", default= None, type=str)
    parser.add_argument("-t", dest="t", help="time (YYMMDDhhmm)", default= None, type=str)
    parser.add_argument("-d", dest="d", help="duration, in minutes, 1..120", default= None, type=int)
    parser.add_argument("-j", dest="j", help="output list in json format", action="store_true")
    parser.add_argument("-b", dest="b", help="Enable debug output", action="store_true")
    args = parser.parse_args()

    if args.b:
        HeaterLog.ENABLED = True

    if args.o not in operations:
        HeaterLog.write("Unknown operation")
        sys.exit(1)

    if args.o == 'set':
        if args.i is None or args.i not in ["0", "1"]:
            HeaterLog.write("Missing or wrong value for -i parameter")
            sys.exit(1)

        if args.t is None:
            HeaterLog.write("Missing -t parameter")
            sys.exit(1)

        if args.d is None or args.d < 1 or args.d > 120:
            HeaterLog.write("Missing or wrong value for -d parameter")
            sys.exit(1)

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
        tasks = HeaterController.list_tasks()
        tasks["elapsed"] = time.time() - start_time
        if args.j:
            print(json.dumps(tasks))
        else:
            for t in tasks:
                print(str(t))