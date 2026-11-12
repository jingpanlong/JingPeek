from .i18n import tr
"""Scoped Shell selection; DeskGo compatibility restores temporary copy data."""
import ctypes as C, ctypes.wintypes as W, pathlib, threading, os
from PySide6.QtCore import QThread, Signal
import win32gui, win32com.client, pythoncom
u=C.WinDLL('user32',use_last_error=True)
k=C.WinDLL('kernel32',use_last_error=True)
u.GetForegroundWindow.restype=W.HWND
u.CallNextHookEx.restype=C.c_ssize_t
u.CallNextHookEx.argtypes=[W.HHOOK,C.c_int,W.WPARAM,W.LPARAM]
u.SetWindowsHookExW.restype=W.HHOOK
HOOKPROC=C.WINFUNCTYPE(C.c_ssize_t,C.c_int,W.WPARAM,W.LPARAM)
u.SetWindowsHookExW.argtypes=[C.c_int,HOOKPROC,W.HINSTANCE,W.DWORD]
u.UnhookWindowsHookEx.argtypes=[W.HHOOK]
k.GetModuleHandleW.argtypes=[W.LPCWSTR]
k.GetModuleHandleW.restype=W.HMODULE
u.SetTimer.restype=C.c_size_t
u.SetTimer.argtypes=[W.HWND,C.c_size_t,W.UINT,C.c_void_p]
u.KillTimer.argtypes=[W.HWND,C.c_size_t]
u.SendMessageW.argtypes=[W.HWND,W.UINT,W.WPARAM,W.LPARAM]
u.SendMessageW.restype=C.c_ssize_t

class GUITHREADINFO(C.Structure):
    _fields_=[('cbSize',W.DWORD),('flags',W.DWORD),('active',W.HWND),('focus',W.HWND),('capture',W.HWND),('menu',W.HWND),('move',W.HWND),('caret',W.HWND),('rect',W.RECT)]
class KBD(C.Structure):
    _fields_=[('vk',W.DWORD),('scan',W.DWORD),('flags',W.DWORD),('time',W.DWORD),('extra',C.c_size_t)]
def shell_focus_ready(frame,focus,caret=False,menu=False):
    if menu:return False
    if frame in ('Progman','WorkerW') and not focus:return not caret
    return frame in ('CabinetWClass','ExploreWClass','Progman','WorkerW') and file_area_focus(focus,caret)

def desktop_listviews(root=None):
    roots=[root] if root else []
    if not root:
        def collect(hwnd,_):
            if win32gui.GetClassName(hwnd) in ('Progman','WorkerW'):roots.append(hwnd)
        win32gui.EnumWindows(collect,None)
    result=[]
    for hwnd in roots:
        def child(item,_):
            if win32gui.GetClassName(item)=='SysListView32':result.append(item)
        win32gui.EnumChildWindows(hwnd,child,None)
    return result

def desktop_renaming(root):
    for view in desktop_listviews(root):
        editing=[]
        def child(hwnd,_):
            if 'edit' in win32gui.GetClassName(hwnd).casefold() and win32gui.IsWindowVisible(hwnd):editing.append(hwnd)
        win32gui.EnumChildWindows(view,child,None)
        if editing:return True
    return False

def explorer_ready(hwnd=None,allow_deskgo=True):
    hwnd=hwnd or u.GetForegroundWindow()
    try:
        if win32gui.GetClassName(hwnd)=='TXMiniSkin':
            if not allow_deskgo:return False
            from .deskgo import ready
            info=GUITHREADINFO();info.cbSize=C.sizeof(info)
            if not u.GetGUIThreadInfo(0,C.byref(info)):return False
            cls=win32gui.GetClassName(info.focus) if info.focus else ''
            return ready(hwnd,cls,bool(info.caret),bool(info.flags&0x1C))
        root=win32gui.GetAncestor(hwnd,2) or hwnd;frame=win32gui.GetClassName(root)
        if frame not in ('CabinetWClass','ExploreWClass','Progman','WorkerW'):return False
        info=GUITHREADINFO(); info.cbSize=C.sizeof(info)
        if u.GetGUIThreadInfo(0,C.byref(info)):
            cls=win32gui.GetClassName(info.focus) if info.focus else ''
            if not shell_focus_ready(frame,cls,bool(info.caret),bool(info.flags&0x1C)):return False
        if frame in ('Progman','WorkerW') and desktop_renaming(root):return False
        return True
    except Exception: return False

