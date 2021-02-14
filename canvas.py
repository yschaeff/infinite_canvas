#!/usr/bin/env python3

import tkinter as tk
from math import sqrt
from time import sleep
from functools import partial

MAX_COMPRESSION_ERROR = 1.2

def line_point_distance(p1, p2, p):
    return abs((p2[0]-p1[0])*(p1[1]-p[1]) - (p1[0]-p[0])*(p2[1]-p1[1])) / sqrt( (p2[0] - p1[0])**2 + (p2[1]-p1[1])**2 )

def error(f, m, l):
    dx, dy = l[0]-f[0], l[1]-f[1]
    if dx == 0 and dy == 0: return 0
    return line_point_distance(f, l, m)

def simplify(path, max_error):
    start, end = 0, 2
    while end < len(path):
        M = path[start+1: end]
        m = map(lambda mi: error(path[start], mi, path[end]) <= max_error, M)
        if all(m) and end+1 < len(path):
            end += 1
            continue ## try adding another one!
        ## remove all between start and previous end
        for i in range(end - start - 2): path.pop(start+1)
        start += 1
        end = start + 2

class Frame():
    def __init__(self, origin):
        print("new frame")
        self.origin = origin
        self.paths = []
        #atime, mtime
    def add_path(self, path):
        simplify(path, MAX_COMPRESSION_ERROR)
        self.paths.append(path)
    def render(self, pos):
        if self.origin != pos:
            color = "#2F30F0"
        else:
            color = "#8d9e0e"
        for path in self.paths:
            for p1, p2 in pairs(path, loop=False):
                _ = canvas.create_line(*translate(p1, self.origin, pos),
                        *translate(p2, self.origin, pos), fill=color, width=5)
                #_ = canvas.create_oval(*translate(p1, self.origin, pos),
                        #*translate(p2, self.origin, pos), width=1)

class FrameCollection:
    def __init__(self):
        self.frames = []
        self.mre = [] #most recent edited
        self.current_frame = None
    def add_frame(self, frame):
        self.frames.append(frame)
        self.mre.append(frame)
        self.current_frame = frame
    def touch(self):
        self.mre.remove(self.current_frame)
        self.mre.append(self.current_frame)
    def prev(self):
        if not self.current_frame: return
        i = self.mre.index(self.current_frame)
        if i > 0:
            self.current_frame = self.mre[i-1]
        return True
    def next(self):
        if not self.current_frame: return False
        i = self.mre.index(self.current_frame)
        if i+1 < len(self.mre):
            self.current_frame = self.mre[i+1]
        return True
    def at(self, pos):
        if not self.current_frame: return False
        return pos == self.current_frame.origin
    def render(self, pos):
        for frame in self.frames:
            frame.render(pos)

pos = (0, 0)
move_anchor = pos
frames = FrameCollection()
staged = []

def pairs(l, loop=False):
    if not l: return
    first = l[0]
    for i in l[1:]:
        second = i
        yield (first, second)
        first = second
    if loop:
        yield (first, l[0])

def translate(point, origin, pos):
    x, y = point
    ox, oy = origin
    zx, zy = pos
    return ox+x-zx, oy+y-zy

def plot():
    canvas.delete("all")
    frames.render(pos)
    def plot_path(path, origin, pos):
        for p1, p2 in pairs(path, loop=False):
            obj_id = canvas.create_line(*translate(p1, origin, pos),
                    *translate(p2, origin, pos), fill="#c2d81b", width=8)
            #print(obj_id)
    plot_path(staged, pos, pos)

def undo(event):
    plot()
def redo(event):
    plot()

def start_move(event):
    global move_anchor
    x, y = event.x, event.y
    move_anchor = (x, y)
    plot()
def continue_move(event):
    global pos, move_anchor
    x, y = event.x, event.y
    pos = (pos[0] + move_anchor[0]-x, pos[1] + move_anchor[1]-y)
    move_anchor = (x, y)
    plot()
def stop_move(event):
    global pos, move_anchor
    x, y = event.x, event.y
    pos = (pos[0] + move_anchor[0]-x, pos[1] + move_anchor[1]-y)
    move_anchor = (x, y)
    plot()

def start_draw(event):
    x, y = event.x, event.y
    staged.clear()
    staged.append( (x, y) )
    plot()
def continue_draw(event):
    x, y = event.x, event.y
    staged.append( (x, y) )
    plot()
def stop_draw(event):
    x, y = event.x, event.y
    staged.append( (x, y) )
    if not frames.at(pos):
        frames.add_frame(Frame(pos))
    frames.current_frame.add_path(staged[:])
    frames.touch()
    staged.clear()
    plot()

def tick(npos):
    global pos
    pos = npos
    plot()

def moveto(new, dt=200):
    global pos
    steps = int(dt*30/1000)
    base = pos
    dx = (new[0]-pos[0])/steps
    dy = (new[1]-pos[1])/steps
    for i in range(1, steps+1):
        npos = (base[0]+i*dx, base[1]+i*dy)
        f = partial(tick, npos=npos)
        f.__name__ = ""
        master.after(i*dt//steps, f)

def next_frame(event):
    global pos
    if frames.next():
        moveto(frames.current_frame.origin)
def prev_frame(event):
    global pos
    if frames.prev():
        moveto(frames.current_frame.origin)

master = tk.Tk()
canvas = tk.Canvas(master)
canvas.pack(expand = True, fill = tk.BOTH)
#canvas.bind("<Motion>", move)
canvas.bind("<Button-1>", start_draw)
canvas.bind("<B1-Motion>", continue_draw)
canvas.bind("<ButtonRelease-1>", stop_draw)
canvas.bind("<Button-3>", start_move)
canvas.bind("<B3-Motion>", continue_move)
canvas.bind("<ButtonRelease-3>", stop_move)
canvas.bind_all("<Key-q>", exit)
canvas.bind_all("<Key-z>", undo)
canvas.bind_all("<Key-x>", redo)
canvas.bind_all("<Key-k>", prev_frame)
canvas.bind_all("<Key-j>", next_frame)
tk.mainloop()
