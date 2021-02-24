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

def start_draw(event, context):
    cursor_pos = np.array([event.x, event.y])
    p = context.viewport.screen_to_world(context, cursor_pos)
    context.sketch.push(p)
    context.redraw()
def continue_draw(event, context):
    cursor_pos = np.array([event.x, event.y])
    p = context.viewport.screen_to_world(context, cursor_pos)
    context.sketch.push(p)
    context.redraw()
def stop_draw(event, context):
    cursor_pos = np.array([event.x, event.y])
    p = context.viewport.screen_to_world(context, cursor_pos)
    context.sketch.push(p)
    context.data.push_sketch(context)
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

    labelExample = tk.Label(context.root, text="q:quit, u:undo, d:delete(recent): b:debug")
    labelExample.pack()

    context.canvas = tk.Canvas(context.root)
    context.canvas.configure(bg='#242424')
    context.canvas.pack()
    def choose_color(context):
        rgb, hexstr = colorchooser.askcolor(title ="Choose color")
        if hexstr:
            context.sketch.set_color(hexstr)
    button = Button(context.root, text = "Select color",
       command = partial(choose_color, context=context))
    button.pack()

    context.canvas.pack(expand = True, fill = tk.BOTH)
    context.canvas.bind_all("<Key-q>", partial(quit, context=context))
    context.canvas.bind_all("<Key-d>", partial(delete_frame, context=context))
    context.canvas.bind_all("<Key-u>", partial(undo_stroke, context=context))
    context.canvas.bind_all("<Key-b>", partial(toggle_debug, context=context))
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
