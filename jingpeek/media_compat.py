from .i18n import tr
"""Isolated, cancellable FFmpeg compatibility decoding; no system codec installation."""
import pathlib,re,uuid
from PySide6.QtCore import QObject,QProcess,QTimer,Signal

def ffmpeg_executable():
    # Resolve the bundled binary directly: never use PATH or a user environment override.
    import imageio_ffmpeg
    files=list((pathlib.Path(imageio_ffmpeg.__file__).parent/'binaries').glob('ffmpeg*.exe'))
    if not files:raise FileNotFoundError(tr('内置 FFmpeg 未找到，请重新解压或安装完整版本。'))
    return str(files[0])

def probe_info(log):
    video=bool(re.search(r'Stream .*Video:',log));audio=bool(re.search(r'Stream .*Audio:',log))
    match=re.search(r'Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)',log)
    duration=sum(float(v)*f for v,f in zip(match.groups(),(3600,60,1))) if match else 0
    if not video and not audio:raise ValueError(tr('未识别到可解码的音视频流；文件可能损坏、受保护，或并非媒体文件。'))
    return {'video':video,'audio':audio,'duration':duration}

class MediaCompat(QObject):
    ready=Signal(str,bool)
    failed=Signal(str)
    progress=Signal(int,object)
    def __init__(self,temp_dir,parent=None):
        super().__init__(parent);self.temp_dir=pathlib.Path(temp_dir);self.proc=None;self.timer=QTimer(self);self.timer.setSingleShot(True);self.timer.timeout.connect(self.timed_out);self.output=None;self.cache={};self.generation=0
    def cancel(self):
        self.generation+=1;self.timer.stop();p=self.proc;self.proc=None
        if p:
            p.kill();p.waitForFinished(1000);p.deleteLater()
        if self.output:
            try:self.output.unlink(missing_ok=True)
            except OSError:pass
            self.output=None
    def start(self,path):
        self.cancel();self.path=pathlib.Path(path).resolve()
        try:
            stat=self.path.stat();self.key=(str(self.path),stat.st_size,stat.st_mtime_ns)
            cached=self.cache.get(self.key)
            if cached and pathlib.Path(cached[0]).exists():
                generation=self.generation;QTimer.singleShot(0,lambda:self.ready.emit(*cached) if generation==self.generation else None);return
            self.exe=ffmpeg_executable()
            self.progress.emit(0,tr('正在检测媒体编码…'))
            self.launch(['-hide_banner','-nostdin','-protocol_whitelist','file,pipe','-probesize','32000000','-analyzeduration','5000000','-i',str(self.path)],'probe',15000)
        except Exception as e:self.failed.emit(str(e))
    def launch(self,args,stage,timeout):
        p=QProcess(self);self.proc=p;self.stage=stage;self.stderr='';self.stdout=''
        p.readyReadStandardError.connect(lambda:self.read_error(p));p.readyReadStandardOutput.connect(lambda:self.read_progress(p));p.finished.connect(lambda code,status:self.finished(p,code));p.errorOccurred.connect(lambda error:self.process_error(p,error))
        p.setProgram(self.exe);p.setArguments(args);p.start();self.timer.start(timeout)
    def read_error(self,p):
        if p is self.proc:self.stderr=(self.stderr+bytes(p.readAllStandardError()).decode('utf-8',errors='replace'))[-65536:]
    def read_progress(self,p):
        if p is not self.proc:return
        self.stdout=(self.stdout+bytes(p.readAllStandardOutput()).decode('utf-8',errors='replace'))[-16384:]
        seconds=re.findall(r'out_time_us=(\d+)',self.stdout)
        if seconds:
            current=int(seconds[-1])/1_000_000;total=self.info['duration'];percent=min(99,int(current/total*100)) if total else 0
            self.progress.emit(percent,tr('正在离线兼容解码，首次准备需要一些时间…'))
    def finished(self,p,code):
        if p is not self.proc:return
        self.read_error(p);self.read_progress(p);stage=self.stage;self.proc=None;self.timer.stop();p.deleteLater()
        try:
            if stage=='probe':
                self.info=probe_info(self.stderr);self.output=self.temp_dir/(uuid.uuid4().hex+('.mp4' if self.info['video'] else '.wav'))
                args=['-hide_banner','-nostdin','-y','-protocol_whitelist','file,pipe','-i',str(self.path),'-map_metadata','-1','-sn','-dn','-threads','2','-filter_threads','2']
                if self.info['video']:
                    args+=['-map','0:v:0','-map','0:a:0?','-vf',"scale=w='min(1280,trunc(iw/2)*2)':h=-2",'-c:v','libx264','-preset','ultrafast','-crf','24','-pix_fmt','yuv420p','-c:a','aac','-b:a','160k','-ac','2','-ar','48000','-movflags','+faststart']
                else:args+=['-map','0:a:0','-vn','-c:a','pcm_s16le','-ac','2','-ar','48000']
                args+=['-fs','1073741824','-progress','pipe:1','-nostats',str(self.output)]
                self.progress.emit(0,tr('正在准备系统可播放的兼容版本…'));self.launch(args,'convert',180000)
            elif code==0 and self.output and self.output.exists() and 0<self.output.stat().st_size<1070000000:
                output=str(self.output);audio=not self.info['video'];self.output=None;self.cache[self.key]=(output,audio)
                while len(self.cache)>3 or sum(pathlib.Path(v[0]).stat().st_size for v in self.cache.values() if pathlib.Path(v[0]).exists())>1610612736:
                    oldest=next(iter(self.cache));old_path=self.cache.pop(oldest)[0]
                    try:pathlib.Path(old_path).unlink(missing_ok=True)
                    except OSError:pass
                self.progress.emit(100,tr('兼容预览已就绪'));self.ready.emit(output,audio)
            else:raise ValueError(tr('兼容解码未完成。文件可能损坏、受 DRM 保护，或超过 1 GB 临时文件限制。'))
        except Exception as e:self.cancel();self.failed.emit(str(e))
    def process_error(self,p,error):
        if p is self.proc and error==QProcess.FailedToStart:self.cancel();self.failed.emit(tr('内置解码程序未能启动，请检查软件文件是否完整。'))
    def timed_out(self):
        self.cancel();self.failed.emit(tr('兼容解码超时，已停止。仍可查看文件信息和原始内容。'))
