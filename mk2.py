#!/usr/bin/env python3
import time, pickle
import tkinter as tk
import numpy as np
from tkinter import colorchooser, Button
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
            self.p1 = viewport.p1.copy()
            self.p2 = viewport.p2.copy()
        else:
            self.p1 = np.array([-1.0, -1.0])
            self.p2 = np.array([1.0, 1.0])
    def __eq__(self, other):
        return np.all(self.p1 == other.p1) and np.all(self.p2 == other.p2)
    ## strokes associated with this viewport have coordinates between [-1, 1]
    def world_coordinates(self, pos):
        delta = self.p2 - self.p1
        return (pos+1)/2 * delta + self.p1

    def screen_to_world(self, context, cursor_pos):
        ##only valid if this is the current viewport
        screen_dim = context.bottomright - context.topleft
        vp_dim = context.viewport.p2 - context.viewport.p1

        pos = (cursor_pos - context.topleft)/screen_dim * vp_dim +\
            context.viewport.p1
        return pos

    def pan(self, context, delta):
        screen_dim = context.bottomright - context.topleft
        vp_dim = context.viewport.p2 - context.viewport.p1
        d = delta/screen_dim * vp_dim
        self.p1 += d
        self.p2 += d

    def zoom_in(self, context, cursor_pos, zoomin):  ##only valid if this is the current viewport
        screen_dim = context.bottomright - context.topleft
        relative_position = cursor_pos / screen_dim
        ## viewport
        delta = self.p2 - self.p1
        absolute_position = self.p1 + delta * relative_position

        zoomfactor = 0.1
        if zoomin:
            self.p1 += (absolute_position - self.p1) * zoomfactor
            self.p2 += (absolute_position - self.p2) * zoomfactor
        else:
            self.p1 -= (absolute_position - self.p1) * zoomfactor
            self.p2 -= (absolute_position - self.p2) * zoomfactor

    def visible(self, viewport):
        """True if self is visible from viewport"""
        return True
    def __str__(self):
        return f"<vp: {self.p1}, {self.p2}>"

class Stroke:
    def __init__(self, path, color, style=None, width=10):
        self.path = path
        self.color = color
        self.style = style
        self.width = width
    def render(self, canvas, mapper, draft=False):
        radius = 10;
        if draft and self.path:
            p1 = mapper(self.path[0]) + np.array([-radius, -radius])
            p2 = mapper(self.path[0]) + np.array([radius, radius])
            (x1, y1), (x2, y2) = p1, p2
            obj_id = canvas.create_oval(x1, y1, x2, y2, fill="#BC347F", width=self.width*3)
            p1 = mapper(self.path[-1]) + np.array([-radius, -radius])
            p2 = mapper(self.path[-1]) + np.array([radius, radius])
            (x1, y1), (x2, y2) = p1, p2
            obj_id = canvas.create_oval(x1, y1, x2, y2, fill="#BC347F", width=self.width*3)
        for p1, p2 in pairs(self.path, loop=False):
            (x1, y1) = mapper(p1)
            (x2, y2) = mapper(p2)
            obj_id = canvas.create_line(x1, y1, x2, y2, fill=self.color, width=self.width)

class Frame:
    def __init__(self, viewport):
        self.viewport = Viewport(viewport)
        self.create_time = time.time()
        self.modify_time = self.create_time
        self.drawables = []
        print("new frame")
    def pop_stroke(self):
        if not self.drawables: return None
        return self.drawables.pop()
    def render(self, context):
        ## context has our current viewport
        def world_to_screen(p, context, viewport):
            w = viewport.world_coordinates(p)
            screen_dim = context.bottomright - context.topleft
            vp_dim = context.viewport.p2 - context.viewport.p1
            pos = (p - context.viewport.p1)/vp_dim * screen_dim +\
                context.topleft
            return pos

        f = partial(world_to_screen, context=context, viewport=self.viewport)
        for drawable in self.drawables:
            drawable.render(context.canvas, f)

class Data:
    def __init__(self):
        """Only exec when starting fresh"""
        print("created")
        self.frames = []
        self.frame_lru = []
    def initialize(self):
        """exec always"""
        print("init")
        self.resolution = 500
    def push_sketch(self, context):
        if not self.frame_lru or self.frame_lru[-1].viewport != context.viewport:
            frame = Frame(context.viewport)
            self.frames.append(frame)
            self.frame_lru.append(frame)
        else:
            frame = self.frame_lru[-1]
        context.sketch.blit(frame)
    def pop_frame(self):
        if not self.frames: return None
        frame = self.frame_lru.pop()
        self.frames.remove(frame)
        return frame
    def pop_stroke(self):
        if not self.frames: return None
        frame = self.frame_lru[-1]
        return frame.pop_stroke()

    def render(self, context):
        for frame in self.frames:
            frame.render(context)

class Sketch:
    width = 3
    def __init__(self):
        self.color = "#BCB534"
        self.stroke = Stroke([], self.color, width=Sketch.width)
    def set_color(self, color):
        self.color = color
        self.stroke.color = color
    def push(self, p):
        self.stroke.path.append( p )
    def blit(self, frame):
        print(f"Adding stroke {id(self.stroke)} to frame {id(frame)}. len: {len(self.stroke.path)}")
        frame.drawables.append(self.stroke)
        self.stroke = Stroke([], self.color, width=Sketch.width)
    def render(self, context):
        ## context has our current viewport
        def world_to_screen(p, context, viewport):
            w = viewport.world_coordinates(p)
            screen_dim = context.bottomright - context.topleft
            vp_dim = context.viewport.p2 - context.viewport.p1
            pos = (p - context.viewport.p1)/vp_dim * screen_dim +\
                context.topleft
            return pos

        f = partial(world_to_screen, context=context, viewport=context.viewport)
        self.stroke.render(context.canvas, f, draft=True)

class Context:
    def __init__(self, data):
        self.root = None
        self.canvas = None
        self.data = data
        self.sketch = Sketch()
        self.topleft = np.array([0, 0])
        self.bottomright = np.array([0, 0])
        self.viewport = Viewport()
        self.drag_anchor = np.array([0, 0])

    def redraw(self):
        self.canvas.delete("all")
        self.data.render(self)
        self.sketch.render(self)

def quit(event, context):
    context.root.quit()

def delete_frame(event, context):
    _ = context.data.pop_frame()
    context.redraw()

def undo_stroke(event, context):
    _ = context.data.pop_stroke()
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
    context.redraw()

def resize(event, context):
    w, h = event.width, event.height
    if w < h:
        d = h-w
        context.topleft = np.array([0, d/2])
        context.bottomright = np.array([w, h-d/2])
    else:
        d = w-h
        context.topleft = np.array([d/2, 0])
        context.bottomright = np.array([w-d/2, h])
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
    context.redraw()
def stop_move(event, context):
    cursor_pos = np.array([event.x, event.y])
    p = context.viewport.screen_to_world(context, cursor_pos)
    context.redraw()

def scroll(event, context):
    cursor_pos = np.array([event.x, event.y])
    zoomin = (event.num == 4)
    context.viewport.zoom_in(context, cursor_pos, zoomin)
    context.redraw()

def init_gui(context):
    context.root = tk.Tk()

    #labelExample = tk.Label(context.root, text="This is a Label")
    #labelExample.pack()

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
    data.render(context)
    tk.mainloop()

    print("pickling")
    with open(PICKLE_FILE, "wb") as fd:
        pickle.Pickler(fd).dump(data)

if __name__ == "__main__":
    main()