def file_area_focus(cls,caret=False):
    name=cls.casefold()
    if any(x in name for x in ('edit','search','address','toolbar','combobox','button')):return False
    if cls in ('DirectUIHWND','SysListView32','SHELLDLL_DefView','WorkerW','Progman'):return True
    return not caret and cls in ('Microsoft.UI.Input.InputSite.WindowClass','Windows.UI.Input.InputSite.WindowClass','Windows.UI.Core.CoreWindow','XamlExplorerHostIslandWindow')

class SpaceHook(QThread):
    pressed=Signal(object)
    observed=Signal(object)
    dismissed=Signal()
    failed=Signal(str)
    def run(self):
        self.thread_id=k.GetCurrentThreadId()
        self.down=False;self.capture_escape=False
        callback=HOOKPROC
        def proc(code,wp,lp):
            if code>=0:
                data=C.cast(lp,C.POINTER(KBD)).contents
                if data.vk==27 and self.capture_escape and wp==0x100 and u.GetForegroundWindow()==getattr(self,'capture_hwnd',0):
                    self.capture_escape=False;self.dismissed.emit();return 1
                if data.vk==32:
                    if wp in (0x100,0x104):
                        hwnd=u.GetForegroundWindow()
                        eligible=explorer_ready(hwnd,getattr(self,'deskgo_enabled',True))
                        modifiers=any(u.GetAsyncKeyState(x)&0x8000 for x in (16,17,18,91,92))
                        if getattr(self,'debug_desktop',False) and not self.down and win32gui.GetClassName(hwnd) in ('TXMiniSkin','Progman','WorkerW'):
                            self.observed.emit((int(hwnd),eligible,bool(modifiers)))
                        if eligible and not modifiers:
                            if not self.down:self.pressed.emit(int(hwnd))
                            self.down=True
                            return 1
                    elif wp in (0x101,0x105) and self.down:
                        self.down=False; return 1
            return u.CallNextHookEx(None,code,wp,lp)
        self.callback=callback(proc)
        self.hook=u.SetWindowsHookExW(13,self.callback,k.GetModuleHandleW(None),0)
        if not self.hook:
            self.failed.emit(tr('空格监听未启动：')+str(C.get_last_error())); return
        # Windows can silently remove a low-level hook after a scheduling stall.
        # Rearm on this same message-loop thread, without involving Shell/COM.
        timer_id=u.SetTimer(None,0,30000,None)
        msg=W.MSG()
        while u.GetMessageW(C.byref(msg),None,0,0)>0:
            if msg.message==0x113 and msg.wParam==timer_id:
                u.UnhookWindowsHookEx(self.hook);self.hook=u.SetWindowsHookExW(13,self.callback,k.GetModuleHandleW(None),0)
            u.TranslateMessage(C.byref(msg)); u.DispatchMessageW(C.byref(msg))
        u.KillTimer(None,timer_id);u.UnhookWindowsHookEx(self.hook)
    def stop(self):
        if hasattr(self,'thread_id'): u.PostThreadMessageW(self.thread_id,0x12,0,0)
        self.wait(2000)

def desktop_shell_view():
    """Use the desktop's real Shell view, including redirected/merged desktops."""
    from win32com.shell import shell
    windows=win32com.client.Dispatch('Shell.Application').Windows()
    hwnd=win32com.client.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
    browser=windows.FindWindowSW(0,0,8,hwnd,1)
    provider=browser._oleobj_.QueryInterface(pythoncom.IID_IServiceProvider)
    shell_browser=provider.QueryService(shell.SID_STopLevelBrowser,shell.IID_IShellBrowser)
    view=shell_browser.QueryActiveShellView()
    return win32com.client.Dispatch(view.GetItemObject(0,pythoncom.IID_IDispatch))

