"""Render each redesigned surface for visual review without changing settings."""
import sys,pathlib,time,multiprocessing
sys.path.insert(0,str(pathlib.Path(__file__).parents[1]))
from PySide6.QtWidgets import QApplication,QMessageBox,QInputDialog,QFileDialog
from PySide6.QtCore import QRect
from PySide6.QtTest import QTest
from jingpeek.app import Window,CSS
from jingpeek.ui import palette,install_theme

def run():
    fixture=pathlib.Path(sys.argv[1]).resolve();out=pathlib.Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
    sys.argv.append('--verify')
    app=QApplication([]);install_theme(app);app.setQuitOnLastWindowClosed(False);w=Window()
    def save(widget,name):widget.show();QTest.qWait(180);assert widget.grab().save(str(out/(name+'.png')))
    def wait():
        end=time.monotonic()+25
        while w.proc and time.monotonic()<end:QTest.qWait(60)
    try:
        w.dashboard();save(w,'01-软件介绍')
        w.about();save(w,'02-关于与联系')
        for method,name in [(w.show_settings,'03-偏好设置'),(w.show_recent,'04-最近预览')]:
            d=method(preview_only=True);save(d,name);d.close();d.deleteLater()
        w.load_paths([fixture/'01-欢迎.md'],popup=True,anchor=QRect(100,100,80,25));wait();save(w,'05-浮动预览')
        d=w.show_file_info(preview_only=True);save(d,'06-文件信息');d.close();d.deleteLater()
        w.load_paths([fixture/'02-demo.py'],popup=True);wait();save(w,'07-代码高亮')
        w.load_paths([fixture/'09-audio.wav'],popup=True);QTest.qWait(300);w.media.pause();save(w,'08-音频预览')
        w.error('文件可能已移动，或暂时无法读取。你可以继续预览其他文件。');save(w,'09-错误提示')
        d=QMessageBox(QMessageBox.Information,'提示 · 景速览','文件路径已复制。',QMessageBox.Ok,w);save(d,'10-消息弹窗');d.close()
        d=QInputDialog(w);d.setWindowTitle('查找当前内容');d.setLabelText('输入关键字');save(d,'11-查找对话框');d.close()
        d=QFileDialog(w,'选择要预览的文件',str(fixture));d.setOption(QFileDialog.DontUseNativeDialog);d.resize(850,550);save(d,'12-文件选择');d.close()
        print('Rendered 12 light-theme surfaces')
    finally:w.quit_app()

if __name__=='__main__':multiprocessing.freeze_support();run()
