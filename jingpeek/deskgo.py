from .i18n import tr
"""Read selection from Tencent DeskGo's custom desktop, with clipboard recovery.

DeskGo exposes neither a Shell selection nor accessible file items. Its copy
command supplies CF_HDROP. Only its verified desktop process is targeted; edit
controls and other Tencent applications are never treated as a desktop.
"""
import ctypes as C,ctypes.wintypes as W,pathlib,time,threading
import win32gui,win32process,win32api,win32clipboard,pythoncom

u=C.WinDLL('user32',use_last_error=True);k=C.WinDLL('kernel32',use_last_error=True)
ole=C.WinDLL('ole32');gdi=C.WinDLL('gdi32')
u.GetForegroundWindow.restype=W.HWND
u.GetClipboardOwner.restype=W.HWND
u.GetClipboardData.argtypes=[W.UINT];u.GetClipboardData.restype=W.HANDLE
u.SetClipboardData.argtypes=[W.UINT,W.HANDLE];u.SetClipboardData.restype=W.HANDLE
u.OpenClipboard.argtypes=[W.HWND]
ole.OleDuplicateData.argtypes=[W.HANDLE,W.UINT,W.UINT];ole.OleDuplicateData.restype=W.HANDLE
ole.OleInitialize.argtypes=[C.c_void_p];ole.OleInitialize.restype=W.LONG
ole.OleUninitialize.argtypes=[];ole.OleUninitialize.restype=None
k.GlobalSize.argtypes=[W.HANDLE];k.GlobalSize.restype=C.c_size_t
k.GlobalFree.argtypes=[W.HANDLE];k.GlobalFree.restype=W.HANDLE
k.QueryFullProcessImageNameW.argtypes=[W.HANDLE,W.DWORD,W.LPWSTR,C.POINTER(W.DWORD)]
k.QueryFullProcessImageNameW.restype=W.BOOL
for name in ('DeleteObject','DeleteEnhMetaFile','DeleteMetaFile'):
    getattr(gdi,name).argtypes=[W.HANDLE]

def desktop_process(hwnd):
    try:
        pid=win32process.GetWindowThreadProcessId(hwnd)[1]
        handle=win32api.OpenProcess(0x1000,False,pid)
        try:
            buffer=C.create_unicode_buffer(32768);size=W.DWORD(len(buffer))
            if not k.QueryFullProcessImageNameW(int(handle),0,buffer,C.byref(size)):return False
            path=buffer.value.replace('/','\\').casefold()
        finally:handle.Close()
        return '\\tencent\\deskgo\\' in path and pathlib.PureWindowsPath(path).name=='desktopmgr64.exe'
    except Exception:return False

def ready(hwnd,focus_class='',caret=False,menu=False):
    if menu or caret or any(x in focus_class.casefold() for x in ('edit','search','combobox')):return False
    try:
        if win32gui.GetClassName(hwnd)!='TXMiniSkin' or not desktop_process(hwnd):return False
        rect=win32gui.GetWindowRect(hwnd)
        monitor=win32api.GetMonitorInfo(win32api.MonitorFromWindow(hwnd,2))['Monitor']
        if rect[2]-rect[0]<(monitor[2]-monitor[0])*.75 or rect[3]-rect[1]<(monitor[3]-monitor[1])*.75:return False
        editing=[]
        def child(h,_):
            if 'edit' in win32gui.GetClassName(h).casefold() and win32gui.IsWindowVisible(h):editing.append(h)
        win32gui.EnumChildWindows(hwnd,child,None)
        return not editing
    except Exception:return False

def _open():
    for _ in range(12):
        if u.OpenClipboard(None):return
        time.sleep(.015)
    raise RuntimeError(tr('剪贴板正在使用，请稍后再次按空格。'))

def _format_name(fmt):
    if fmt<0xC000:return ''
    try:return win32clipboard.GetClipboardFormatName(fmt)
    except Exception:return ''

