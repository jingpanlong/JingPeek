from .i18n import tr,apply_language,get_language
"""Shared light design system: palette, icons, cards and accessible switches."""
from PySide6.QtCore import Qt,QSize,QByteArray,QRectF,QTranslator
from PySide6.QtGui import QColor,QPalette,QIcon,QPixmap,QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QWidget,QFrame,QLabel,QVBoxLayout,QHBoxLayout,QGridLayout,QPushButton,QScrollArea,QCheckBox

from .localized_widgets import QLabel,QPushButton,QCheckBox

CSS='''
* {font-family:"Microsoft YaHei UI";font-size:13px;color:#24324a;}
QMainWindow,QDialog {background:#f4f7fc;}
QWidget#sidebar {background:#f9fbfe;border-right:1px solid #e4eaf3;}
QWidget#panel {background:#ffffff;border-left:1px solid #e4eaf3;}
QWidget#canvas {background:#ffffff;border:1px solid #e5ebf3;border-radius:12px;}
QWidget#popupRoot {background:#f8faff;border:1px solid #cdd9ec;border-radius:12px;}
QWidget#header {background:transparent;}
QLabel {background:transparent;}
QLabel#brand {font-size:25px;font-weight:700;color:#1c3158;}
QLabel#section {font-size:19px;font-weight:700;color:#203454;}
QLabel#hero {font-size:32px;font-weight:700;color:#1b3055;}
QLabel#muted {color:#7c889d;font-size:12px;}
QLabel#badge {color:#158060;background:#e9f7f1;border-radius:10px;padding:6px 10px;font-size:11px;font-weight:600;}
QLabel#fileBadge {color:#3267df;background:#e9f0ff;border-radius:8px;padding:7px;font-size:10px;font-weight:700;}
QLabel#eyebrow {color:#4b75cb;font-size:11px;font-weight:700;}
QFrame#card {background:#ffffff;border:1px solid #e2e9f3;border-radius:14px;}
QFrame#softCard {background:#f0f5ff;border:1px solid #e0e9fb;border-radius:14px;}
QPushButton {background:#ffffff;border:1px solid #dce4f0;border-radius:8px;padding:8px 12px;font-weight:500;}
QPushButton:hover {background:#f0f5ff;border-color:#a9c1f4;color:#285bca;}
QPushButton:pressed {background:#e3edff;}
QPushButton:focus {border-color:#6592ed;}
QPushButton:checked {background:#eaf1ff;color:#2e63d7;border-color:#adc7ff;}
QPushButton:disabled {color:#acb5c5;background:#f3f5f8;border-color:#e9edf3;}
QPushButton#primary {background:#3973ed;border:1px solid #3973ed;color:#ffffff;font-weight:600;}
QPushButton#primary:hover {background:#2860d6;border-color:#2860d6;}
QPushButton#nav {background:transparent;border:0;text-align:left;padding:11px 12px;color:#66758c;}
QPushButton#nav:hover {background:#edf3ff;color:#3069df;}
QPushButton#nav:checked {background:#e8f0ff;color:#2d65da;font-weight:600;}
QPushButton#closeButton {background:transparent;border:0;color:#8491a6;padding:7px 10px;}
QPushButton#closeButton:hover {background:#fff0f0;color:#d95764;}
QListWidget {background:transparent;border:0;outline:0;}
QListWidget::item {padding:11px 9px;border-radius:8px;margin:2px 0;color:#66738b;}
QListWidget::item:hover {background:#f0f4fa;}
QListWidget::item:selected {background:#e7efff;color:#2d62ce;}
QTextBrowser {background:#ffffff;border:0;padding:22px;selection-background-color:#d7e6ff;selection-color:#183d80;}
QLineEdit,QComboBox,QSpinBox {background:#ffffff;border:1px solid #dce4f0;border-radius:8px;padding:9px;selection-background-color:#d7e6ff;}
QLineEdit:focus {border-color:#6a96ed;}
QSlider::groove:horizontal {height:4px;background:#e3eaf5;border-radius:2px;}
QSlider::sub-page:horizontal {background:#7199f1;border-radius:2px;}
QSlider::handle:horizontal {background:#3973ed;border:2px solid #ffffff;width:12px;height:12px;margin:-6px 0;border-radius:8px;}
QProgressBar {border:1px solid #dce5f2;border-radius:7px;background:#eef3fb;height:18px;text-align:center;color:#31598f;}
QProgressBar::chunk {background:#9ab9fa;border-radius:6px;}
QScrollArea,QStackedWidget {border:0;background:transparent;}
QCheckBox {padding:8px;spacing:10px;}
QCheckBox::indicator {width:18px;height:18px;}
QScrollBar:vertical {background:transparent;width:8px;margin:4px 0;}
QScrollBar::handle:vertical {background:#cbd6e8;min-height:30px;border-radius:4px;}
QScrollBar::handle:vertical:hover {background:#9db4d8;}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {height:0;}
QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical {background:transparent;}
QScrollBar:horizontal {background:transparent;height:8px;}
QScrollBar::handle:horizontal {background:#cbd6e8;min-width:30px;border-radius:4px;}
QScrollBar::add-line:horizontal,QScrollBar::sub-line:horizontal {width:0;}
QToolTip {background:#ffffff;color:#344561;border:1px solid #d9e3f2;padding:6px;}
QMenu {background:#ffffff;border:1px solid #dce5f2;border-radius:10px;padding:6px;}
QMenu::item {padding:9px 24px 9px 14px;border-radius:6px;}
QMenu::item:selected {background:#eaf2ff;color:#2d65da;}
QMenu::separator {height:1px;background:#e8edf5;margin:5px 8px;}
QDialogButtonBox {background:transparent;}
QTreeView,QListView {background:#ffffff;border:1px solid #e2e9f3;border-radius:8px;selection-background-color:#e8f0ff;selection-color:#285bc1;outline:0;}
QTreeView::item {padding:5px 2px;}
QHeaderView::section {background:#f6f8fc;color:#71819a;border:0;border-bottom:1px solid #e2e9f3;padding:8px 5px;}
QSplitter::handle {background:#e4ebf5;width:1px;}
'''

