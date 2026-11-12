"""Regression: repeatedly seek paused media, then immediately switch files."""
import sys,pathlib,multiprocessing
sys.path.insert(0,str(pathlib.Path(__file__).parents[1]))
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from jingpeek.app import Window

def run():
    root=pathlib.Path(sys.argv[1]).resolve();sys.argv.append('--verify');app=QApplication([]);app.setQuitOnLastWindowClosed(False);w=Window()
    try:
        for i in range(15):
            for name in ('09-audio.wav','12-video.mp4'):
                w.preview(root/name);QTest.qWait(160)
                for _ in range(25):
                    if w.media.duration()>0:break
                    QTest.qWait(50)
                assert w.media.error()==w.media.Error.NoError,w.media.errorString()
                assert w.media.duration()>0,'media did not load'
                w.media.pause();w.media.setPosition(700)
                w.preview(root/'10-unknown.xyz');QTest.qWait(20)
            print('media switching cycle',i+1,flush=True)
        print('PASS: 30 immediate paused-seek -> file-switch transitions')
    finally:w.quit_app()

if __name__=='__main__':multiprocessing.freeze_support();run()
