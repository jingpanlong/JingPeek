from .i18n import tr, get_language, set_language, apply_language
import os, sys, pathlib, tempfile, multiprocessing as mp, time, json, hashlib, logging
# Windows Media Foundation avoids FFmpeg teardown deadlocks when seeking and
# immediately navigating away. Format decoding follows the system's codecs.
os.environ.setdefault('QT_MEDIA_BACKEND','windows')
from PySide6.QtCore import Qt, QUrl, QTimer, QSettings, QSize, QEvent, QRect, QPointF
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QImageReader, QDesktopServices, QMovie, QTextDocument, QCursor, QGuiApplication
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget, QListWidgetItem, QStackedWidget, QTextBrowser, QScrollArea, QFileDialog, QSplitter, QFrame, QSystemTrayIcon, QMenu, QSlider, QCheckBox, QMessageBox, QLineEdit, QDialog, QSizeGrip, QSizePolicy, QProgressBar, QComboBox)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPdfWidgets import QPdfView
from .localized_widgets import QLabel,QPushButton,QCheckBox,QMainWindow,QDialog,QLineEdit,QMenu,QSystemTrayIcon,QComboBox
from . import formats as f
from .native import SpaceHook, selection, selection_anchor, activate, show_preview
from .positioning import popup_geometry,physical_anchor
from .media_compat import MediaCompat
from .office_render import OfficeRenderer
from .parse_worker import worker
from .background import Background

APP='景速览'
GITHUB_REPO_URL='https://github.com/jingpanlong/JingPeek'
GITHUB_RELEASE_URL='https://github.com/jingpanlong/JingPeek/releases/latest'
from .ui import CSS, palette, svg_icon, setting_card, home_page, install_theme

def icon():
    pix=QPixmap(64,64); pix.fill(Qt.transparent)
    p=QPainter(pix); p.setRenderHint(QPainter.Antialiasing);p.setBrush(QColor('#3973ed'));p.setPen(Qt.NoPen);p.drawRoundedRect(2,2,60,60,15,15)
    p.setBrush(QColor('#ffffff'));p.drawEllipse(12,21,40,23);p.setBrush(QColor('#3973ed'));p.drawEllipse(26,26,13,13);p.end()
    return QIcon(pix)
def label(text,style=None):
    w=QLabel(text);w.setWordWrap(True)
    if style: w.setObjectName(style)
    return w
def button(text,fn,primary=False):
    b=QPushButton(text);b.clicked.connect(fn)
    if primary:b.setObjectName('primary')
    return b
class LocalBrowser(QTextBrowser):
    def loadResource(self, kind, name):
        # Local Markdown images only, within the document directory; never fetch network data.
        if hasattr(self,'local_root') and kind==QTextDocument.ImageResource and name.scheme() in ('','file'):
            try:
                p=pathlib.Path(name.toLocalFile() if name.isLocalFile() else self.local_root/name.path()).resolve()
                p.relative_to(self.local_root)
                if p.suffix.lower().lstrip('.') in f.IMAGE and p.stat().st_size<20*1024*1024:
                    reader=QImageReader(str(p));sz=reader.size()
                    if 0<sz.width()*sz.height()<20_000_000:return reader.read()
            except (OSError,ValueError):pass
        return None

class ImagePane(QScrollArea):
    def __init__(self,owner):
        super().__init__(); self.owner=owner; self.label=QLabel();self.label.setAlignment(Qt.AlignCenter)
        self.setWidget(self.label);self.setAlignment(Qt.AlignCenter);self.pix=None;self.zoom=1;self.angle=0;self.movie=None
    def load(self,p):
        self.clear()
        reader=QImageReader(str(p));s=reader.size()
        if s.width()*s.height()>80_000_000:raise ValueError(tr('图片超过 8,000 万像素，请用默认程序打开。'))
        reader.setAutoTransform(True);im=reader.read()
        if im.isNull():
            from pillow_heif import register_heif_opener
            register_heif_opener()
            from PIL import Image
            from PIL.ImageQt import ImageQt
            with Image.open(p) as pil:
                if pil.width*pil.height>80_000_000:raise ValueError(tr('图片过大'))
                im=ImageQt(pil.convert('RGBA')).copy()
        self.pix=QPixmap.fromImage(im);self.angle=0
        self.fit()
        if p.suffix.lower()=='.gif':
            self.movie=QMovie(str(p));self.label.setMovie(self.movie);self.movie.setScaledSize(self.label.size());self.movie.start()
    def clear(self):
        if self.movie:self.movie.stop();self.movie.deleteLater();self.movie=None
        self.label.clear();self.pix=None
    def fit(self):
        if self.pix:
            self.zoom=min((self.viewport().width()-24)/self.pix.width(),(self.viewport().height()-24)/self.pix.height(),1)
            self.draw()
    def draw(self):
        if not self.pix:return
        from PySide6.QtGui import QTransform
        pix=self.pix.transformed(QTransform().rotate(self.angle),Qt.SmoothTransformation)
        sz=QSize(max(1,int(pix.width()*self.zoom)),max(1,int(pix.height()*self.zoom)))
        self.label.resize(sz)
        if self.movie:self.movie.setScaledSize(sz)
        else:self.label.setPixmap(pix.scaled(sz,Qt.KeepAspectRatio,Qt.SmoothTransformation))
        self.owner.status.setText(tr('图片  ·  {p0} × {p1}  ·  {p2}%  ·  Ctrl + 滚轮缩放', p0=self.pix.width(), p1=self.pix.height(), p2=int(self.zoom * 100)))
    def wheelEvent(self,e):
        if e.modifiers() & Qt.ControlModifier:
            self.zoom=max(.02,min(8,self.zoom*(1.15 if e.angleDelta().y()>0 else 1/1.15)));self.draw();e.accept()
        else:super().wheelEvent(e)
    def rotate(self):
        if self.movie:return
        self.angle=(self.angle+90)%360;self.draw()