def palette():
    p=QPalette()
    for role,color in [(QPalette.Window,'#f4f7fc'),(QPalette.WindowText,'#24324a'),(QPalette.Base,'#ffffff'),(QPalette.AlternateBase,'#f4f7fc'),(QPalette.Text,'#24324a'),(QPalette.Button,'#ffffff'),(QPalette.ButtonText,'#24324a'),(QPalette.Highlight,'#d7e6ff'),(QPalette.HighlightedText,'#204c9b'),(QPalette.ToolTipBase,'#ffffff'),(QPalette.ToolTipText,'#24324a'),(QPalette.Link,'#3973ed')]:p.setColor(role,QColor(color))
    p.setColor(QPalette.Disabled,QPalette.Text,QColor('#a7b2c4'));return p

def install_theme(app):
    import pathlib
    app.setStyle('Fusion');app.setPalette(palette());app.setStyleSheet(CSS)
    apply_language(get_language())


def svg_icon(name,color='#71829d'):
    paths={
        'home':'<path d="M3 10 12 3l9 7v10H3Z"/><path d="M9 20v-7h6v7"/>',
        'clock':'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
        'settings':'<circle cx="12" cy="12" r="4"/><path d="M12 2v3m0 14v3M2 12h3m14 0h3M5 5l2 2m10 10 2 2M5 19l2-2M17 7l2-2"/>',
        'info':'<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10v1"/>',
        'file':'<path d="M6 3h8l4 4v14H6Z"/><path d="M14 3v5h4M9 12h6M9 16h5"/>',
        'plus':'<path d="M12 5v14M5 12h14"/>',
        'image':'<rect x="3" y="4" width="18" height="16" rx="3"/><circle cx="8" cy="9" r="1"/><path d="m4 17 5-5 4 4 3-3 4 4"/>',
        'code':'<path d="m8 6-6 6 6 6m8-12 6 6-6 6M14 3l-4 18"/>',
        'folder':'<path d="M3 6h7l2 3h9v11H3Z"/>',
        'audio':'<path d="M3 10v4m4-8v12m5-16v20m5-16v12m4-8v4"/>',
        'shield':'<path d="m12 2 8 4v6c0 5-8 10-8 10S4 17 4 12V6Z"/><path d="m8 12 3 3 5-6"/>'}
    xml=f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">{paths.get(name,paths["file"])}</svg>'
    pix=QPixmap(48,48);pix.fill(Qt.transparent);p=QPainter(pix);QSvgRenderer(QByteArray(xml.encode())).render(p);p.end();return QIcon(pix)

