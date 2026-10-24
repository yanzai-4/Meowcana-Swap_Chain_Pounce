"""Device-time cost model for one frame of TFT drawing. Single source of truth for Screen.stats() and
tools/sim.py. Constants come from measurements on the console (see docs/demo-plan.md section 2).
"""

RPC_MS = 17.0          # one arcade_draw_ops Bridge call (also returns the next input snapshot)
OP_MS = 1.5            # per drawing op: parse + address-window setup
FAST_KPX = 770.0       # solid fill whose RGB565 high byte equals its low byte (one bus write per pixel)
SLOW_KPX = 180.0       # other fills, bitmaps, glyph cells: two bus writes per pixel plus decode
RUN_MS = 0.06          # one extra address window (transparent text / asset runs, dotted dashes)

IDLE_LIMIT_MS = 45.0   # menus and idle screens
BUSY_LIMIT_MS = 70.0   # frames while the scene declares busy = True


def is_fast(color):
    return (color >> 8) == (color & 0xFF)


def frame_ms(chunks, ops, fast_px, slow_px, runs=0):
    return (chunks * RPC_MS + ops * OP_MS + runs * RUN_MS
            + fast_px / FAST_KPX + slow_px / SLOW_KPX)