class Window(QMainWindow):
    def __init__(self):
        super().__init__();self.setWindowTitle(APP+tr(' · 文件快速预览'));self.setWindowIcon(icon());self.resize(1240,800);self.setMinimumSize(960,620)
        self.temp=tempfile.TemporaryDirectory(prefix='JingPeek-',ignore_cleanup_errors=True)
        self.settings=(QSettings(str(pathlib.Path(self.temp.name)/'verification.ini'),QSettings.IniFormat) if '--verify' in sys.argv else QSettings('JingTongXue','JingPeek'));self.paths=[];self.path=None;self.proc=None;self.pipe=None;self.original_hwnd=None;self.quitting=False;self.compact=False;self.drag_offset=None
        apply_language(os.environ.get('JINGPEEK_LANG',self.settings.value('language','zh_CN')));self.setWindowTitle(tr('景速览 · 文件快速预览'))
        self._request=0;self._queue_request=0;self._queue_offset=0;self._loading_selection=False;self._html_cache={};self._html_key=None
        self.background=Background(self);self.background.selected.connect(self.selection_ready);self.background.directory.connect(self.directory_ready)
        self.recent=list(self.settings.value('recent',[],type=list))[:30]
        self.compat=MediaCompat(self.temp.name,self);self.compat.ready.connect(self.compat_ready);self.compat.failed.connect(lambda reason:self.base_preview(tr('兼容解码未完成：')+reason));self.compat.progress.connect(self.compat_progress);self._media_active=False;self._using_compat=False;self._office_text_once=False
        cache_dir=(pathlib.Path(self.temp.name)/'cache' if '--verify' in sys.argv else pathlib.Path(os.environ.get('JINGPEEK_DATA',os.environ.get('LOCALAPPDATA',self.temp.name)))/'JingPeek/cache/office-v3')
        self.office=OfficeRenderer(self.temp.name,self,cache_dir=cache_dir);self.office.ready.connect(self.office_ready);self.office.failed.connect(self.office_error)
        self.media=QMediaPlayer(self);self.audio=QAudioOutput(self);self.media.setAudioOutput(self.audio);self.audio.setVolume(.65)
        root=QWidget();self.root=root;rootlayout=QHBoxLayout(root);rootlayout.setContentsMargins(0,0,0,0);rootlayout.setSpacing(0);self.setCentralWidget(root)
        side=QWidget();self.sidebar=side;side.setObjectName('sidebar');side.setFixedWidth(226);sl=QVBoxLayout(side);sl.setContentsMargins(18,25,18,18);sl.setSpacing(10)
        sl.addWidget(label(tr('◉  景速览'),'brand'));sl.addWidget(label('JING PEEK  /  1.6','muted'));sl.addSpacing(22)
        self.nav_buttons=[]
        for ico,caption,fn in [('plus',tr('选择文件'),self.choose),('home',tr('开始使用'),self.home),('clock',tr('最近预览'),self.show_recent),('settings',tr('偏好设置'),self.show_settings),('info',tr('关于与联系'),self.about)]:
            b=button(caption,fn,ico=='plus');b.setIcon(svg_icon(ico,'#ffffff' if ico=='plus' else '#71829d'));b.setIconSize(QSize(18,18))
            if ico!='plus':b.setObjectName('nav')
            if ico in ('home','info'):b.setCheckable(True)
            sl.addWidget(b);self.nav_buttons.append(b)
        sl.addSpacing(14);sl.addWidget(label(tr('当前文件夹 / 预览队列'),'muted'));self.files=QListWidget();self.files.currentRowChanged.connect(self.row_changed);sl.addWidget(self.files,1)
        sl.addWidget(label(tr('SPACE  即看即走\nESC  回到文件所在位置'),'muted'));rootlayout.addWidget(side)
        center=QWidget();cl=QVBoxLayout(center);self.center_layout=cl;cl.setContentsMargins(24,20,24,14);cl.setSpacing(14)
        self.header=QWidget();self.header.setObjectName('header');top=QHBoxLayout(self.header);top.setContentsMargins(0,0,0,0);self.title=label(tr('让文件，先被看见。'));self.title.setWordWrap(False);self.title.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Preferred);self.title.setStyleSheet('font-size:16px;font-weight:600');self.file_badge=label('JP');self.file_badge.setObjectName('fileBadge');top.addWidget(self.file_badge);top.addWidget(self.title,1)
        self.pin=button(tr('置顶'),lambda:self.set_pin(self.pin.isChecked()));self.pin.setCheckable(True);self.pin.setChecked(True);self.pin.setEnabled(False);self.pin.setToolTip(tr('预览窗口始终置顶'));self.setWindowFlag(Qt.WindowStaysOnTopHint,True);top.addWidget(self.pin)
        self.open_button=button(tr('打开 ↗'),self.open_file,True);top.addWidget(self.open_button);top.addWidget(button('⋯',self.popup_menu));self.close_button=button('×',self.hide_preview);self.close_button.setObjectName('closeButton');self.close_button.setToolTip(tr('关闭预览（Esc / 空格）'));top.addWidget(self.close_button);self.close_button.hide();cl.addWidget(self.header)
        self.toolbar=QWidget();toolbar=QHBoxLayout(self.toolbar);toolbar.setContentsMargins(0,0,0,0)
        for text,fn in [(tr('← 上一个'),lambda:self.step(-1)),(tr('下一个 →'),lambda:self.step(1)),(tr('适应窗口'),self.fit),('1:1',self.actual),(tr('旋转 90°'),lambda:self.image.rotate()),(tr('全屏 F11'),self.fullscreen)]:toolbar.addWidget(button(text,fn))
        toolbar.addStretch();cl.addWidget(self.toolbar)
        self.stack=QStackedWidget();self.stack.setObjectName('canvas');cl.addWidget(self.stack,1)
        self.browser=LocalBrowser();self.browser.setOpenLinks(False);self.browser.anchorClicked.connect(self.link_clicked);self.stack.addWidget(self.browser)
        self.compat_page=QWidget();cp=QVBoxLayout(self.compat_page);cp.setContentsMargins(32,32,32,32);cp.addStretch();cp.addWidget(label(tr('正在准备兼容预览'),'section'));self.compat_note=label(tr('内置解码，不需要安装系统编解码器。'),'muted');cp.addWidget(self.compat_note);self.compat_bar=QProgressBar();self.compat_bar.setRange(0,100);self.compat_bar.setValue(0);cp.addWidget(self.compat_bar);cp.addWidget(label(tr('不修改原文件。大文件首次准备可能较慢；可随时切换文件或取消。'),'muted'));cp.addWidget(button(tr('取消并查看文件原始内容'),lambda:self.base_preview(tr('已取消兼容解码。'))));cp.addStretch();self.stack.addWidget(self.compat_page)
        self.office_page=QWidget();op=QVBoxLayout(self.office_page);op.setContentsMargins(32,32,32,32);op.addStretch();op.addWidget(label(tr('正在生成原版式预览'),'section'));self.office_note=label(tr('保留图片、图表、分页和样式；首次渲染可能需要稍候。'),'muted');op.addWidget(self.office_note);bar=QProgressBar();bar.setRange(0,0);op.addWidget(bar);op.addWidget(button(tr('取消预览'),self.hide_preview));op.addStretch();self.stack.addWidget(self.office_page);self.office.progress.connect(self.office_note.setText)
        self.image=ImagePane(self);self.stack.addWidget(self.image)
        self.pdfdoc=QPdfDocument(self);self.pdf=QPdfView();self.pdf.setDocument(self.pdfdoc);self.pdf.setPageMode(QPdfView.PageMode.MultiPage);self.pdf.setZoomMode(QPdfView.ZoomMode.FitToWidth);self.stack.addWidget(self.pdf)
        self.pdf_controls=QWidget();pc=QHBoxLayout(self.pdf_controls);pc.setContentsMargins(0,0,0,0);pc.addWidget(button(tr('上一页'),lambda:self.jump_pdf_page(self.pdf.pageNavigator().currentPage()-1)));self.page_selector=QComboBox();self.page_selector.setMinimumWidth(140);self.page_selector.currentIndexChanged.connect(self.jump_pdf_page);pc.addWidget(self.page_selector,1);pc.addWidget(button(tr('下一页'),lambda:self.jump_pdf_page(self.pdf.pageNavigator().currentPage()+1)));pc.addWidget(button(tr('整页'),lambda:self.pdf.setZoomMode(QPdfView.ZoomMode.FitInView)));cl.insertWidget(cl.indexOf(self.stack),self.pdf_controls);self.pdf_controls.hide();self.pdf.pageNavigator().currentPageChanged.connect(self.pdf_page_changed)
        self.media_widget=QWidget();ml=QVBoxLayout(self.media_widget);ml.setContentsMargins(16,16,16,16);ml.setSpacing(16);self.video=QVideoWidget();self.media_surface=QStackedWidget();self.media_surface.addWidget(self.video)
        audio_page=QWidget();ap=QVBoxLayout(audio_page);ap.setAlignment(Qt.AlignCenter);cover=QLabel();cover.setAlignment(Qt.AlignCenter);cover.setPixmap(svg_icon('audio','#6088dc').pixmap(88,88));ap.addWidget(cover);ap.addSpacing(16);self.audio_title=label(tr('音频预览'),'section');self.audio_title.setAlignment(Qt.AlignCenter);ap.addWidget(self.audio_title);tip=label(tr('戴上耳机，听听文件里的声音。'),'muted');tip.setAlignment(Qt.AlignCenter);tip.setWordWrap(False);ap.addWidget(tip);self.audio_page=audio_page;self.media_surface.addWidget(audio_page);ml.addWidget(self.media_surface,1);self.media.setVideoOutput(self.video)
        controls=QHBoxLayout();self.play_button=button(tr('播放'),self.play_pause,True);controls.addWidget(self.play_button);self.seek=QSlider(Qt.Horizontal);controls.addWidget(self.seek,1);self.clock=label('00:00 / 00:00','muted');controls.addWidget(self.clock);controls.addWidget(label(tr('音量')));self.volume=QSlider(Qt.Horizontal);self.volume.setRange(0,100);self.volume.setValue(65);self.volume.setFixedWidth(75);self.volume.valueChanged.connect(lambda v:self.audio.setVolume(v/100));controls.addWidget(self.volume);ml.addLayout(controls);self.stack.addWidget(self.media_widget)
        self.media.playbackStateChanged.connect(lambda state:self.play_button.setText(tr('暂停') if state==QMediaPlayer.PlayingState else tr('播放')))
        self.media.hasVideoChanged.connect(lambda video:self.media_surface.setCurrentWidget(self.video if video else self.audio_page))
        self.media.durationChanged.connect(lambda v:self.seek.setRange(0,min(v,2147483647)));self.media.positionChanged.connect(self.media_position);self.seek.sliderMoved.connect(self.media.setPosition);self.media.errorOccurred.connect(lambda *_:self.media_error())
        self.hints=label(tr('← →  切换文件     Enter  打开     Space / Esc  收起'),'muted');cl.addWidget(self.hints);self.hints.hide()
        self.status=label(tr('本地预览  ·  文件内容不上传'),'muted');footer=QHBoxLayout();footer.addWidget(self.status,1);self.grip=QSizeGrip(self);footer.addWidget(self.grip);cl.addLayout(footer);rootlayout.addWidget(center,1)
        self.info=QWidget();self.info.setObjectName('panel');self.info.setFixedWidth(240);il=QVBoxLayout(self.info);il.setContentsMargins(20,25,20,20);il.addWidget(label(tr('文件信息'),'section'));self.info_text=label(tr('选择文件后查看信息'),'muted');self.info_text.setTextInteractionFlags(Qt.TextSelectableByMouse);il.addWidget(self.info_text);il.addSpacing(15);il.addWidget(button(tr('复制文件路径'),self.copy_path));il.addWidget(button(tr('定位文件'),self.reveal));il.addWidget(button(tr('保存预览截图'),self.export_preview));il.addWidget(button(tr('计算 SHA-256'),self.hash_file));self.hash_text=label('','muted');self.hash_text.setTextInteractionFlags(Qt.TextSelectableByMouse);il.addWidget(self.hash_text);il.addStretch();rootlayout.addWidget(self.info);self.info.hide()
        self.tray=QSystemTrayIcon(icon(),self);self.tray.setToolTip(APP+tr(' · 后台就绪 · 选中文件后按空格'));menu=QMenu();menu.addAction(tr('使用说明 / 软件介绍'),self.dashboard);menu.addAction(tr('选择文件预览'),self.choose);menu.addAction(tr('设置'),self.show_settings);menu.addAction(tr('关于与联系作者'),self.show_about);menu.addSeparator();menu.addAction(tr('退出景速览'),self.quit_app);self.tray.setContextMenu(menu);self.tray.activated.connect(lambda reason:self.dashboard() if reason==QSystemTrayIcon.DoubleClick else None);self.tray.show()
        self.hook=SpaceHook();self.hook.deskgo_enabled=self.settings.value('deskgo_compat',True,type=bool);self.hook.pressed.connect(self.from_explorer);self.hook.dismissed.connect(self.hide_preview);self.hook.failed.connect(lambda msg:self.status.setText(msg))
        if '--verify' not in sys.argv:self.hook.start()
        self.timer=QTimer(self);self.timer.timeout.connect(self.poll);self.timer.start(60)
        self.home_page=home_page(self);self.stack.addWidget(self.home_page);self.setAcceptDrops(True);QApplication.instance().installEventFilter(self);self.home()

    def html(self,body):
        self.browser.setHtml('<html><head><style>body{color:#34445d;background:#ffffff;font-family:Microsoft YaHei UI;font-size:14px;}h1{font-size:30px;color:#203454;}h2{font-size:19px;color:#345f9f;}h3{color:#395578;}a{color:#3973ed;}td{border-bottom:1px solid #e5ebf3;}th{background:#edf3ff;color:#315b9d;}code,pre{font-family:Consolas;}blockquote{color:#7c8da7;}p{line-height:1.65;}</style></head><body>'+body+'</body></html>');self.stack.setCurrentWidget(self.browser)

    def stop(self):
        self._media_active=False;self.compat.cancel();self.office.cancel();self.pdf_controls.hide()
        self.media.stop();self.media.setSource(QUrl());self.image.clear();self.pdfdoc.close()
        if self.proc:
            if self.proc.is_alive():self.proc.terminate()
            self.proc.join(2);self.proc.close();self.proc=None
        if self.pipe:self.pipe.close();self.pipe=None
    def home(self):
        if self.compact:self.set_mode(False)
        self.stop();self.path=None;self.open_button.setEnabled(False);self.nav_buttons[1].setChecked(True);self.nav_buttons[4].setChecked(False);self.title.setText(tr('让文件，先被看见。'))
        self.file_badge.setText('JP');self.stack.setCurrentWidget(self.home_page)
        self.status.setText(tr('空格监听已启用  ·  仅在资源管理器文件区 / 桌面生效'))
    def choose(self):
        d=QFileDialog(self,tr('选择要预览的文件'));d.setOption(QFileDialog.DontUseNativeDialog);d.setFileMode(QFileDialog.ExistingFiles);d.setViewMode(QFileDialog.Detail);d.resize(940,600)
        d.setLabelText(QFileDialog.LookIn,tr('所在位置'));d.setLabelText(QFileDialog.FileName,tr('文件名称'));d.setLabelText(QFileDialog.FileType,tr('文件类型'));d.setLabelText(QFileDialog.Accept,tr('预览'));d.setLabelText(QFileDialog.Reject,tr('取消'))
        if d.exec():self.load_paths([pathlib.Path(p) for p in d.selectedFiles()],popup=True)
    def load_paths(self,paths,popup=False,anchor=None):
        paths=[pathlib.Path(os.path.abspath(p)) for p in paths]
        if not paths:return
        self._queue_request+=1;self.set_mode(popup);selected=paths[0];self.paths=paths
        self.populate_queue(selected)
        # Paint before stat, decoding, spawning parsers or enumerating siblings.
        self.title.setText(selected.name);self.html('<h2>'+f.esc(selected.name)+tr('</h2><p>正在加载内容…</p>'))
        if popup:self.show_popup(anchor)
        else:self.restore()
        self.repaint();self.preview(selected)
        if len(paths)==1:self.background.scan(self._queue_request,selected)
    def populate_queue(self,selected):
        index=self.paths.index(selected) if selected in self.paths else 0
        self._queue_offset=max(0,index-500);visible=self.paths[self._queue_offset:self._queue_offset+1000]
        self.files.blockSignals(True);self.files.clear();self.files.addItems([p.name for p in visible]);self.files.setCurrentRow(index-self._queue_offset);self.files.blockSignals(False)
    def directory_ready(self,generation,selected,paths):
        if self.quitting or generation!=self._queue_request or not self.path or self.path.parent!=selected.parent:return
        current=self.path;self.paths=paths;self.populate_queue(current)
    def row_changed(self,n):
        index=n+self._queue_offset
        if n>=0 and index<len(self.paths):self.preview(self.paths[index])
    def step(self,d):
        if self.paths:
            index=self.paths.index(self.path) if self.path in self.paths else 0
            selected=self.paths[(index+d)%len(self.paths)];self.populate_queue(selected);self.preview(selected)
    def preview(self,p):
        self.stop();self.path=p;self.open_button.setEnabled(True);self.nav_buttons[1].setChecked(False);self.nav_buttons[4].setChecked(False);self.file_badge.setText(p.suffix.lstrip('.').upper()[:5] or 'FILE');self.hash_text.clear();self.title.setText(p.name);self.title.setToolTip(str(p));self.status.setText(tr('正在读取…'))
        self._using_compat=False
        self.browser.local_root=p.parent.resolve();self.browser.document().setBaseUrl(QUrl.fromLocalFile(str(p.parent)+os.sep))
        try:
            st=p.stat();self._html_key=(str(p),st.st_size,st.st_mtime_ns,get_language());self.info_text.setText(tr('{p0}\n\n{p1}\n\n类型：{p2}\n\n修改：{p3}\n\n{p4}', p0=p.name, p1=f.size(st.st_size), p2=p.suffix.upper() or tr('文件夹'), p3=time.strftime('%Y-%m-%d %H:%M', time.localtime(st.st_mtime)), p4=p.parent))
            self.recent=[str(p)]+[s for s in self.recent if s!=str(p)];self.recent=self.recent[:30];self.settings.setValue('recent',self.recent)
            if p.is_file() and st.st_size==0:self.base_preview();return
            if self._html_key in self._html_cache:
                self.html(self._html_cache[self._html_key]);self.status.setText(tr('已缓存的内容预览'));return
            typ=f.kind(p)
            if typ=='image':self.stack.setCurrentWidget(self.image);self.image.load(p)
            elif typ=='pdf':self.load_pdf(str(p))
            elif typ=='media':
                is_audio=p.suffix.lower() in ('.mp3','.wav','.flac','.aac','.m4a','.ogg','.opus','.wma','.ape','.aif','.aiff','.amr','.ac3','.dts','.alac','.mp2','.caf','.au','.mka');self.play_media(str(p),is_audio)
            elif typ in ('office','legacy') and self.settings.value('office_layout',True,type=bool) and not self._office_text_once:self.start_office()
            elif typ in ('text','office','archive','legacy','folder','unknown'):
                self.html(tr('<h2>正在准备预览…</h2><p>解析在独立进程中进行，可随时切换其他文件。</p>'))
                parent,child=mp.Pipe(False);self.pipe=parent;out=str(pathlib.Path(self.temp.name)/'office.pdf');self.proc=mp.Process(target=worker,args=(str(p),out,child,get_language()),daemon=True);self.proc.start();child.close();self.deadline=time.monotonic()+(60 if typ=='legacy' else 25)
            else:self.base_preview()
        except Exception as e:self.error(str(e))
    def poll(self):
        if not self.proc:return
        try:
            if self.pipe.poll():
                status,data=self.pipe.recv();self.proc.join(.2)
                if self.proc.is_alive():self.proc.terminate();self.proc.join(1)
                self.proc.close();self.proc=None;self.pipe.close();self.pipe=None
                if status=='error':self.error(data)
                elif data[0]=='pdf':self.load_pdf(data[1])
                else:
                    if len(data[1])<=1_000_000:self._html_cache[self._html_key]=data[1]
                    while len(self._html_cache)>32 or sum(map(len,self._html_cache.values()))>8_000_000:self._html_cache.pop(next(iter(self._html_cache)))
                    self.html(data[1]);self.status.setText(tr('只读内容预览 · Ctrl + F 查找 · Enter 默认程序打开'))
            elif time.monotonic()>self.deadline or not self.proc.is_alive():
                self.stop();self.error(tr('解析超时或进程已退出。加密、损坏或复杂文件请用默认程序打开。'))
        except (EOFError,OSError) as e:self.stop();self.error(str(e))
    def load_pdf(self,path,info=None):
        error=self.pdfdoc.load(path)
        if error!=QPdfDocument.Error.None_:raise ValueError(tr('PDF 无法读取，可能已损坏或有密码保护。'))
        self.pdf.setPageMode(QPdfView.PageMode.SinglePage if info and info.get('family')=='spreadsheet' else QPdfView.PageMode.MultiPage)
        self._pdf_info=info;names=self.pdf_names(info);count=self.pdfdoc.pageCount();self.page_selector.blockSignals(True);self.page_selector.clear();self.page_selector.addItems(names if len(names)==count else [tr('第 {p0} 页 / 共 {p1} 页', p0=n + 1, p1=count) for n in range(count)]);self.page_selector.blockSignals(False);self.pdf_controls.show();self.stack.setCurrentWidget(self.pdf)
        if info:self.pdf.setZoomMode(QPdfView.ZoomMode.FitToWidth if info.get('family')=='spreadsheet' else QPdfView.ZoomMode.FitInView)
        else:self.pdf.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        self.status.setText(tr('原版式预览 · {p0} 页 / 工作表 · 图片与图表保留 · Ctrl + 滚轮缩放', p0=count) if info else tr('PDF · 共 {p0} 页 · 滚轮翻页 · Ctrl + 滚轮缩放', p0=count))
    def jump_pdf_page(self,index):
        if 0<=index<self.pdfdoc.pageCount():self.pdf.pageNavigator().jump(index,QPointF(),0)
    def pdf_page_changed(self,index):
        if 0<=index<self.page_selector.count():self.page_selector.blockSignals(True);self.page_selector.setCurrentIndex(index);self.page_selector.blockSignals(False)
    def start_office(self):
        if not self.path:return
        self.stop();self.stack.setCurrentWidget(self.office_page);self.office_note.setText(tr('正在载入文档，保留原有页面、图片和图表…'));self.status.setText(tr('Office 原版式预览 · 后台渲染中'));self.office.start(self.path)
    def office_ready(self,path,info):
        try:self.load_pdf(path,info)
        except Exception as e:self.office_error(str(e))
    def office_error(self,reason):
        self.html(tr('<h2>版式预览未能完成</h2><p>')+f.esc(reason)+tr('</p><p><a href="jingpeek:office-retry">重试原版式预览 →</a></p><p><a href="jingpeek:office-text">手动切换文字预览 →</a></p><p><a href="jingpeek:raw-content">查看文件原始内容 →</a></p>'));self.status.setText(tr('请选择重试、文字模式或原始内容查看'))
    def office_text_preview(self):
        if not self.path:return
        self._office_text_once=True
        try:self.preview(self.path)
        finally:self._office_text_once=False
    def error(self,msg):
        if self.path and self.path.is_file():self.base_preview(tr('暂时无法按原格式预览此文件。')+msg)
        else:self.html(tr('<h2>暂时无法预览此文件</h2><p>')+f.esc(msg)+'</p>');self.status.setText(tr('预览提示 · ')+msg[:100])
    def base_preview(self,reason=''):
        self.stop()
        if self.path:self.html(f.universal_html(self.path,reason));self.status.setText(tr('基础预览 · 文件信息 / 文本探测 / 十六进制内容'))
    def play_media(self,path,audio=False):
        self._media_active=True;self.audio_title.setText(self.path.name if self.path else tr('音频预览'));self.media_surface.setCurrentWidget(self.audio_page if audio else self.video);self.stack.setCurrentWidget(self.media_widget);self.media.setSource(QUrl.fromLocalFile(path))
        if self.settings.value('autoplay',True,type=bool):self.media.play()
        self.status.setText(tr('媒体兼容预览 · 已使用内置解码') if self._using_compat else tr('媒体预览 · 系统解码失败时自动切换内置兼容解码'))
    def start_compat(self):
        if not self.path or not self.path.is_file():return
        path=self.path;self.stop();self._using_compat=True;self.stack.setCurrentWidget(self.compat_page);self.compat_bar.setValue(0);self.compat_note.setText(tr('正在检测视频和音频编码…'));self.status.setText(tr('正在准备兼容预览 · 可随时切换文件'));self.compat.start(path)
    def compat_progress(self,percent,message):self.compat_bar.setValue(percent);self.compat_note.setText(message)
    def compat_ready(self,path,audio):
        self._using_compat=True;self.play_media(path,audio)
    def media_error(self):
        if not self._media_active or self.stack.currentWidget()!=self.media_widget:return
        self._media_active=False
        if self._using_compat:self.base_preview(tr('系统播放器仍无法打开兼容媒体，下面提供文件基础查看。'))
        else:
            path=self.path;QTimer.singleShot(0,lambda:self.start_compat() if self.path==path else None)
    def media_position(self,v):
        if not self.seek.isSliderDown():self.seek.setValue(v)
        def clock(n):return f'{n//60000:02d}:{n//1000%60:02d}'
        self.clock.setText(clock(v)+' / '+clock(self.media.duration()))
    def play_pause(self):
        if self.media.playbackState()==QMediaPlayer.PlayingState:self.media.pause()
        else:self.media.play()
    def fit(self):
        if self.stack.currentWidget()==self.image:self.image.fit()
        elif self.stack.currentWidget()==self.pdf:self.pdf.setZoomMode(QPdfView.ZoomMode.FitToWidth)
    def actual(self):
        if self.stack.currentWidget()==self.image:self.image.zoom=1;self.image.draw()
        elif self.stack.currentWidget()==self.pdf:self.pdf.setZoomMode(QPdfView.ZoomMode.Custom);self.pdf.setZoomFactor(1)
    def fullscreen(self):self.showNormal() if self.isFullScreen() else self.showFullScreen()
    def set_pin(self,v):self.setWindowFlag(Qt.WindowStaysOnTopHint,True);self.pin.setChecked(True);self.show()
    def open_file(self):
        if self.path:QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.path)))
    def reveal(self):
        if self.path:
            import subprocess
            subprocess.Popen(['explorer.exe','/select,',str(self.path)])
    def copy_path(self):
        if self.path:QApplication.clipboard().setText(str(self.path));self.status.setText(tr('文件路径已复制'))
    def export_preview(self):
        if self.stack.currentWidget()==self.media_widget:
            QMessageBox.information(self,APP,tr('媒体画面由视频后端绘制，请使用系统截图工具截取。'));return
        path,_=QFileDialog.getSaveFileName(self,tr('保存当前可见预览截图'),tr('景速览-预览.png'),tr('PNG 图片 (*.png)'),options=QFileDialog.DontUseNativeDialog)
        if path:
            ok=self.stack.currentWidget().grab().save(path,'PNG');self.status.setText(tr('预览截图已保存') if ok else tr('保存失败，请检查路径权限'))
    def hash_file(self):
        if not self.path or not self.path.is_file():return
        if self.path.stat().st_size>100*1024*1024:self.hash_text.setText(tr('仅计算 100 MB 以内文件，避免阻塞预览。'));return
        with self.path.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
        self.hash_text.setText('SHA-256\n'+digest);QApplication.clipboard().setText(digest)
    def toggle_info(self):
        if self.compact:self.show_file_info()
        else:self.info.setVisible(not self.info.isVisible())
    def show_file_info(self,preview_only=False):
        d=QDialog(self);d.setWindowTitle(tr('文件信息 · 景速览'));d.resize(560,570);v=QVBoxLayout(d);v.setContentsMargins(28,26,28,24);v.setSpacing(14);v.addWidget(label('FILE DETAILS','eyebrow'));v.addWidget(label(self.path.name if self.path else tr('尚未选择文件'),'section'))
        card=QFrame();card.setObjectName('card');c=QVBoxLayout(card);c.setContentsMargins(18,16,18,16);c.setSpacing(14)
        if self.path:
            try:
                st=self.path.stat();fields=[(tr('文件类型'),self.path.suffix.upper().lstrip('.') or tr('文件夹')),(tr('文件大小'),f.size(st.st_size)),(tr('修改时间'),time.strftime('%Y-%m-%d %H:%M',time.localtime(st.st_mtime))),(tr('所在位置'),str(self.path.parent))]
                for name,value in fields:
                    c.addWidget(label(name,'muted'));val=label(value);val.setTextInteractionFlags(Qt.TextSelectableByMouse);c.addWidget(val)
            except OSError:c.addWidget(label(tr('文件已移动或暂时无法读取。'),'muted'))
        else:c.addWidget(label(tr('先在文件夹中选中文件，再按空格预览。'),'muted'))
        v.addWidget(card);actions=QHBoxLayout();actions.addWidget(button(tr('复制路径'),self.copy_path));actions.addWidget(button(tr('定位文件'),self.reveal));actions.addWidget(button(tr('保存截图'),self.export_preview));v.addLayout(actions)
        digest=label(tr('SHA-256 校验值可用于核对文件完整性（100 MB 内）。'),'muted');digest.setTextInteractionFlags(Qt.TextSelectableByMouse)
        def calculate():
            try:self.hash_file();digest.setText(self.hash_text.text() or tr('请选择可读取的文件。'))
            except OSError as e:digest.setText(str(e))
        v.addWidget(digest);bottom=QHBoxLayout();bottom.addWidget(button(tr('计算并复制 SHA-256'),calculate));bottom.addStretch();bottom.addWidget(button(tr('完成'),d.accept,True));v.addStretch();v.addLayout(bottom)
        if preview_only:return d
        d.exec()
    def set_mode(self,compact):
        if self.compact==compact:return
        self.compact=compact;self.hide();self.info.hide()
        flags=(Qt.Tool|Qt.FramelessWindowHint) if compact else Qt.Window
        flags|=Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags);self.sidebar.setVisible(not compact);self.toolbar.setVisible(not compact);self.close_button.setVisible(compact);self.hints.setVisible(compact)
        self.root.setObjectName('popupRoot' if compact else '');self.root.style().unpolish(self.root);self.root.style().polish(self.root)
        self.center_layout.setContentsMargins(*(14,12,14,10) if compact else (24,20,24,14));self.center_layout.setSpacing(8 if compact else 14)
        self.setMinimumSize(440,300) if compact else self.setMinimumSize(960,620)
        self.resize(600,460) if compact else self.resize(1240,800)
    def show_popup(self,anchor=None,activate_window=True):
        anchor=anchor or QRect(QCursor.pos(),QSize(1,1));screen=QGuiApplication.screenAt(anchor.center()) or QGuiApplication.primaryScreen()
        rect=popup_geometry(anchor,screen.availableGeometry());self.setGeometry(rect)
        if activate_window:self.setAttribute(Qt.WA_ShowWithoutActivating,False);self.restore()
        else:self.setAttribute(Qt.WA_ShowWithoutActivating,True);self.show();self.raise_();show_preview(self.winId(),False)
        if self.stack.currentWidget()==self.image:QTimer.singleShot(0,self.image.fit)
    def popup_menu(self):
        menu=QMenu(self)
        menu.addAction(tr('文件信息 / 复制路径 / 截图'),self.toggle_info)
        menu.addAction(tr('图片 / PDF 适应窗口'),self.fit);menu.addAction(tr('原始比例 1:1'),self.actual);menu.addAction(tr('静态图片旋转 90°'),self.image.rotate)
        menu.addAction(tr('全屏（F11）'),self.fullscreen);menu.addSeparator();menu.addAction(tr('设置'),self.show_settings);menu.addAction(tr('关于与联系作者'),self.show_about)
        menu.addSeparator();menu.addAction(tr('Office 原版式预览（重试）'),self.start_office);menu.addAction(tr('Office 文字预览'),self.office_text_preview);menu.addAction(tr('尝试内置媒体兼容解码'),self.start_compat);menu.addAction(tr('查看文件原始内容'),self.base_preview)
        menu.exec(QCursor.pos())
    def dashboard(self):
        self.set_mode(False);self.home();self.restore()
    def show_about(self):
        self.set_mode(False);self.about();self.restore()
    def from_explorer(self,hwnd=None):
        if self.quitting:return
        from .native import u
        if self._loading_selection:self.hide_preview();return
        self._request+=1;self._selection_hwnd=int(hwnd or u.GetForegroundWindow());self._selection_previous=self.path if self.compact and self.isVisible() else None
        self.original_hwnd=self._selection_hwnd;self._loading_selection=True;self.hook.capture_escape=True;self.hook.capture_hwnd=self.original_hwnd;self.path=None;self.open_button.setEnabled(False);self.set_mode(True)
        self.title.setText(tr('正在读取选中文件'));self.html(tr('<h2>正在读取选中文件…</h2><p>任何类型的本地文件均可查看；复杂内容将在后台准备。</p>'));self.status.setText(tr('空格已响应 · 正在读取资源管理器选中项'))
        self.show_popup(activate_window=False);self.repaint();self.stop();self.background.resolve(self._request,self._selection_hwnd)
        generation=self._request;QTimer.singleShot(5000,lambda:self.selection_timeout(generation))
    def selection_timeout(self,generation):
        if self._loading_selection and generation==self._request:
            self.status.setText(tr('资源管理器响应较慢；可拖入文件或点击选择文件'))
    def selection_ready(self,generation,paths,raw,error):
        if self.quitting or generation!=self._request or not self._loading_selection:return
        self._loading_selection=False;self.hook.capture_escape=False
        if not paths:
            self.html(tr('<h2>未能读取选中文件</h2><p>请先单击文件再按空格，或将文件直接拖入此窗口。压缩包内虚拟条目需先解压；地址栏、搜索栏和重命名输入不触发预览。</p><p>')+f.esc(error)+'</p>');self.restore();return
        if self._selection_previous==paths[0]:self.hide_preview();return
        try:anchor=physical_anchor(raw,QGuiApplication.screens()) if raw else None
        except Exception:anchor=None
        self.load_paths(paths,popup=True,anchor=anchor)
    def restore(self):self.showNormal();self.raise_();self.activateWindow();show_preview(self.winId(),True)
    def hide_preview(self):
        self._request+=1;self._queue_request+=1;self._loading_selection=False;self.hook.capture_escape=False;self.background.cancel_selection()
        if self.compat.proc is not None:self.compat.cancel()
        if self.office.running:self.office.cancel()
        self.media.pause();self.hide()
        if self.original_hwnd:activate(self.original_hwnd)
    def show_recent(self,preview_only=False):
        d=QDialog(self);d.setWindowTitle(tr('最近预览 · 景速览'));d.resize(720,540);v=QVBoxLayout(d);v.setContentsMargins(28,26,28,24);v.setSpacing(14)
        v.addWidget(label('RECENT FILES','eyebrow'));v.addWidget(label(tr('继续上次的一眼'),'brand'));v.addWidget(label(tr('双击文件即可继续预览。最近记录仅保存在这台电脑上。'),'muted'))
        lst=QListWidget();lst.setStyleSheet('QListWidget{background:#ffffff;border:1px solid #e2e9f3;border-radius:12px;}');v.addWidget(lst,1)
        for path in self.recent:
            p=pathlib.Path(path);item=QListWidgetItem(svg_icon('file'),p.name+'\n'+str(p.parent));item.setData(Qt.UserRole,path);item.setToolTip(path);lst.addItem(item)
        if not self.recent:
            item=QListWidgetItem(tr('还没有最近预览记录\n选中文件，按下空格，就从这里开始。'));item.setFlags(Qt.NoItemFlags);lst.addItem(item)
        def pick(item):
            path=item.data(Qt.UserRole)
            if path:d.accept();self.load_paths([pathlib.Path(path)],popup=True)
        lst.itemDoubleClicked.connect(pick)
        def clear():self.recent=[];self.settings.setValue('recent',[]);lst.clear()
        actions=QHBoxLayout();actions.addWidget(button(tr('清空记录'),clear));actions.addStretch();actions.addWidget(button(tr('完成'),d.accept,True));v.addLayout(actions)
        if preview_only:return d
        d.exec()
    def show_settings(self,preview_only=False):
        d=QDialog(self);d.setWindowTitle(tr('偏好设置 · 景速览'));d.resize(760,800);shell=QVBoxLayout(d);shell.setContentsMargins(12,12,12,12);scroll=QScrollArea();scroll.setWidgetResizable(True);body=QWidget();v=QVBoxLayout(body);v.setContentsMargins(18,14,18,14);v.setSpacing(14);scroll.setWidget(body);shell.addWidget(scroll)
        v.addWidget(label('PREFERENCES','eyebrow'));v.addWidget(label(tr('让预览，适合你的习惯'),'brand'));v.addWidget(label(tr('设置即时生效，下次打开时仍会保留。'),'muted'));v.addSpacing(4)
        language_card=QFrame();language_card.setObjectName('card');language_row=QHBoxLayout(language_card);language_row.setContentsMargins(18,16,18,16);language_col=QVBoxLayout();language_col.addWidget(label(tr('界面语言')));language_col.addWidget(label(tr('切换即时生效，并自动记住你的选择。'),'muted'));language_row.addLayout(language_col,1)
        languages=QComboBox();languages.setObjectName('languageSelector');languages.addItem('简体中文','zh_CN');languages.addItem('English','en_US');languages.setMinimumWidth(160);languages.setCurrentIndex(1 if get_language()=='en_US' else 0);languages.currentIndexChanged.connect(lambda index:self.change_language(languages.itemData(index)));language_row.addWidget(languages);v.addWidget(language_card)
        def set_deskgo(on):self.settings.setValue('deskgo_compat',on);self.hook.deskgo_enabled=on
        v.addWidget(setting_card(tr('腾讯桌面整理兼容'),tr('读取所选文件时临时使用复制接口，并恢复剪贴板；不作用于聊天或编辑输入框。'),self.settings.value('deskgo_compat',True,type=bool),set_deskgo))
        v.addWidget(setting_card(tr('自动播放音视频'),tr('打开媒体文件时直接播放，也可在预览框中手动暂停。'),self.settings.value('autoplay',True,type=bool),lambda x:self.settings.setValue('autoplay',x)))
        def clear_cache():
            self.stop()
            old=self.pdfdoc;self.pdfdoc=QPdfDocument(self);self.pdf.setDocument(self.pdfdoc)
            import shiboken6
            shiboken6.delete(old);self.office.cache.clear();self._html_cache.clear()
            if self.office.disk:self.office.disk.clear()
            self.status.setText(tr('预览缓存已清除'))
        v.addWidget(button(tr('清除预览缓存'),clear_cache))
        v.addWidget(setting_card(tr('Office 原版式预览'),tr('保留图片、图表和版式。关闭后使用文字模式；不影响本机 Office/WPS。'),self.settings.value('office_layout',True,type=bool),lambda x:self.settings.setValue('office_layout',x)))
        import winreg
        run=r'Software\Microsoft\Windows\CurrentVersion\Run'
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,run) as key:winreg.QueryValueEx(key,'JingPeek');enabled=True
        except OSError:enabled=False
        def set_startup(on):
            try:
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER,run) as key:
                    if on:
                        cmd='"'+sys.executable+'"'+('' if getattr(sys,'frozen',False) else ' "'+str(pathlib.Path(__file__).parents[1]/'main.py')+'"')+' --background'
                        winreg.SetValueEx(key,'JingPeek',0,winreg.REG_SZ,cmd)
                    else:
                        try:winreg.DeleteValue(key,'JingPeek')
                        except FileNotFoundError:pass
            except OSError as e:QMessageBox.warning(d,APP,str(e))
        v.addWidget(setting_card(tr('登录 Windows 后启动'),tr('启动后静默驻留托盘，选中文件即可按空格预览。'),enabled,set_startup))
        note=QFrame();note.setObjectName('softCard');nl=QVBoxLayout(note);nl.setContentsMargins(16,14,16,14);nl.addWidget(label(tr('小提示'),'section'));nl.addWidget(label(tr('空格只在资源管理器文件区与桌面响应。地址栏、搜索和重命名输入不受影响。\n移动便携版 EXE 后，请重新开关一次登录启动。'),'muted'));v.addWidget(note);v.addStretch()
        actions=QHBoxLayout();footer=label(tr('景速览 1.6.0  ·  浅色界面'),'muted');footer.setWordWrap(False);actions.addWidget(footer);actions.addStretch();actions.addWidget(button(tr('完成'),d.accept,True));shell.addLayout(actions)
        if preview_only:return d
        d.exec()
    def pdf_names(self,info):
        if not info:return []
        hidden=info.get('hidden',[])
        return [name+(tr('（隐藏）') if index<len(hidden) and hidden[index] else '') for index,name in enumerate(info.get('names',[]))]
    def change_language(self,language):
        self.settings.setValue('language',language);self.settings.sync();apply_language(language);self._html_cache.clear()
        if self.path is None:
            if self.nav_buttons[4].isChecked():self.about()
        elif self.stack.currentWidget()==self.pdf:
            index=self.page_selector.currentIndex();names=self.pdf_names(getattr(self,'_pdf_info',None));count=self.pdfdoc.pageCount();self.page_selector.blockSignals(True);self.page_selector.clear();self.page_selector.addItems(names if len(names)==count else [tr('第 {p0} 页 / 共 {p1} 页',p0=n+1,p1=count) for n in range(count)]);self.page_selector.setCurrentIndex(index);self.page_selector.blockSignals(False)
        elif self.stack.currentWidget()==self.browser or self.proc:
            self.preview(self.path)

    def about(self):
        if self.compact:self.set_mode(False)
        self.stop();self.path=None;self.open_button.setEnabled(False);self.nav_buttons[1].setChecked(False);self.nav_buttons[4].setChecked(True);self.title.setText(tr('关于景速览'))
        self.file_badge.setText('JP')
        self.html(tr('<p style="color:#6387c6;font-size:11px"><b>JING PEEK &nbsp; / &nbsp; VERSION 1.6.0</b></p>\n<h1>景速览</h1><h2>轻轻一按，离内容更近。</h2><p>为 Windows 设计的本地快速预览工具，灵感来自 macOS Quick Look。<br>留在文件夹里，用空格查看内容，让文件浏览保持轻快。</p>\n<br><table width="100%" cellspacing="8" cellpadding="18"><tr><td bgcolor="#eef4ff" width="50%"><p style="color:#5d7cae;font-size:11px">微信公众号</p><p><font size="5" color="#244d8c"><b>景同志</b></font></p><p><a href="jingpeek:copy-wechat">复制公众号名称 →</a></p></td><td bgcolor="#fff2f4" width="50%"><p style="color:#ad7884;font-size:11px">小红书</p><p><font size="5" color="#a25168"><b>景同学</b></font></p><p><a href="jingpeek:copy-redbook">复制小红书名称 →</a></p></td></tr></table>\n<p style="color:#8794a7">在对应平台搜索名称，即可找到作者、反馈建议与了解更新。</p><br>\n<table width="100%" cellspacing="8" cellpadding="18"><tr><td bgcolor="#eaf3ff" width="100%"><p style="color:#3973ed;font-size:11px"><b>GITHUB · 开源项目与下载地址</b></p><p><font size="4" color="#203454"><b>github.com/jingpanlong/JingPeek</b></font></p><p><a href="https://github.com/jingpanlong/JingPeek">访问项目主页 / 查看源代码 →</a>\u3000<a href="https://github.com/jingpanlong/JingPeek/releases/latest">下载最新版本 →</a>\u3000<a href="jingpeek:copy-github">复制项目地址 →</a>\u3000<a href="jingpeek:copy-download">复制下载地址 →</a></p><p style="color:#8794a7;font-size:11px">源码以 MIT 许可开源；问题反馈、更新日志与新版本下载均在项目页面。</p></td></tr></table>\n<h2>一个小框，容纳更多内容</h2><p>图片与 GIF、音视频、PDF、代码高亮、Markdown、CSV，以及 ZIP / 7Z / RAR / TAR 压缩包目录。</p>\n<p>Office 默认使用独立引擎生成静态版式预览，保留页面、图片、表格、图表和样式。Word/PPT 可翻页，Excel 可切换工作表；文字提取作为手动选项。特殊字体、动画与复杂对象的边界见使用说明。</p>\n<h2>更广的文件兼容</h2><p>系统缺少媒体解码器时自动使用内置 FFmpeg。任何可读取文件都可以查看基础属性、文本探测或十六进制内容。</p><h2>你的文件，留在本机</h2><p>本地解析，不上传文件。预览完成，按 Esc 或空格收起，继续手头的工作。</p>\n<p style="color:#8794a7;font-size:11px">使用 Python、Qt for Python、Pygments、Python-Markdown 等开源组件。许可与源码随交付文件提供。<br>项目主页：github.com/jingpanlong/JingPeek\u3000 / \u3000下载：github.com/jingpanlong/JingPeek/releases/latest<br>微信公众号：景同志\u3000 /\u3000 小红书：景同学</p>'));self.status.setText(tr('微信公众号：景同志  ·  小红书：景同学'))

    def find(self):
        if self.stack.currentWidget()!=self.browser:return
        from PySide6.QtWidgets import QInputDialog
        text,ok=QInputDialog.getText(self,tr('查找当前内容'),tr('输入关键字'))
        if ok and text:
            if not self.browser.find(text):self.browser.moveCursor(self.browser.textCursor().MoveOperation.Start);self.browser.find(text)
    def link_clicked(self,url):
        if url.scheme()=='jingpeek':
            if url.path()=='office-retry':self.start_office();return
            if url.path()=='office-text':self.office_text_preview();return
            if url.path()=='raw-content':self.base_preview();return
            if url.path()=='media-compat':self.start_compat();return
            name={'copy-wechat':'景同志','copy-redbook':'景同学','copy-github':GITHUB_REPO_URL,'copy-download':GITHUB_RELEASE_URL}.get(url.path())
            if name:QApplication.clipboard().setText(name);self.status.setText(tr('已复制：')+name)
            return
        if url.scheme() in ('https','http'):
            if QMessageBox.question(self,tr('打开链接'),tr('使用默认浏览器打开？\n{p0}', p0=url.toString()))==QMessageBox.Yes:QDesktopServices.openUrl(url)
    def eventFilter(self,obj,e):
        if self.compact and obj in (self.header,self.title):
            if e.type()==QEvent.MouseButtonPress and e.button()==Qt.LeftButton:self.drag_offset=e.globalPosition().toPoint()-self.pos();return True
            if e.type()==QEvent.MouseMove and self.drag_offset is not None:self.move(e.globalPosition().toPoint()-self.drag_offset);return True
            if e.type()==QEvent.MouseButtonRelease:self.drag_offset=None
        if e.type()==QEvent.KeyPress and self.isActiveWindow() and not QApplication.activeModalWidget() and not QApplication.activePopupWidget():
            key=e.key();mods=e.modifiers()
            if key==Qt.Key_Escape:self.hide_preview();return True
            if self._loading_selection and key not in (Qt.Key_Space,):return True
            if key==Qt.Key_Space and not isinstance(QApplication.focusWidget(),QLineEdit):self.hide_preview();return True
            if key in (Qt.Key_Return,Qt.Key_Enter):self.open_file();return True
            if key in (Qt.Key_Left,Qt.Key_Up,Qt.Key_Right,Qt.Key_Down) and not isinstance(QApplication.focusWidget(),QComboBox):self.step(-1 if key in (Qt.Key_Left,Qt.Key_Up) else 1);return True
            if key==Qt.Key_F11:self.fullscreen();return True
            if mods & Qt.ControlModifier and key==Qt.Key_O:self.choose();return True
            if mods & Qt.ControlModifier and key==Qt.Key_F:self.find();return True
        if e.type()==QEvent.Wheel and self.stack.currentWidget()==self.pdf and e.modifiers() & Qt.ControlModifier:
            self.pdf.setZoomMode(QPdfView.ZoomMode.Custom);self.pdf.setZoomFactor(max(.1,min(5,self.pdf.zoomFactor()*(1.1 if e.angleDelta().y()>0 else 1/1.1))));return True
        return super().eventFilter(obj,e)
    def dragEnterEvent(self,e):
        if e.mimeData().hasUrls():e.acceptProposedAction()
    def dropEvent(self,e):self.load_paths([pathlib.Path(u.toLocalFile()) for u in e.mimeData().urls() if u.isLocalFile()],popup=True)
    def closeEvent(self,e):
        if self.quitting:e.accept()
        else:e.ignore();self.hide_preview()
    def quit_app(self):
        if self.quitting:return
        self._request+=1;self._queue_request+=1;self.quitting=True;self.timer.stop();self.hook.stop();self.stop();self.background.close();self.tray.hide()
        # QPdfView can retain a background renderer's file handle after close().
        # Destroy its document before removing the private preview directory.
        self.pdf.setDocument(None)
        import shiboken6
        shiboken6.delete(self.pdfdoc)
        self.settings.sync();self.temp.cleanup();QApplication.instance().quit()

