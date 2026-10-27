"""lldb script for wedge_autopsy (env.sh): name the path a wedged claude's main
thread is blocked opening. Loaded with `command script import` inside an
attached lldb; runs once on import, prints to lldb's stdout.

The syscall's argument registers are clobbered by the time a debugger stops
the thread (x0 already holds the interrupted return value), so the path is
recovered from the callee-saved registers and the top of the stack, which
still hold the caller's copies. Then the blocked open is forced to return -1
so the caller reports the path itself in claude's own debug log."""

import struct

import lldb  # type: ignore[import-not-found]

_USER_SPACE = (0x1_0000_0000, 0x7FFF_FFFF_FFFF)


def _cstring(process, addr):
    # ReadCStringFromMemory raises SystemError on an unmapped address in the
    # Python binding; a raw read split at NUL is the reliable form.
    err = lldb.SBError()
    try:
        raw = process.ReadMemory(addr, 512, err)
    except Exception:  # noqa: BLE001 - any binding failure means "not a string"
        return None
    if not err.Success() or not raw:
        return None
    s = bytes(raw).split(b"\0", 1)[0]
    if len(s) < 2 or not all(32 <= c < 127 for c in s):
        return None
    return s.decode("ascii")


def __lldb_init_module(debugger, _internal_dict):
    process = debugger.GetSelectedTarget().GetProcess()
    thread = process.GetThreadAtIndex(0)
    frame = thread.GetFrameAtIndex(0)
    print("frame0:", frame.GetFunctionName(), hex(frame.GetPC()))
    for i in range(min(thread.GetNumFrames(), 15)):
        f = thread.GetFrameAtIndex(i)
        print(f"  #{i} {f.GetFunctionName()} {hex(f.GetPC())}")
    paths = []
    for reg in frame.GetRegisters().GetValueAtIndex(0):
        try:
            val = int(reg.GetValue(), 0)
        except (TypeError, ValueError):
            continue
        if _USER_SPACE[0] <= val < _USER_SPACE[1]:
            s = _cstring(process, val)
            if s is not None:
                print(f"  {reg.GetName()} -> {s!r}")
                if "/" in s:
                    paths.append(s)
    err = lldb.SBError()
    stack = process.ReadMemory(frame.GetSP(), 1024, err)
    if err.Success():
        for off in range(0, len(stack) - 7, 8):
            (v,) = struct.unpack_from("<Q", stack, off)
            if _USER_SPACE[0] <= v < _USER_SPACE[1]:
                s = _cstring(process, v)
                if s is not None and "/" in s:
                    print(f"  sp+{off} -> {s!r}")
                    paths.append(s)
    print("AUTOPSY_PATH:", paths[0] if paths else "none")
    if "open" in (frame.GetFunctionName() or ""):
        thread.ReturnFromFrame(frame, frame.EvaluateExpression("(long)-1"))
        print("forced the blocked open to return -1")
    process.Detach()
