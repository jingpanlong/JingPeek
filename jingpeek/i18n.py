"""Explicit UI messages; document text and filenames never enter the catalog."""
import json, pathlib, os
_language='zh_CN'
_catalog=json.loads((pathlib.Path(__file__).parents[1]/'assets'/'en_US.json').read_text(encoding='utf-8'))
class Message(str):
    def __new__(cls,source='',params=None,parts=None):
        def render(v):return v.render() if isinstance(v,Message) else str(v)
        value=''.join(render(v) for v in parts) if parts is not None else (_catalog.get(source,source) if _language=='en_US' else source)
        if params:value=value.format(**{k:render(v) for k,v in params.items()})
        obj=str.__new__(cls,value);obj.source=source;obj.params=params;obj.parts=parts;return obj
    def render(self):return str(Message(self.source,self.params,self.parts))
    def __add__(self,other):return Message(parts=(self,other))
    def __radd__(self,other):return Message(parts=(other,self))
def tr(source,**params):return Message(source,params)
def get_language():return _language
def set_language(language):
    global _language
    _language=language if language in ('zh_CN','en_US') else 'zh_CN'
def apply_language(language):
    set_language(language)
    from PySide6.QtCore import QLocale,QTranslator
    from PySide6.QtWidgets import QApplication
    app=QApplication.instance()
    if not app:return
    QLocale.setDefault(QLocale(_language))
    old=getattr(app,'_jingpeek_translator',None)
    if old:app.removeTranslator(old)
    if _language=='zh_CN':
        translator=QTranslator(app)
        if translator.load(str(pathlib.Path(__file__).parents[1]/'assets'/'qtbase_zh_CN.qm')):app.installTranslator(translator)
        app._jingpeek_translator=translator
    else:app._jingpeek_translator=None
    from .localized_widgets import refresh
    refresh()
