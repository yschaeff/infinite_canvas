#!/usr/bin/env python3
import time, pickle
import tkinter as tk
import numpy as np
from tkinter import colorchooser, Button
from functools import partial
from logic import Data, Viewport, Sketch, Frame

PICKLE_FILE = "canvas.pickle"

class Context:
    """This holds all the runtime context. Anything we don't care to save
       to file. """
    COLOR_SIZE = 48
    COLOR_GAP = 4
    def __init__(self, data):
            ## Main window
        self.root = None
            ## TKinter canvas to draw on
        self.canvas = None
            ## Long term storage
        self.data = data
            ## Scratchpad, what is being drawn *now*
        self.sketch = Sketch()
            ## Which part of the world is currently on screen?
        self.viewport = Viewport()
            ## Where, in pixel coords, does viewport map to?
        self.topleft = np.array([0, 0])
        self.bottomright = np.array([100, 100])
            ## Size of border around viewport when canvas is not square
        self.margin = np.array([0, 0])
            ## Start drag coordinate
        self.drag_anchor = np.array([0, 0])
            ## List of frames currently in view
        self.visible_frames = []
            ## set of colors currently in view
        self.visible_colors = set()
            ## Set to True is something changed on screen.
            ## TODO maybe in the future make this a state
            ## CLEAN / DRAW / IN / OUT / LEFT / RIGHT / UP / DOWN
            ## Then we can intelligently decide which frames to test
        self.dirty = True
            ## print/show some debug info
        self.debug = False
            ## are we performing a stroke now?
        self.drawing = False
        self.last_frame = None
        self.timers = []
    @classmethod
    def color_picker_location(c):
        r = c.COLOR_SIZE
        s = c.COLOR_GAP
        return np.array([s, s]), np.array([s+r, s+r])
    @classmethod
    def palette_location(c, index):
        r = c.COLOR_SIZE
        s = c.COLOR_GAP
        i = index + 1
        return np.array([s, s*(i+1)+r*i]), np.array([s+r, (s+r)*(i+1)])
    def redraw(self):
        self.canvas.delete("all")
        self.data.render(self)
        self.sketch.render(self)

def quit(event, context):
    context.root.quit()
def delete_frame(event, context):
    _ = context.data.pop_frame(context)
    context.dirty = True
    context.redraw()
def undo_stroke(event, context):
    _ = context.data.pop_stroke(context)
    context.dirty = True
    context.redraw()
def toggle_debug(event, context):
    context.debug ^= True
    context.redraw()


def moveto(context, vp):
    context.viewport = Viewport(vp)
    context.dirty = True
    context.redraw()

