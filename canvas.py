#!/usr/bin/env python3

import tkinter as tk

COMPRESSION = 5

def error(f, m, l):
    fx, fy = f
    mx, my = m
    lx, ly = l
    dx, dy = lx-fx, ly-fy
    if dx != 0:
        slope = dy/dx
        y = fy + slope * (fx-mx)
        return abs(round(y) - my)
    elif dy != 0:
        slope = dx/dy
        x = fx + slope * (fy-my)
        return abs(round(x) - mx)
    else:
        return 0

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
        print("before:", len(path))
        simplify(path, COMPRESSION)
        print("after:", len(path))
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
            print(obj_id)
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

def next_frame(event):
    global pos
    if frames.next():
        pos = frames.current_frame.origin
    plot()
def prev_frame(event):
    global pos
    if frames.prev():
        pos = frames.current_frame.origin
    plot()

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
