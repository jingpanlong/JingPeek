"""Bounded daemon jobs: slow Shell calls never block the preview window."""
import threading,pathlib,os,time
from PySide6.QtCore import QObject,Signal,QCoreApplication,QEventLoop
from .formats import natural

class Background(QObject):
    selected=Signal(int,object,object,str)
    directory=Signal(int,object,object)
    def __init__(self,parent=None):super().__init__(parent);self.closed=False;self.selection_generation=None;self.selection_threads=[]
    def close(self):
        self.closed=True;self.selection_generation=None;deadline=time.monotonic()+2.5
        for thread in self.selection_threads:
            while thread.is_alive() and thread is not threading.current_thread() and time.monotonic()<deadline:
                thread.join(.01)
                # OLE clipboard providers can live on our GUI thread. Let them
                # render data while a pending compatibility read restores it.
                QCoreApplication.processEvents(QEventLoop.ExcludeUserInputEvents,10)
    def cancel_selection(self):self.selection_generation=None
    def publish(self,name,*args):
        if not self.closed:
            try:getattr(self,name).emit(*args)
            except RuntimeError:pass
    def resolve(self,generation,hwnd):
        self.selection_generation=generation
        def run():
            import pythoncom
            pythoncom.CoInitialize()
            try:
                from .native import selection,selection_anchor
                paths=selection(hwnd,cancelled=lambda:self.closed or self.selection_generation!=generation)
                anchor=selection_anchor(paths) if paths else None
                self.publish('selected',generation,paths,anchor,'')
            except Exception as e:self.publish('selected',generation,[],None,str(e))
            finally:pythoncom.CoUninitialize()
        thread=threading.Thread(target=run,daemon=True,name='Explorer selection');self.selection_threads=[t for t in self.selection_threads if t.is_alive()]+[thread];thread.start()
    def scan(self,generation,selected):
        def run():
            try:
                with os.scandir(selected.parent) as entries:paths=sorted((pathlib.Path(e.path) for e in entries if e.is_file()),key=natural)
                if selected not in paths:paths=[selected]
            except OSError:paths=[selected]
            self.publish('directory',generation,selected,paths)
        threading.Thread(target=run,daemon=True,name='Preview queue').start()