def move_to(context, viewport, dt=500):
    while context.timers:
        context.root.after_cancel(context.timers.pop())
    frametime_ms = 30/1000
    steps = int(dt*frametime_ms)
    for i in range(1, steps+1):
        vp = context.viewport.interpolate(viewport, steps, i)
        f = partial(moveto, context=context, vp=vp)
        f.__name__ = ""
        timer = context.root.after(i*dt//steps, f)
        context.timers.append(timer)

def next_frame(event, context):
    context.last_frame = context.data.next(context.last_frame)
    move_to(context, context.last_frame.viewport)
def prev_frame(event, context):
    context.last_frame = context.data.previous(context.last_frame)
    move_to(context, context.last_frame.viewport)

def scroll(event, context):
    cursor_pos = np.array([event.x, event.y])
    zoom_in = (event.num == 4)
    context.viewport.zoom(context, cursor_pos, zoom_in)
    context.dirty = True
    context.redraw()

def resize(event, context):
    w, h = event.width, event.height
    if w < h:
        margin = np.array([0, (h-w)/2])
    else:
        margin = np.array([(w-h)/2, 0])
    context.topleft = np.array([0, 0]) + margin
    context.bottomright = np.array([w, h]) - margin
    context.margin = margin
    context.dirty = True
    context.redraw()

def handle_hud(event, context):
    cursor_pos = np.array([event.x, event.y])
    shift = (event.state == 1)
    p1, p2 = context.color_picker_location()
    ##color picker
    if np.all(cursor_pos > p1) and np.all(cursor_pos < p2):
        rgb, hexstr = colorchooser.askcolor(title ="Choose color", color=context.sketch.color)
        if hexstr:
            if shift:
                context.canvas.configure(bg=hexstr)
            else:
                context.sketch.set_color(hexstr)
        return True
    for i, color in enumerate(context.visible_colors):
        p1, p2 = context.palette_location(i)
        if np.all(cursor_pos > p1) and np.all(cursor_pos < p2):
            context.sketch.set_color(color)
            return True
    return False

def start_draw(event, context):
    if not handle_hud(event, context):
        cursor_pos = np.array([event.x, event.y])
        p = context.viewport.screen_to_world(context, cursor_pos)
        context.sketch.push(p)
        context.drawing = True
    context.redraw()
def continue_draw(event, context):
    if not context.drawing: return
    cursor_pos = np.array([event.x, event.y])
    p = context.viewport.screen_to_world(context, cursor_pos)
    context.sketch.push(p)
    context.redraw()
def stop_draw(event, context):
    if not context.drawing: return
    cursor_pos = np.array([event.x, event.y])
    p = context.viewport.screen_to_world(context, cursor_pos)
    context.sketch.push(p)
    context.data.push_sketch(context)
    context.drawing = False
    context.dirty = True
    context.redraw()

def start_move(event, context):
    cursor_pos = np.array([event.x, event.y])
    context.drag_anchor = cursor_pos
    context.redraw()
def continue_move(event, context):
    cursor_pos = np.array([event.x, event.y])
    delta = context.drag_anchor - cursor_pos
    context.drag_anchor = cursor_pos
    context.viewport.pan(context, delta)
    context.dirty = True
    context.redraw()
def stop_move(event, context):
    cursor_pos = np.array([event.x, event.y])
    p = context.viewport.screen_to_world(context, cursor_pos)
    context.dirty = True
    context.redraw()

def init_gui(context):
    context.root = tk.Tk()

    labelExample = tk.Label(context.root, text="q:quit, u:undo, d:delete(recent): b:debug j:next k:prev")
    labelExample.pack()

    context.canvas = tk.Canvas(context.root)
    context.canvas.configure(bg='#242424')
    context.canvas.pack()

    context.canvas.pack(expand = True, fill = tk.BOTH)
    context.canvas.bind_all("<Key-q>", partial(quit, context=context))
    context.canvas.bind_all("<Key-d>", partial(delete_frame, context=context))
    context.canvas.bind_all("<Key-u>", partial(undo_stroke, context=context))
    context.canvas.bind_all("<Key-b>", partial(toggle_debug, context=context))
    context.canvas.bind_all("<Key-j>", partial(next_frame, context=context))
    context.canvas.bind_all("<Key-k>", partial(prev_frame, context=context))
    context.canvas.bind("<Button-1>", partial(start_draw, context=context))
    context.canvas.bind("<B1-Motion>", partial(continue_draw, context=context))
    context.canvas.bind("<ButtonRelease-1>", partial(stop_draw, context=context))
    context.canvas.bind("<Button-4>", partial(scroll, context=context))
    context.canvas.bind("<Button-5>", partial(scroll, context=context))
    context.canvas.bind("<Button-3>", partial(start_move, context=context))
    context.canvas.bind("<B3-Motion>", partial(continue_move, context=context))
    context.canvas.bind("<ButtonRelease-3>", partial(stop_move, context=context))
    context.canvas.bind("<Configure>", partial(resize, context=context))

def main():
    def load(fn):
        try:
            with open(PICKLE_FILE, "rb") as fd:
                return pickle.Unpickler(fd).load()
        except FileNotFoundError as e:
            print("No save file found. Creating new.")
            return Data()
        except Exception as e:
            print("unpickling failed", e)
            return Data()

    data = load(PICKLE_FILE)
    data.initialize()
    context = Context(data)
    init_gui(context)
    data.dirty = True
    tk.mainloop()

    print("pickling")
    with open(PICKLE_FILE, "wb") as fd:
        pickle.Pickler(fd).dump(data)

if __name__ == "__main__":
    main()
