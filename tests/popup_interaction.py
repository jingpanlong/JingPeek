"""Exercise the Explorer hotkey callback and compact-window keys using a fixture."""
import sys,pathlib,multiprocessing,time
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).parents[1]))
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QRect,Qt,QTimer
from PySide6.QtTest import QTest
from jingpeek.app import Window,CSS

def run():
    fixture=pathlib.Path(sys.argv[1]).resolve();output=pathlib.Path(sys.argv[2]).resolve()
    sys.argv.append('--verify');app=QApplication([]);app.setStyleSheet(CSS);app.setQuitOnLastWindowClosed(False);w=Window()
    def wait():
        deadline=time.monotonic()+25
        while (w.proc or w._loading_selection) and time.monotonic()<deadline:QTest.qWait(75)
        assert w.proc is None
    try:
        def resolve(generation,hwnd):
            QTimer.singleShot(0,lambda:w.selection_ready(generation,[fixture],(100,100,80,25),''))
        with patch.object(w.background,'resolve',side_effect=resolve),patch('jingpeek.app.physical_anchor',return_value=QRect(100,100,80,25)),patch('jingpeek.native.u.GetForegroundWindow',return_value=0):
            w.from_explorer();wait();QTest.qWait(150)
            assert w.compact and w.path==fixture and not w.sidebar.isVisible() and not w.toolbar.isVisible()
            assert w.width()==600 and w.height()==460
            assert w.browser.toPlainText().strip()
            output.parent.mkdir(parents=True,exist_ok=True);w.grab().save(str(output))
            w.from_explorer();wait();assert not w.isVisible(),'same file + Space must toggle closed'
            w.from_explorer();wait();QTest.qWait(150);assert w.isVisible()
        QTest.keyClick(w,Qt.Key_Right);QTest.qWait(150);assert w.path!=fixture
        QTest.keyClick(w,Qt.Key_Escape);assert not w.isVisible()
        w.load_paths([fixture],popup=True);wait();QTest.qWait(150)
        QTest.keyClick(w,Qt.Key_Space);assert not w.isVisible()
        w.dashboard();assert not w.compact and w.sidebar.isVisible()
        print('PASS: hotkey callback -> 600x460 floating content -> toggle -> arrows -> Esc -> Space -> tray dashboard')
    finally:w.quit_app()

if __name__=='__main__':multiprocessing.freeze_support();run()