def desktop_selection():
    try:
        items=desktop_shell_view().SelectedItems();paths=[]
        for item in items:
            if item.IsFileSystem and item.Path:paths.append(pathlib.Path(item.Path))
        if items.Count and not paths:raise ValueError(tr('此电脑、回收站等系统图标不是普通本地文件，请选择桌面上的文件或文件夹。'))
        return paths
    except ValueError:raise
    except Exception:
        import logging
        logging.debug('Desktop Shell view unavailable; trying compatibility reader',exc_info=True)
        return desktop_selection_legacy()

def desktop_selection_legacy():
    # ListView text lives in Explorer's address space; use a small temporary buffer.
    prog=win32gui.FindWindow('Progman',None)
    view=win32gui.FindWindowEx(prog,0,'SHELLDLL_DefView',None)
    if not view:
        found=[]
        def enum(h,_):
            v=win32gui.FindWindowEx(h,0,'SHELLDLL_DefView',None)
            if v: found.append(v)
        win32gui.EnumWindows(enum,None)
        view=found[0] if found else 0
    lv=win32gui.FindWindowEx(view,0,'SysListView32',None) if view else 0
    if not lv: return []
    pid=W.DWORD(); u.GetWindowThreadProcessId(lv,C.byref(pid))
    k.OpenProcess.restype=W.HANDLE
    k.VirtualAllocEx.restype=C.c_void_p
    k.VirtualAllocEx.argtypes=[W.HANDLE,C.c_void_p,C.c_size_t,W.DWORD,W.DWORD]
    k.WriteProcessMemory.argtypes=[W.HANDLE,C.c_void_p,C.c_void_p,C.c_size_t,C.c_void_p]
    k.ReadProcessMemory.argtypes=[W.HANDLE,C.c_void_p,C.c_void_p,C.c_size_t,C.c_void_p]
    k.VirtualFreeEx.argtypes=[W.HANDLE,C.c_void_p,C.c_size_t,W.DWORD]
    k.CloseHandle.argtypes=[W.HANDLE]
    class LVITEM(C.Structure):
        _fields_=[('mask',W.UINT),('item',C.c_int),('sub',C.c_int),('state',W.UINT),('stateMask',W.UINT),('text',C.c_void_p),('max',C.c_int),('image',C.c_int),('param',C.c_ssize_t),('indent',C.c_int),('group',C.c_int),('columns',W.UINT),('puColumns',C.c_void_p),('piColFmt',C.c_void_p),('iGroup',C.c_int)]
    handle=k.OpenProcess(0x38,False,pid.value)
    if not handle: return []
    remote=k.VirtualAllocEx(handle,None,8192,0x3000,4)
    if not remote: k.CloseHandle(handle); return []
    names=[]
    try:
        idx=-1
        for _ in range(1000):
            idx=u.SendMessageW(lv,0x100C,idx,2)
            if idx<0: break
            item=LVITEM(); item.item=idx; item.text=remote+1024; item.max=2048
            k.WriteProcessMemory(handle,remote,C.byref(item),C.sizeof(item),None)
            u.SendMessageW(lv,0x1073,idx,remote)
            buf=C.create_unicode_buffer(2048)
            k.ReadProcessMemory(handle,remote+1024,buf,C.sizeof(buf),None)
            names.append(buf.value)
    finally:
        k.VirtualFreeEx(handle,remote,0,0x8000); k.CloseHandle(handle)
    import win32com.shell.shell as shell, win32com.shell.shellcon as sc
    roots=[pathlib.Path(shell.SHGetFolderPath(0,sc.CSIDL_DESKTOPDIRECTORY,0,0)),pathlib.Path(shell.SHGetFolderPath(0,sc.CSIDL_COMMON_DESKTOPDIRECTORY,0,0))]
    paths=[]
    for name in names:
        for root in roots:
            exact=root/name
            if exact.exists(): paths.append(exact); break
            matches=[p for p in root.glob('*') if p.stem==name] if root.exists() else []
            if len(matches)==1: paths.extend(matches); break
    return paths