class Switch(QCheckBox):
    def __init__(self,text,parent=None):
        super().__init__(parent);self.setAccessibleName(text);self.setFixedSize(46,28);self.setCursor(Qt.PointingHandCursor);self.toggled.connect(self.update)
    def hitButton(self,pos):return self.rect().contains(pos)
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);p.setPen(Qt.NoPen);p.setBrush(QColor('#3973ed' if self.isChecked() else '#d9e2ef'));p.drawRoundedRect(QRectF(1,3,44,22),11,11);p.setBrush(QColor('white'));p.drawEllipse(QRectF(25 if self.isChecked() else 4,6,16,16));p.end()

def text(value,object_name=None):
    w=QLabel(value);w.setWordWrap(True)
    if object_name:w.setObjectName(object_name)
    return w

def setting_card(title,description,checked,changed):
    card=QFrame();card.setObjectName('card');row=QHBoxLayout(card);row.setContentsMargins(18,16,18,16);col=QVBoxLayout();col.setSpacing(6)
    title_label=text(title);title_label.setStyleSheet('font-size:14px;font-weight:600');col.addWidget(title_label);col.addWidget(text(description,'muted'));row.addLayout(col,1)
    switch=Switch(title);switch.setChecked(checked);switch.toggled.connect(changed);row.addWidget(switch);return card

def home_page(owner):
    scroll=QScrollArea();scroll.setWidgetResizable(True);page=QWidget();outer=QVBoxLayout(page);outer.setContentsMargins(30,28,30,28);outer.setSpacing(18)
    topline=QHBoxLayout();eyebrow=text('JING PEEK  /  QUICK PREVIEW','eyebrow');eyebrow.setWordWrap(False);topline.addWidget(eyebrow);topline.addStretch();badge=text(tr('●  本地预览已就绪'),'badge');badge.setWordWrap(False);topline.addWidget(badge);outer.addLayout(topline)
    outer.addSpacing(4);outer.addWidget(text(tr('轻按空格，\n文件内容即刻呈现。'),'hero'));outer.addWidget(text(tr('留在文件夹里，把每一次打开，变成轻松的一眼。\n选中文件后按空格，在文件旁查看图片、文档和更多内容。'),'muted'))
    actions=QHBoxLayout();b=QPushButton(tr('选择文件，开始预览'));b.setObjectName('primary');b.setIcon(svg_icon('plus','#ffffff'));b.clicked.connect(owner.choose);actions.addWidget(b);b=QPushButton(tr('偏好设置'));b.clicked.connect(owner.show_settings);actions.addWidget(b);actions.addStretch();outer.addLayout(actions)
    grid=QGridLayout();grid.setSpacing(12)
    cards=[('image',tr('影像与声音'),tr('图片、动图、音频与视频'),'#547de4'),('file',tr('文档与阅读'),tr('PDF、Office 原版式、Markdown'),'#9874c5'),('code',tr('代码与数据'),tr('代码高亮、文本与 CSV 表格'),'#3b9c8a'),('folder',tr('文件与目录'),tr('压缩包目录、文件夹与元信息'),'#cf9b42')]
    for i,(ico,title,desc,color) in enumerate(cards):
        card=QFrame();card.setObjectName('card');v=QVBoxLayout(card);v.setContentsMargins(18,16,18,16);v.setSpacing(8);row=QHBoxLayout();im=QLabel();im.setPixmap(svg_icon(ico,color).pixmap(26,26));row.addWidget(im);row.addStretch();v.addLayout(row);l=text(title);l.setStyleSheet('font-size:15px;font-weight:600');v.addWidget(l);v.addWidget(text(desc,'muted'));grid.addWidget(card,i//2,i%2)
    outer.addLayout(grid)
    shortcuts=QFrame();shortcuts.setObjectName('softCard');s=QVBoxLayout(shortcuts);s.setContentsMargins(18,15,18,15);s.addWidget(text(tr('键盘，就是你的预览遥控器'),'section'));s.addWidget(text(tr('空格  预览 / 收起        Esc  关闭        Enter  打开文件\n方向键  切换文件        Ctrl + 滚轮  图片缩放        F11  全屏'),'muted'));outer.addWidget(shortcuts);outer.addStretch();scroll.setWidget(page);return scroll
