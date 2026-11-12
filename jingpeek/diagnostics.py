"""Optional offline packaged-runtime verification using caller-supplied fixtures."""
import pathlib, time, json, hashlib,re
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtMultimedia import QMediaPlayer

def verify(window,fixtures,report):
    app=QApplication.instance();results=[];report.parent.mkdir(parents=True,exist_ok=True)
    trace=(report.parent/'diagnostic-trace.txt').open('w',encoding='utf-8')
    import faulthandler
    faulthandler.dump_traceback_later(40,repeat=True,file=trace)
    def check(name,fn):
        report.write_text(json.dumps({'running':name,'results':results},ensure_ascii=False,indent=2),encoding='utf-8')
        start=time.perf_counter()
        try:fn();results.append({'test':name,'passed':True,'elapsed_ms':round((time.perf_counter()-start)*1000,1)})
        except Exception as e:results.append({'test':name,'passed':False,'error':str(e)})
    def load(name):
        p=fixtures/name
        assert p.exists(),'missing fixture '+name
        window.load_paths([p]);start=time.monotonic()
        while (window.proc or window.office.running) and time.monotonic()-start<125:QTest.qWait(75)
        QTest.qWait(200)
        assert window.proc is None and not window.office.running,'worker timed out'
    def text(name,token):
        load(name);assert token in window.browser.toPlainText(),window.browser.toPlainText()[:300]
    def image():
        load('03-image.png');assert window.image.pix.width()==1200
        window.actual();assert window.image.zoom==1;window.image.rotate();assert window.image.angle==90
        window.fit();window.grab().save(str(report.parent/'图片预览.png'))
    def pdf():
        load('04-document.pdf');assert window.pdfdoc.pageCount()==2
        window.actual();assert window.pdf.zoomFactor()==1;window.fit()
    def media(name):
        load(name);QTest.qWait(1000)
        assert window.media.error()==QMediaPlayer.NoError,window.media.errorString()
        assert window.media.duration()>=1900,'no duration'
        window.play_pause();window.media.setPosition(700);assert window.media.position()>=500
    def keys():
        window.load_paths([fixtures/'01-欢迎.md',fixtures/'02-demo.py']);window.show();window.activateWindow();QTest.qWait(200)
        QTest.keyClick(window,Qt.Key_Right);assert window.path.name=='02-demo.py'
        QTest.keyClick(window,Qt.Key_Escape);assert not window.isVisible()
    def meta():
        # Do not overwrite or race the user's clipboard while verification runs.
        from unittest.mock import patch
        class Clipboard:
            def setText(self,value):self.value=value
            def text(self):return self.value
        clipboard=Clipboard();load('03-image.png')
        with patch.object(QApplication,'clipboard',return_value=clipboard):
            window.copy_path();assert str((fixtures/'03-image.png').resolve())==clipboard.text(),'incorrect copied path'
            window.hash_file();assert clipboard.text()==hashlib.sha256((fixtures/'03-image.png').read_bytes()).hexdigest(),'incorrect digest'
    def about():
        window.about();assert all(x in window.browser.toPlainText() for x in ['景同志','景同学'])
        window.grab().save(str(report.parent/'关于页面.png'))
    def floating():
        from PySide6.QtCore import QRect
        screen=app.primaryScreen().availableGeometry();anchor=QRect(screen.left()+30,screen.top()+100,80,24)
        window.load_paths([fixtures/'01-欢迎.md'],popup=True,anchor=anchor)
        start=time.monotonic()
        while window.proc and time.monotonic()-start<30:QTest.qWait(75)
        QTest.qWait(150)
        assert window.windowFlags() & Qt.WindowStaysOnTopHint
        import win32gui
        assert win32gui.IsWindowVisible(int(window.winId())) and not win32gui.IsIconic(int(window.winId()))
        assert window.compact and window.sidebar.isHidden() and window.toolbar.isHidden()
        assert window.width()<=620 and window.height()<=480,(window.width(),window.height())
        assert screen.contains(window.geometry()),window.geometry()
        assert '每一眼' in window.browser.toPlainText()
        window.grab().save(str(report.parent/'文件旁浮动预览框.png'))
    def automation_binding():
        from comtypes.client import CreateObject
        from comtypes.gen.UIAutomationClient import CUIAutomation,IUIAutomation
        assert CreateObject(CUIAutomation,interface=IUIAutomation)
    def compatible_video(name):
        source=fixtures/name;before=hashlib.sha256(source.read_bytes()).hexdigest();window.load_paths([source]);QTest.qWait(120)
        if not window._using_compat:
            # Exercise the exact unsupported-codec error route even on systems that
            # already have a decoder for this test codec installed.
            window.media.errorOccurred.emit(QMediaPlayer.Error.FormatError,'Unsupported media, a codec is missing.')
        deadline=time.monotonic()+30
        while time.monotonic()<deadline:
            QTest.qWait(60)
            if window._using_compat and window.stack.currentWidget()==window.media_widget and window.compat.proc is None:break
        QTest.qWait(600)
        assert window._using_compat,'fallback was not enabled'
        assert window.stack.currentWidget()==window.media_widget,window.browser.toPlainText()[:500]
        assert window.media.error()==QMediaPlayer.Error.NoError,window.media.errorString()
        assert window.media.duration()>=1800,'compatibility file did not load'
        assert window.media.source().toLocalFile()!=str(source),'original unsupported input still selected'
        assert hashlib.sha256(source.read_bytes()).hexdigest()==before,'source was modified'
        window.grab().save(str(report.parent/(name+'-兼容预览.png')))
    def heic():
        load('16-photo.heic');assert window.image.pix.width()==160 and window.image.pix.height()==100
    def renamed_pdf():
        load('19-extensionless');assert window.pdfdoc.pageCount()==2
    def cancel_compat():
        window.load_paths([fixtures/'13-hevc-10bit.mp4']);window.start_compat();window.load_paths([fixtures/'20-unfamiliar-code.custom']);QTest.qWait(300)
        assert window.compat.proc is None and window.path.name=='20-unfamiliar-code.custom'
    def corrupt_media():
        window.load_paths([fixtures/'21-corrupt.mp4']);deadline=time.monotonic()+15
        while time.monotonic()<deadline:
            QTest.qWait(70)
            if window.stack.currentWidget()==window.browser and '十六进制' in window.browser.toPlainText():break
        assert '十六进制' in window.browser.toPlainText(),window.browser.toPlainText()[:500]
    def office_document(name,token,minimum=1,rich=False):
        source=fixtures/name;before=hashlib.sha256(source.read_bytes()).hexdigest();load(name)
        assert window.stack.currentWidget()==window.pdf,window.browser.toPlainText()[:800]
        assert window.pdfdoc.pageCount()>=minimum,(name,window.pdfdoc.pageCount())
        text=''.join(window.pdfdoc.getAllText(i).text() for i in range(window.pdfdoc.pageCount()))
        assert token in text,(name,text[:400])
        assert hashlib.sha256(source.read_bytes()).hexdigest()==before,'source changed'
        if rich:
            if name.endswith('.xlsx'):assert 'Sales chart' in text,'chart placeholder instead of real chart'
            if name.endswith('.pptx'):assert 'Values' in text,'chart placeholder instead of real chart'
            rendered=pathlib.Path(next(v[0] for k,v in window.office.cache.items() if k[0]==str(source.resolve())))
            assert re.search(rb'/Subtype\s*/Image',rendered.read_bytes()),'embedded pictures missing'
            window.grab().save(str(report.parent/(name+'-版式预览.png')))
        if name.endswith('.xlsx') and rich:
            assert window.page_selector.count()==3 and 'Dashboard' in window.page_selector.itemText(0)
            window.page_selector.setCurrentIndex(1);QTest.qWait(100);assert window.pdf.pageNavigator().currentPage()==1
    def office_cached():
        load('23-layout.docx');window.office.cache.clear()
        start=time.monotonic();load('23-layout.docx')
        assert window.stack.currentWidget()==window.pdf and not window.office.running
        assert time.monotonic()-start<1.5,'persistent preview cache did not avoid rendering'
    def cancel_office():
        window.office.cache.clear();window.office.disk.clear();window.load_paths([fixtures/'23-layout.docx']);assert window.office.running
        window.load_paths([fixtures/'02-demo.py']);QTest.qWait(200);assert not window.office.running and window.path.name=='02-demo.py'
    def languages():
        from PySide6.QtWidgets import QComboBox,QLabel
        from PySide6.QtCore import QSettings
        window.home();dialog=window.show_settings(preview_only=True);dialog.show();QTest.qWait(100)
        selector=dialog.findChild(QComboBox,'languageSelector');assert selector is not None
        selector.setCurrentIndex(1);QTest.qWait(100)
        assert dialog.windowTitle()=='Preferences · JingPeek'
        assert window.open_button.text()=='Open ↗'
        assert window.tray.contextMenu().actions()[2].text()=='Settings'
        assert any(label.text()=='Interface language' for label in dialog.findChildren(QLabel))
        assert QSettings(window.settings.fileName(),QSettings.IniFormat).value('language')=='en_US'
        assert dialog.grab().save(str(report.parent/'Language-English-Settings.png'))
        window.dashboard();assert window.grab().save(str(report.parent/'Language-English-Home.png'))
        window.about();assert 'Your files stay here' in window.browser.toPlainText()
        assert '景同志' in window.browser.toPlainText() and '景同学' in window.browser.toPlainText()
        assert window.grab().save(str(report.parent/'Language-English-About.png'))
        load('10-unknown.xyz');assert 'Detected type' in window.browser.toPlainText()
        load('01-欢迎.md');assert '每一眼' in window.browser.toPlainText()
        selector.setCurrentIndex(0);QTest.qWait(100)
        while window.proc:QTest.qWait(60)
        assert dialog.windowTitle()=='偏好设置 · 景速览' and window.open_button.text()=='打开 ↗'
        assert window.tray.contextMenu().actions()[2].text()=='设置'
        assert window.settings.value('language')=='zh_CN'
        assert dialog.grab().save(str(report.parent/'Language-Chinese-Settings.png'))
        dialog.close();dialog.deleteLater()
    try:
        for name,token in [('01-欢迎.md','每一眼'),('02-demo.py','preview'),('08-archive.zip','hello.txt')]:
            check(name,lambda n=name,t=token:text(n,t))
        for name,token in [('05-Word.docx','可阅读'),('06-Excel.xlsx','42'),('07-slides.pptx','幻灯片预览')]:check(name+' layout PDF',lambda n=name,t=token:office_document(n,t))
        check('image zoom/rotate',image);check('PDF multipage',pdf)
        check('WAV play/seek',lambda:media('09-audio.wav'));check('MP4 decode/seek',lambda:media('12-video.mp4'))
        check('unknown format',lambda:text('10-unknown.xyz','没有内置'))
        check('damaged PDF',lambda:text('11-broken.pdf','暂时无法'))
        check('navigation/hide',keys);check('path/SHA-256',meta);check('author contacts',about)
        window.home();QTest.qWait(100);window.grab().save(str(report.parent/'软件主界面.png'))
        load('01-欢迎.md');window.grab().save(str(report.parent/'Markdown预览.png'))
        check('compact floating preview / screen bounds',floating)
        check('Windows UI Automation binding',automation_binding)
        for name in ('13-hevc-10bit.mp4','14-vp9.mp4','15-av1.mp4'):
            if (fixtures/name).exists():check(name+' unsupported-codec fallback',lambda n=name:compatible_video(n))
        if (fixtures/'16-photo.heic').exists():check('HEIC image',heic)
        if (fixtures/'17-generic.unknown').exists():check('arbitrary binary hex preview',lambda:text('17-generic.unknown','十六进制'))
        if (fixtures/'18-empty.custom').exists():check('empty arbitrary file',lambda:text('18-empty.custom','空文件'))
        if (fixtures/'19-extensionless').exists():check('extensionless PDF detection',renamed_pdf)
        if (fixtures/'20-unfamiliar-code.custom').exists():
            check('arbitrary text extension',lambda:text('20-unfamiliar-code.custom','Hello, arbitrary'))
            check('cancel media conversion on navigation',cancel_compat)
        if (fixtures/'21-corrupt.mp4').exists():check('corrupt MP4 still has basic preview',corrupt_media)
        if (fixtures/'22-legacy.xls').exists():check('XLS full layout without Office',lambda:office_document('22-legacy.xls','Legacy XLS'))
        for name,token,count in [('23-layout.docx','WORD LAYOUT TEST',2),('24-layout.xlsx','EXCEL LAYOUT TEST',3),('25-layout.pptx','PPT LAYOUT TEST',2)]:
            if (fixtures/name).exists():check(name+' pictures / layout / navigation',lambda n=name,t=token,c=count:office_document(n,t,c,True))
        if (fixtures/'23-layout.docx').exists():
            check('persistent Office cache',office_cached)
            check('cancel isolated Office rendering',cancel_office)
        check('Chinese-English live switch / settings persistence / user content',languages)
        report.write_text(json.dumps({'all_passed':all(x['passed'] for x in results),'results':results},ensure_ascii=False,indent=2),encoding='utf-8')
    finally:faulthandler.cancel_dump_traceback_later();trace.close();window.quit_app()
