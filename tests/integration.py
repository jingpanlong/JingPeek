"""Real Qt preview integration; generates its own fixtures, no user files touched."""
import sys, pathlib, os, time, tempfile, wave, struct, zipfile, multiprocessing
sys.path.insert(0,str(pathlib.Path(__file__).parents[1]))
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QPdfWriter,QPainter,QImage,QColor
from PySide6.QtTest import QTest
from jingpeek.app import Window,CSS

def run():
    app=QApplication([]);app.setStyleSheet(CSS);app.setQuitOnLastWindowClosed(False)
    root=pathlib.Path(__file__).parents[2]/'fixtures';root.mkdir(exist_ok=True)
    (root/'01-欢迎.md').write_text('# 景速览\n\n文件里的世界，一按即现。\n\n## 每一眼都有收获\n\n- 支持 Markdown 排版\n- 代码高亮与表格\n\n|类型|状态|\n|---|---|\n|本地预览|就绪|\n\n```python\nprint("你好，世界")\n```',encoding='utf-8')
    (root/'02-demo.py').write_text('from pathlib import Path\n\ndef preview(file: Path):\n    """让每个文件先被看见。"""\n    return file.read_text(encoding="utf-8")\n',encoding='utf-8')
    im=QImage(1200,750,QImage.Format_RGB32);im.fill(QColor('#182c45'));p=QPainter(im);p.setPen(QColor('#8bb5ff'));font=p.font();font.setPointSize(44);p.setFont(font);p.drawText(80,180,'JING PEEK');p.setPen(QColor('#78ddc3'));p.drawEllipse(720,180,300,300);p.end();im.save(str(root/'03-image.png'))
    writer=QPdfWriter(str(root/'04-document.pdf'));writer.setResolution(96);p=QPainter(writer);p.drawText(100,100,'JingPeek PDF / Page 1');writer.newPage();p.drawText(100,100,'Page 2 / Multi-page preview');p.end()
    from docx import Document
    d=Document();d.add_heading('Word 内容预览',0);d.add_paragraph('可阅读文字和表格。');d.save(root/'05-Word.docx')
    from openpyxl import Workbook
    w=Workbook();w.active.append(['项目','数量']);w.active.append(['测试',42]);w.save(root/'06-Excel.xlsx')
    from pptx import Presentation
    r=Presentation();s=r.slides.add_slide(r.slide_layouts[0]);s.shapes.title.text='幻灯片预览';r.save(root/'07-slides.pptx')
    with zipfile.ZipFile(root/'08-archive.zip','w') as z:z.writestr('资料/hello.txt','hello')
    with wave.open(str(root/'09-audio.wav'),'w') as audio:audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(8000);audio.writeframes(b'\0\0'*16000)
    (root/'10-unknown.xyz').write_bytes(b'\x00\x01\x02');(root/'11-broken.pdf').write_bytes(b'bad pdf')
    window=Window();window.show();QTest.qWait(150);results=[]
    def preview(name):
        window.load_paths([root/name]);start=time.monotonic()
        while window.proc and time.monotonic()-start<35:QTest.qWait(70)
        QTest.qWait(100)
        assert not window.proc,'parser did not finish'
    try:
        for name,token in [('01-欢迎.md','每一眼'),('02-demo.py','preview'),('05-Word.docx','可阅读'),('06-Excel.xlsx','42'),('07-slides.pptx','幻灯片预览'),('08-archive.zip','hello.txt')]:
            preview(name);assert token in window.browser.toPlainText(),(name,window.browser.toPlainText());results.append(name+' PASS')
        preview('03-image.png');assert window.image.pix.width()==1200;window.actual();assert window.image.zoom==1;window.image.rotate();assert window.image.angle==90;window.fit();results.append('image fit / actual / rotate PASS')
        window.copy_path();assert '03-image.png' in app.clipboard().text();window.hash_file();assert len(app.clipboard().text())==64;results.append('copy path / SHA256 PASS')
        preview('04-document.pdf');assert window.pdfdoc.pageCount()==2;results.append('PDF pages PASS')
        preview('09-audio.wav');QTest.qWait(800);assert window.media.error()==window.media.Error.NoError;assert window.media.duration()==2000;window.play_pause();results.append('audio decode / duration PASS')
        preview('10-unknown.xyz');assert '没有内置' in window.browser.toPlainText();results.append('unknown fallback PASS')
        preview('11-broken.pdf');assert '暂时无法' in window.browser.toPlainText();results.append('damaged PDF PASS')
        window.load_paths([root/'01-欢迎.md',root/'02-demo.py']);QTest.qWait(100);window.activateWindow();QTest.qWait(100)
        QTest.keyClick(window,Qt.Key_Right);assert window.path.name=='02-demo.py';results.append('arrow navigation PASS')
        QTest.keyClick(window,Qt.Key_Escape);assert not window.isVisible();results.append('Esc hide PASS')
        window.about();assert '景同志' in window.browser.toPlainText() and '景同学' in window.browser.toPlainText();results.append('about author contacts PASS')
        window.home();window.show();QTest.qWait(100);window.grab().save(str(root/'home.png'))
        preview('01-欢迎.md');window.grab().save(str(root/'markdown.png'))
    finally:window.quit_app()
    print('\n'.join(results));return root

if __name__=='__main__':multiprocessing.freeze_support();run()