def run():
    import pythoncom
    pythoncom.CoInitialize()
    app=QApplication(sys.argv);app.setQuitOnLastWindowClosed(False);app.setApplicationName(APP);app.setWindowIcon(icon());install_theme(app)
    if '--verify' in sys.argv:
        from .diagnostics import verify
        index=sys.argv.index('--verify');w=Window();verify(w,pathlib.Path(sys.argv[index+1]),pathlib.Path(sys.argv[index+2]));return 0
    # Local socket enforces a single resident instance and forwards file arguments.
    from PySide6.QtNetwork import QLocalServer,QLocalSocket
    sock=QLocalSocket();sock.connectToServer('JingPeek-'+os.environ.get('USERNAME','user'))
    if sock.waitForConnected(250):
        # Explicitly launching the EXE replaces an older resident version. Otherwise
        # a 1.0 process could receive 1.1 commands and still show the old large UI.
        replacing=not sys.argv[1:]
        sock.write(json.dumps(['--quit'] if replacing else sys.argv[1:],ensure_ascii=False).encode());sock.waitForBytesWritten(1000)
        if not replacing:sock.disconnectFromServer();return 0
        if sock.state()!=QLocalSocket.UnconnectedState:sock.waitForDisconnected(4000)
        sock.disconnectFromServer()
    if '--quit' in sys.argv:return 0
    server=QLocalServer();server.removeServer('JingPeek-'+os.environ.get('USERNAME','user'));server.listen('JingPeek-'+os.environ.get('USERNAME','user'))
    w=Window();connections=[]
    import ctypes
    user32=ctypes.windll.user32;user32.SetPropW.argtypes=[ctypes.c_void_p,ctypes.c_wchar_p,ctypes.c_void_p];user32.SetPropW(int(w.winId()),'JingPeekResidentVersion',160)
    def connection():
        client=server.nextPendingConnection();connections.append(client)
        def read():
            try:
                args=json.loads(bytes(client.readAll()).decode());paths=[pathlib.Path(x) for x in args if not x.startswith('--')]
                if '--quit' in args:w.quit_app()
                elif paths:w.load_paths(paths,popup=True)
                elif '--dashboard' in args:w.dashboard()
                else:w.tray.showMessage(APP,tr('已在后台运行。在资源管理器单击文件，按空格预览。'))
            except Exception:w.restore()
            client.disconnectFromServer()
        client.readyRead.connect(read)
        if client.bytesAvailable():read()
    server.newConnection.connect(connection)
    paths=[pathlib.Path(x) for x in sys.argv[1:] if not x.startswith('--')]
    if paths:w.load_paths(paths,popup=True)
    elif '--dashboard' in sys.argv:w.dashboard()
    elif '--background' not in sys.argv:QTimer.singleShot(600,lambda:w.tray.showMessage(APP,tr('已在后台运行。单击资源管理器里的文件，按空格，在文件旁预览；Esc 关闭。')))
    if '--smoke-test' in sys.argv:QTimer.singleShot(1500,w.quit_app)
    app.aboutToQuit.connect(w.hook.stop)
    return app.exec()
