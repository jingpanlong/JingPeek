"""Bindings retain message identity, so user content is never translated by matching text."""
import weakref
from PySide6 import QtWidgets as W
from .i18n import Message
_bindings=weakref.WeakKeyDictionary()
def bind(obj,key,value,setter):
    values=_bindings.setdefault(obj,{})
    if isinstance(value,Message):values[key]=(value,setter)
    else:values.pop(key,None)
    setter(obj,str(value))
def refresh():
    import shiboken6
    for obj,values in list(_bindings.items()):
        if shiboken6.isValid(obj):
            for value,setter in list(values.values()):setter(obj,value.render())
class Mixin:
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        if args and isinstance(args[0],Message) and hasattr(self,'setText'):self.setText(args[0])
    def setText(self,value):bind(self,'text',value,lambda obj,s:super(Mixin,obj).setText(s))
    def setToolTip(self,value):bind(self,'tooltip',value,lambda obj,s:super(Mixin,obj).setToolTip(s))
    def setWindowTitle(self,value):bind(self,'title',value,lambda obj,s:super(Mixin,obj).setWindowTitle(s))
    def setAccessibleName(self,value):bind(self,'accessible',value,lambda obj,s:super(Mixin,obj).setAccessibleName(s))
    def setPlaceholderText(self,value):bind(self,'placeholder',value,lambda obj,s:super(Mixin,obj).setPlaceholderText(s))
class QLabel(Mixin,W.QLabel):pass
class QPushButton(Mixin,W.QPushButton):pass
class QCheckBox(Mixin,W.QCheckBox):pass
class QMainWindow(Mixin,W.QMainWindow):pass
class QDialog(Mixin,W.QDialog):pass
class QLineEdit(Mixin,W.QLineEdit):pass
class QSystemTrayIcon(Mixin,W.QSystemTrayIcon):pass
class QMenu(Mixin,W.QMenu):
    def addAction(self,*args):
        action=super().addAction(*args)
        if args and isinstance(args[0],Message):bind(action,'text',args[0],lambda obj,s:obj.setText(s))
        return action

class QComboBox(Mixin,W.QComboBox):
    def addItem(self,text,*args):
        index=self.count();super().addItem(str(text),*args)
        if isinstance(text,Message):bind(self,'item'+str(index),text,lambda obj,s,i=index:obj.setItemText(i,s))
    def addItems(self,texts):
        for text in texts:self.addItem(text)
    def clear(self):
        values=_bindings.get(self,{})
        for key in list(values):
            if key.startswith('item'):values.pop(key)
        super().clear()
