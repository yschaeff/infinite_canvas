import time, pickle
import tkinter as tk
from functools import partial

PICKLE_FILE = "canvas.pickle"

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
        pass

class Frame:
    def __init__(self, viewport):
        self.viewport = viewport
        self.create_time = time.time()
        self.modify_time = self.create_time
        self.drawables = []
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
    def initialize(self):
        """exec always"""
        print("init")
        self.resolution = 500
        self.current_viewport = self.initial_viewport
    def render(self, canvas):
        for frame in self.frames:
            frame.render(canvas, self.viewport)

def quit(event, context):
    context.root.quit()

class Context:
    def __init__(self, data):
        self.root = tk.Tk()
        self.canvas = tk.Canvas(self.root)
        self.data = data

def init_gui(context):
    context.canvas.pack(expand = True, fill = tk.BOTH)
    context.canvas.bind_all("<Key-q>", partial(quit, context=context))

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
