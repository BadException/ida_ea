from idaapi import *
from idautils import *
from idc import *
from api_funcs import get_rg
from ea_UI import QtCore, QtWidgets, Warning_UI
from json import dump, load
from os import remove
from os.path import isfile
from string import printable
from threading import Thread
from time import sleep, time


def read(file, mode="r"):
    with open(file, mode) as f:
        return f.read()


def write(string, file, type="w"):
    with open(file, type) as f:
        f.write(string)


def cPrint(color, msg):
    return ("<span class='%s'>" % (color)) + msg + "</span>"


def parse_mem(mem):
    return ("<img src='" + root_dir + "arrow.png'>").join(mem)


def get_bits():

    global file_name
    global _32_bit

    new_name = get_root_filename()

    if new_name != file_name:
        file_name = new_name

        # avoid IDA bug
        if get_inf_structure().is_32bit() and get_inf_structure().is_64bit():
            _32_bit = (next((False for i in ("r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15")
                             if get_rg(i) != 0xffffffffffffffff), True) and
                       next((False for i in ("rax", "rbx", "rcx", "rdx", "rsi", "rdi", "rbp", "rsp", "rip")
                             if get_rg(i) > 0xffffffff), True))
        else:
            _32_bit = get_inf_structure().is_32bit()

    return _32_bit


def get_mem_recursive(mem, matches, prev_mem=False, get_perm=True, int_size=4):

    global iterations

    mem_str = hex(mem)[2:].strip("L").zfill(int_size * 2)

    if get_perm:
        try:
            perm = bin(GetSegmentAttr(mem, SEGATTR_PERM))[2:].zfill(3)
            if "1" in perm:
                perm = '(' + "".join(sym if int(v) else "-" for v, sym in zip(perm, ("r", "w", "x"))) + ')'
            else:
                perm = ""
        except:
            perm = ""
    else:
        perm = ""

    offset = None

    if codeSegment and codeStart < mem < codeEnd:
        offset = GetFuncOffset(mem)
        if offset:
            text = cPrint(b_red, "0x" + mem_str) + cPrint(b_red, " &lt;" + offset + "&gt;")
            code = True

    if not offset:
        if perm or not get_perm:
            text = cPrint(b_lightblue, "0x" + mem_str)
        elif next((False for i in mem_str if i != "0"), True):
            text = cPrint(b_yellow, "0x" + mem_str)  # + "(NULL)"
        else:
            text = "0x" + mem_str

        if next((False for i in reversed(mem_str.decode("HEX")) if i not in printable), True) and prev_mem:
            r_mem = dbg_read_memory(prev_mem, 50)
            if r_mem:
                text += '(' + cPrint(b_green, '"' + r_mem.split("\x00")[0].replace("\n", "") + '"') + ')'

        code = False

    matches.append(text)

    if not code and iterations < max_iterations:
        iterations += 1
        next_mem = dbg_read_memory(mem, int_size)

        if next_mem:
            get_mem_recursive(int("".join(reversed(next_mem)).encode("HEX"), 16), matches, mem, int_size=int_size)

    iterations = 0


def ea_warning(text, additional_buttons=[], title="EA Warning"):

    global warning
    global form
    global buttons

    warning = QtWidgets.QFrame()
    form = Warning_UI()
    form.setupUi(warning)
    form.label.setText(text)
    form.pushButton.clicked.connect(warning.close)

    for button, handler in additional_buttons:
        setattr(form, button, QtWidgets.QPushButton(warning))
        getattr(form, button).clicked.connect(handler)
        getattr(form, button).setText(QtWidgets.QApplication.translate("Dialog", button, None))
        form.horizontalLayout.addWidget(getattr(form, button))

    warning.setWindowFlags(warning.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
    warning.setWindowTitle(QtWidgets.QApplication.translate("Dialog", title, None))
    warning.show()


def save_config():

    with open(root_dir + "config.json", "w") as w:
        dump(config, w)


def load_config():

    global config

    init_config = {
        "libc_offsets": [0, 0, 0, 0],
        "trace_dir": 0,
        "stack_display_length": 25,
        "apply_skin_on_startup": True,
        "current_skin": ["1c1c2a", "ffffff", "818181", "00d5ff", "ffffff", "202030", "ffffff", "00e6ff", "ffffff"],
        "skins": [["Neon Dark", "212121", "ffffff", "414141", "00fff7", "ffffff", "282828", "ffffff", "00ffea", "ffffff"],
                  ["Neon Blue", "1c1c2a", "ffffff", "818181", "00d5ff", "ffffff", "202030", "ffffff", "00e6ff", "ffffff"]]
    }

    if not isfile(root_dir + "config.json"):
        config = init_config

    else:
        try:
            with open(root_dir + "config.json", "r") as f:
                config = load(f)
        except:
            print 'IDA EA Error: Config File ("config.json") contained invalid JSON. Reinitializing config...'
            remove(root_dir + "config.json")
            load_config()
            return

        for i,v in init_config.items():
            if i not in config:
                config[i] = v

    save_config()



def a_sync(func, ThreadClass=QtCore.QThread):

    # if reference to QThread is not global,
    # python's garbage collection cleans up QThread whilst running causing a crash in IDA
    # to prevent this we have an array of global thread references which expands as nessecary

    thread_idx = next((i for i, v in enumerate(threads) if not v.isRunning()), False)
    thread = ThreadClass()

    if thread_idx is not False:
        threads[thread_idx] = thread
    else:
        threads.append(thread)

    thread.run = func
    thread.start()


max_iterations = 10
iterations = 0

codeSegment = get_segm_by_name(".text")

if codeSegment:
    codeStart = codeSegment.startEA
    codeEnd = codeSegment.endEA

b_red = 'red'
b_green = 'green'
b_yellow = 'yellow'
b_lightblue = 'blue'

file_name = None
_32_bit = None
root_dir = __file__[:max(__file__.rfind("/"), __file__.rfind("\\"), 0)] + "/"
warning = None
config = None

load_config()

threads = []