def _free(fmt,handle):
    if not handle:return
    if fmt in (2,9,0x82) or 0x300<=fmt<=0x3FF:gdi.DeleteObject(handle)
    elif fmt in (14,0x8E):gdi.DeleteEnhMetaFile(handle)
    elif fmt in (3,0x83):
        class Meta(C.Structure):_fields_=[('mode',C.c_int),('x',C.c_int),('y',C.c_int),('meta',W.HANDLE)]
        k.GlobalLock.argtypes=[W.HANDLE];k.GlobalLock.restype=C.c_void_p
        k.GlobalUnlock.argtypes=[W.HANDLE]
        pointer=k.GlobalLock(handle)
        if pointer:gdi.DeleteMetaFile(C.cast(pointer,C.POINTER(Meta)).contents.meta);k.GlobalUnlock(handle)
        k.GlobalFree(handle)
    else:k.GlobalFree(handle)

class ClipboardBackup:
    def __init__(self):self.handles={};self.original=None;self.sequence=0;self.metadata=set();self.ole_initialized=False
    def save(self):
        if ole.OleInitialize(None)<0:raise RuntimeError(tr('无法安全访问剪贴板，已取消腾讯桌面兼容读取。'))
        self.ole_initialized=True
        # Pin the original OLE data object before replacing the clipboard. Native
        # handle copies provide a fallback if the previous owner exits meanwhile.
        try:self.original=pythoncom.OleGetClipboard()
        except pythoncom.com_error:pass
        try:_open()
        except Exception:self.dispose();raise
        try:
            total=0;fmt=0
            while True:
                fmt=u.EnumClipboardFormats(fmt)
                if not fmt:break
                name=_format_name(fmt)
                if name.casefold() in ('dataobject','ole private data'):
                    self.metadata.add(fmt);continue
                if fmt==0x80:raise RuntimeError(tr('当前剪贴板包含专用显示数据，已取消兼容读取以保留原内容。'))
                source=u.GetClipboardData(fmt)
                if not source:raise RuntimeError(tr('无法完整保存当前剪贴板，已取消兼容读取。'))
                total+=int(k.GlobalSize(source))
                if total>128*1024*1024:raise RuntimeError(tr('当前剪贴板内容较大，已取消兼容读取以保留原内容。'))
                clone=ole.OleDuplicateData(source,fmt,2)
                if not clone:raise RuntimeError(tr('无法完整保存当前剪贴板，已取消兼容读取。'))
                self.handles[fmt]=clone
            self.sequence=u.GetClipboardSequenceNumber()
        except Exception:self.dispose();raise
        finally:u.CloseClipboard()
        if self.metadata and self.original is None:
            self.dispose();raise RuntimeError(tr('无法完整保存当前剪贴板对象，已取消兼容读取。'))
        return self
    def restore(self,expected):
        if u.GetClipboardSequenceNumber()!=expected:return False
        if self.metadata and self.original is not None:
            owner=None
            try:
                pythoncom.OleSetClipboard(self.original);owner=u.GetClipboardOwner();pythoncom.OleFlushClipboard()
                if u.GetClipboardOwner()!=owner:return False
                if all(u.IsClipboardFormatAvailable(f) for f in self.handles):return True
            except pythoncom.com_error:
                if owner is None and u.GetClipboardSequenceNumber()!=expected:return False
                if owner is not None and u.GetClipboardOwner()!=owner:return False
            # The sequence now belongs to our attempted restoration.
            expected=u.GetClipboardSequenceNumber()
        window=win32gui.CreateWindowEx(0,'Static','JingPeek clipboard recovery',0,0,0,0,0,-3,0,0,None)
        try:
            for attempt in range(20):
                if u.OpenClipboard(window):break
                time.sleep(.025)
            else:raise RuntimeError(tr('剪贴板被其他程序占用，暂时无法恢复。'))
            try:
                if u.GetClipboardSequenceNumber()!=expected:return False
                u.EmptyClipboard()
                for fmt,handle in list(self.handles.items()):
                    if not u.SetClipboardData(fmt,handle):raise RuntimeError(tr('剪贴板恢复未完成。'))
                    del self.handles[fmt] # Ownership transferred to Windows.
                return True
            finally:u.CloseClipboard()
        finally:win32gui.DestroyWindow(window)
    def dispose(self):
        for fmt,handle in self.handles.items():_free(fmt,handle)
        self.handles.clear();self.original=None
        if self.ole_initialized:ole.OleUninitialize();self.ole_initialized=False

