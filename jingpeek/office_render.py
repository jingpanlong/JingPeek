from .i18n import tr,get_language
"""Full static Office rendering, isolated from the user's Office/WPS processes."""
import pathlib,uuid,time,json,subprocess,sys,ctypes
from PySide6.QtCore import QObject,QTimer,Signal
import win32job,win32process,win32event,win32api,win32file,win32con,pywintypes
from .office_cache import OfficeCache

def engine_directory():return pathlib.Path(__file__).parents[1]/'office_runtime'/'program'

def write_profile(directory):
    user=directory/'user';user.mkdir(parents=True,exist_ok=True)
    (user/'registrymodifications.xcu').write_text('''<?xml version="1.0" encoding="UTF-8"?>
<oor:items xmlns:oor="http://openoffice.org/2001/registry">
<item oor:path="/org.openoffice.Office.Common/Security/Scripting"><prop oor:name="MacroSecurityLevel" oor:op="fuse"><value>3</value></prop><prop oor:name="DisableMacrosExecution" oor:op="fuse"><value>true</value></prop></item>
</oor:items>''',encoding='utf-8')

class OfficeRenderer(QObject):
    ready=Signal(str,object)
    failed=Signal(str)
    progress=Signal(object)
    def __init__(self,temp_dir,parent=None,cache_dir=None):
        super().__init__(parent);self.temp=pathlib.Path(temp_dir);self.timer=QTimer(self);self.timer.setInterval(120);self.timer.timeout.connect(self.poll);self.job=None;self.process=None;self.cache={};self.generation=0
        self.disk=OfficeCache(cache_dir) if cache_dir else None
    @property
    def running(self):return self.job is not None
    def cancel(self):
        self.generation+=1;self.timer.stop()
        if self.job:
            try:win32job.TerminateJobObject(self.job,1)
            except pywintypes.error:pass
        if self.process:
            win32event.WaitForSingleObject(self.process,1000);self.process.Close();self.process=None
        if self.job:self.job.Close();self.job=None
    def start(self,path):
        self.cancel();source=pathlib.Path(path).resolve()
        try:
            st=source.stat();self.key=(str(source),st.st_size,st.st_mtime_ns)
            if st.st_size>200*1024*1024:raise ValueError(tr('文档超过 200 MB，暂不进行完整渲染。'))
            cached=self.cache.get(self.key) or (self.disk.get(self.key) if self.disk else None)
            if cached and pathlib.Path(cached[0]).exists():
                generation=self.generation;QTimer.singleShot(0,lambda:self.ready.emit(*cached) if generation==self.generation else None);return
            program=engine_directory();python=program/'python.exe';helper=pathlib.Path(__file__).parents[1]/'assets'/'office_render_helper.py'
            if not python.is_file() or not helper.is_file():raise FileNotFoundError(tr('完整文档引擎不完整，请使用本版完整安装包重新安装。'))
            work=self.temp/('office-'+uuid.uuid4().hex);work.mkdir();profile=work/'profile';write_profile(profile);self.output=work/'preview.pdf';self.log=work/'render.log'
            self.job=win32job.CreateJobObject(None,'JingPeek-Office-'+uuid.uuid4().hex);limits=win32job.QueryInformationJobObject(self.job,win32job.JobObjectExtendedLimitInformation)
            limits['BasicLimitInformation']['LimitFlags']|=win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE|win32job.JOB_OBJECT_LIMIT_JOB_MEMORY|win32job.JOB_OBJECT_LIMIT_DIE_ON_UNHANDLED_EXCEPTION;limits['JobMemoryLimit']=2*1024*1024*1024
            win32job.SetInformationJobObject(self.job,win32job.JobObjectExtendedLimitInformation,limits)
            security=pywintypes.SECURITY_ATTRIBUTES();security.bInheritHandle=True
            log=win32file.CreateFile(str(self.log),win32con.GENERIC_WRITE,win32con.FILE_SHARE_READ|win32con.FILE_SHARE_WRITE,security,win32con.CREATE_ALWAYS,win32con.FILE_ATTRIBUTE_NORMAL,None)
            nul=win32file.CreateFile('NUL',win32con.GENERIC_READ,win32con.FILE_SHARE_READ|win32con.FILE_SHARE_WRITE,security,win32con.OPEN_EXISTING,0,None)
            try:
                startup=win32process.STARTUPINFO();startup.dwFlags=win32con.STARTF_USESTDHANDLES|win32con.STARTF_USESHOWWINDOW;startup.wShowWindow=win32con.SW_HIDE;startup.hStdInput=nul;startup.hStdOutput=log;startup.hStdError=log
                command=subprocess.list2cmdline([str(python),str(helper),str(source),str(self.output),str(profile),str(program),get_language()])
                if getattr(sys,'frozen',False):ctypes.windll.kernel32.SetDllDirectoryW(None)
                try:process,thread,_,_=win32process.CreateProcess(str(python),command,None,None,True,win32con.CREATE_SUSPENDED|win32con.CREATE_NO_WINDOW,None,str(program),startup)
                finally:
                    if getattr(sys,'frozen',False):ctypes.windll.kernel32.SetDllDirectoryW(sys._MEIPASS)
                self.process=process
                try:win32job.AssignProcessToJobObject(self.job,process);win32process.ResumeThread(thread)
                except Exception:win32api.TerminateProcess(process,1);raise
                finally:thread.Close()
            finally:log.Close();nul.Close()
            self.deadline=time.monotonic()+120;self.progress.emit(tr('正在保留页面、图片、图表与原有排版…'));self.timer.start()
        except Exception as e:
            import logging
            logging.exception('Office rendering bootstrap failed');self.cancel();self.failed.emit(str(e))
    def poll(self):
        if not self.job:return
        try:
            if time.monotonic()>self.deadline:raise TimeoutError(tr('文档渲染超过 120 秒，已停止。可重试或手动选择文字模式。'))
            code=win32process.GetExitCodeProcess(self.process)
            if code==win32con.STILL_ACTIVE:return
            self.timer.stop();self.process.Close();self.process=None;win32job.TerminateJobObject(self.job,0);self.job.Close();self.job=None
            if code!=0 or not self.output.exists():
                detail=self.log.read_text(encoding='utf-8',errors='replace')[-1200:]
                raise RuntimeError(tr('无法生成版式预览。文档可能需要密码、已损坏或使用特殊对象。')+('\n'+detail if detail else ''))
            with self.output.open('rb') as stream:
                if stream.read(5)!=b'%PDF-':raise ValueError(tr('渲染结果不是有效的 PDF。'))
            if self.output.stat().st_size>512*1024*1024:raise ValueError(tr('渲染结果超过 512 MB。'))
            info=json.loads(self.output.with_suffix('.json').read_text(encoding='utf-8'));self.cache[self.key]=(str(self.output),info)
            if self.disk:self.disk.put(self.key,self.output,info)
            while len(self.cache)>8:self.cache.pop(next(iter(self.cache)))
            self.ready.emit(str(self.output),info)
        except Exception as e:self.cancel();self.failed.emit(str(e))
