#!/usr/bin/env python3
import time, pickle
import tkinter as tk
from functools import partial

PICKLE_FILE = "canvas.pickle"

def pairs(l, loop=False):
    if not l: return
    first = l[0]
    for i in l[1:]:
        second = i
        yield (first, second)
        first = second
    if loop:
        yield (first, l[0])

class Viewport:
    def __init__(self, viewport=None):
        if viewport:
            self.x = viewport.x
            self.y = viewport.y
            self.z = viewport.z
            self.a = viewport.a
        else:
            self.x = 0
            self.y = 0
            self.z = 1
            self.a = 0
    def subtract(self, viewport):
        vp = Viewport(self)
        vp.x -= viewport.x
        vp.y -= viewport.y
        vp.z -= viewport.z ## TODO needs to be division?
        vp.a -= viewport.a
        return vp
    def visible(self, viewport):
        """True if self is visible from viewport"""
        return True

class Stroke:
    def __init__(self, path, color, style):
        self.path = path
        self.color = color
        self.style = style
    def render(self, canvas, vieport):
        for p1, p2 in pairs(self.path, loop=False):
            obj_id = canvas.create_line(*p1, *p2, fill=self.color, width=3)

class Frame:
    def __init__(self, viewport):
        self.viewport = viewport
        self.create_time = time.time()
        self.modify_time = self.create_time
        self.drawables = []
        print("new frame")
    def pop_stroke(self):
        if not self.drawables: return None
        return self.drawables.pop()
    def render(self, canvas, current_viewport):
        vp_diff = self.viewport.subtract(current_viewport)
        for drawable in self.drawables:
            drawable.render(canvas, vp_diff)

class Data:
    def __init__(self):
        """Only exec when starting fresh"""
        print("created")
        self.initial_viewport = Viewport()
        self.frames = []
        self.frame_lru = []
    def initialize(self):
        """exec always"""
        print("init")
        self.resolution = 500
        self.current_viewport = self.initial_viewport
    def push_sketch(self, sketch):
        if not self.frame_lru or not self.frame_lru[0].viewport is self.current_viewport:
            frame = Frame(self.current_viewport)
            self.frames.append(frame)
            self.frame_lru.append(frame)
        else:
            frame = self.frame_lru[-1]
        sketch.blit(frame)
    def pop_frame(self):
        if not self.frames: return None
        frame = self.frame_lru.pop()
        self.frames.remove(frame)
        return frame
    def pop_stroke(self):
        if not self.frames: return None
        frame = self.frame_lru[-1]
        return frame.pop_stroke()
    def render(self, canvas):
        for frame in self.frames:
            frame.render(canvas, self.current_viewport)

class Sketch:
    def __init__(self):
        self.stroke = Stroke([], "#BCB534", None)
    def push(self, x, y):
        self.stroke.path.append( (x,y) )
    def blit(self, frame):
        print(f"Adding stroke {id(self.stroke)} to frame {id(frame)}")
        frame.drawables.append(self.stroke)
        self.stroke = Stroke([], "#BCB534", None)
    def render(self, canvas):
        for p1, p2 in pairs(self.stroke.path, loop=False):
            obj_id = canvas.create_line(*p1, *p2, fill="#BC347F", width=12)

def quit(event, context):
    context.root.quit()

def delete_frame(event, context):
    _ = context.data.pop_frame()
    context.redraw()

def undo_stroke(event, context):
    _ = context.data.pop_stroke()
    context.redraw()

def start_draw(event, context):
    x, y = event.x, event.y
    context.sketch.push(x, y)
    context.redraw()
def continue_draw(event, context):
    x, y = event.x, event.y
    context.sketch.push(x, y)
    context.redraw()
def stop_draw(event, context):
    x, y = event.x, event.y
    context.sketch.push(x, y)
    context.data.push_sketch(context.sketch)
    context.redraw()

class Context:
    def __init__(self, data):
        self.root = tk.Tk()
        self.canvas = tk.Canvas(self.root)
        self.canvas.configure(bg='#242424')
        self.data = data
        self.sketch = Sketch()
    def redraw(self):
        self.canvas.delete("all")
        self.data.render(self.canvas)
        self.sketch.render(self.canvas)

def init_gui(context):
    context.canvas.pack(expand = True, fill = tk.BOTH)
    context.canvas.bind_all("<Key-q>", partial(quit, context=context))
    context.canvas.bind_all("<Key-d>", partial(delete_frame, context=context))
    context.canvas.bind_all("<Key-u>", partial(undo_stroke, context=context))
    context.canvas.bind("<Button-1>", partial(start_draw, context=context))
    context.canvas.bind("<B1-Motion>", partial(continue_draw, context=context))
    context.canvas.bind("<ButtonRelease-1>", partial(stop_draw, context=context))
    #contect.canvas.bind("<Button-3>", partial(start_move, context=context))
    #contect.canvas.bind("<B3-Motion>", partial(continue_move, context=context))
    #contect.canvas.bind("<ButtonRelease-3>", partial(stop_move, context=context))

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
    data.render(context.canvas)
    tk.mainloop()

    print("pickling")
    with open(PICKLE_FILE, "wb") as fd:
        pickle.Pickler(fd).dump(data)

if __name__ == "__main__":
    main()