def selection(hwnd=None,cancelled=None):
    if cancelled and cancelled():return []
    hwnd=hwnd or u.GetForegroundWindow()
    if win32gui.GetClassName(hwnd)=='TXMiniSkin':
        from .deskgo import selection as deskgo_selection
        return deskgo_selection(hwnd,cancelled=cancelled)
    root=win32gui.GetAncestor(hwnd,2) or hwnd
    if win32gui.GetClassName(root) in ('Progman','WorkerW'):return desktop_selection()
    shell=win32com.client.Dispatch('Shell.Application')
    for window in shell.Windows():
        try:
            if int(window.HWND)==int(hwnd):
                paths=[pathlib.Path(i.Path) for i in window.Document.SelectedItems() if i.Path]
                if paths:return paths
        except Exception: continue
    return desktop_selection() if win32gui.GetClassName(hwnd) in ('Progman','WorkerW') else []

_automation=threading.local()
def selection_anchor(paths):
    """Read the selected Shell item's physical screen bounds. No UI input or focus changes."""
    try:
        from comtypes.client import CreateObject
        from comtypes.gen.UIAutomationClient import CUIAutomation, IUIAutomation
        if not hasattr(_automation,'value'):_automation.value=CreateObject(CUIAutomation,interface=IUIAutomation)
        automation=_automation.value; element=automation.GetFocusedElement()
        names={p.name.casefold() for p in paths}|{p.stem.casefold() for p in paths}
        # Focus is normally the selected file item. Walk up from its name sub-control.
        for _ in range(4):
            if not element:break
            if (element.CurrentName or '').casefold() in names:
                r=element.CurrentBoundingRectangle
                if r.right>r.left and r.bottom>r.top:
                    return (r.left,r.top,r.right-r.left,r.bottom-r.top)
            element=automation.ControlViewWalker.GetParentElement(element)
    except Exception:logging_anchor_failure()
    return None

def logging_anchor_failure():
    import logging
    logging.debug('UI Automation bounds unavailable; positioning by cursor',exc_info=True)

def activate(hwnd):
    try: win32gui.SetForegroundWindow(int(hwnd))
    except Exception: pass

def show_preview(hwnd,active=True):
    """Also handle a launcher/login entry whose STARTUPINFO requested hiding."""
    try:
        win32gui.ShowWindow(int(hwnd),1 if active else 4)
        win32gui.SetWindowPos(int(hwnd),-1,0,0,0,0,0x0001|0x0002|0x0010|0x0040)
        if active:activate(hwnd)
    except Exception:
        import logging
        logging.debug('Native preview visibility update failed',exc_info=True)

def office_convert(source, target):
    """Runs only in an isolated helper process. Macros and link updates disabled."""
    pythoncom.CoInitialize()
    app=None; doc=None
    try:
        ext=pathlib.Path(source).suffix.lower()
        if ext in ('.doc','.docm','.rtf'):
            app=win32com.client.DispatchEx('Word.Application'); app.Visible=False; app.DisplayAlerts=0; app.AutomationSecurity=3
            doc=app.Documents.Open(str(source),ConfirmConversions=False,ReadOnly=True,AddToRecentFiles=False,Visible=False,OpenAndRepair=False)
            doc.ExportAsFixedFormat(str(target),17)
        elif ext in ('.xls','.xlsm'):
            app=win32com.client.DispatchEx('Excel.Application'); app.Visible=False; app.DisplayAlerts=False; app.AutomationSecurity=3
            doc=app.Workbooks.Open(str(source),UpdateLinks=0,ReadOnly=True,IgnoreReadOnlyRecommended=True)
            doc.ExportAsFixedFormat(0,str(target))
        else:
            app=win32com.client.DispatchEx('PowerPoint.Application'); app.AutomationSecurity=3
            doc=app.Presentations.Open(str(source),ReadOnly=True,Untitled=False,WithWindow=False)
            doc.SaveAs(str(target),32)
    finally:
        if doc:
            try:
                if pathlib.Path(source).suffix.lower() in ('.ppt','.pptm'): doc.Close()
                else: doc.Close(False)
            except Exception: pass
        if app:
            try: app.Quit()
            except Exception: pass
        pythoncom.CoUninitialize()