class Key(C.Structure):_fields_=[('vk',W.WORD),('scan',W.WORD),('flags',W.DWORD),('time',W.DWORD),('extra',C.c_size_t)]
class Mouse(C.Structure):_fields_=[('x',W.LONG),('y',W.LONG),('data',W.DWORD),('flags',W.DWORD),('time',W.DWORD),('extra',C.c_size_t)]
class InputData(C.Union):_fields_=[('key',Key),('mouse',Mouse)]
class Input(C.Structure):_fields_=[('kind',W.DWORD),('data',InputData)]
u.SendInput.argtypes=[W.UINT,C.POINTER(Input),C.c_int];u.SendInput.restype=W.UINT
last_read={}
_selection_lock=threading.Lock()

def _copy(hwnd):
    if u.GetForegroundWindow()!=hwnd or any(u.GetAsyncKeyState(v)&0x8000 for v in (16,17,18,91,92)):return False
    keys=(Input*4)()
    for entry,(vk,flags) in zip(keys,((17,0),(67,0),(67,2),(17,2))):entry.kind=1;entry.data.key=Key(vk,0,flags,0,0)
    return u.SendInput(4,keys,C.sizeof(Input))==4

def selection(hwnd,cancelled=None):
    for _ in range(40):
        if cancelled and cancelled():return []
        if _selection_lock.acquire(timeout=.05):break
    else:return []
    try:return _read_selection(hwnd,cancelled)
    finally:_selection_lock.release()

def _read_selection(hwnd,cancelled=None):
    global last_read
    last_read={'eligible':ready(hwnd),'copied':False,'paths':0,'restored':None}
    if not last_read['eligible'] or (cancelled and cancelled()):return []
    deadline=time.monotonic()+.6
    while u.GetAsyncKeyState(32)&0x8000 and time.monotonic()<deadline:time.sleep(.01)
    if u.GetAsyncKeyState(32)&0x8000:return []
    saved=ClipboardBackup().save();copied=None
    try:
        if (cancelled and cancelled()) or not ready(hwnd) or u.GetClipboardSequenceNumber()!=saved.sequence or not _copy(hwnd):return []
        last_read['copied']=True
        deadline=time.monotonic()+1.2
        while time.monotonic()<deadline:
            sequence=u.GetClipboardSequenceNumber()
            if sequence!=saved.sequence:
                owner=u.GetClipboardOwner()
                same_owner=bool(owner) and win32process.GetWindowThreadProcessId(owner)[1]==win32process.GetWindowThreadProcessId(hwnd)[1]
                files=bool(u.IsClipboardFormatAvailable(15))
                # DeskGo can delegate file copying to Shell/OLE, whose clipboard
                # owner is Explorer or null. Accept that file drop only while
                # the original desktop still has focus; ignore unrelated data.
                if not same_owner and not (files and u.GetForegroundWindow()==hwnd):return []
                copied=sequence
                if files:
                    _open()
                    try:
                        paths=[pathlib.Path(p) for p in win32clipboard.GetClipboardData(15)]
                        # CF_HDROP can be delay-rendered by Shell. Reading it may
                        # advance the sequence even without another user copy.
                        # Capture that final version while the clipboard is locked.
                        copied=u.GetClipboardSequenceNumber()
                    finally:u.CloseClipboard()
                    last_read['paths']=len(paths);return paths
            time.sleep(.015)
        return []
    finally:
        try:
            if copied is not None:last_read['restored']=saved.restore(copied)
        finally:saved.dispose()
