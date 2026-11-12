"""Screen-aware floating preview placement, independent of Windows selection APIs."""
from PySide6.QtCore import QRect,QPoint,QSize

def popup_geometry(anchor,available,preferred=QSize(600,460),gap=12):
    width=min(preferred.width(),available.width())
    height=min(preferred.height(),available.height())
    if anchor.right()+gap+width<=available.right()+1:
        x=anchor.right()+gap
    elif anchor.left()-gap-width>=available.left():
        x=anchor.left()-gap-width
    else:
        x=max(available.left(),min(anchor.right()+gap,available.right()-width+1))
    y=max(available.top(),min(anchor.top()-18,available.bottom()-height+1))
    return QRect(x,y,width,height)

def physical_anchor(rect,screens):
    """Convert UIA's physical pixels into Qt logical coordinates, including mixed-DPI monitors."""
    import win32api
    x,y,width,height=rect
    monitor=win32api.GetMonitorInfo(win32api.MonitorFromPoint((x+width//2,y+height//2),2))
    screen=next((s for s in screens if s.name().casefold()==monitor['Device'].casefold()),None)
    if screen is None:return None
    left,top,_,_=monitor['Monitor'];origin=screen.geometry().topLeft();ratio=screen.devicePixelRatio()
    return QRect(origin.x()+round((x-left)/ratio),origin.y()+round((y-top)/ratio),max(1,round(width/ratio)),max(1,round(height/ratio)))
