using System;
using System.IO;
using System.IO.Compression;
using System.Text;
using System.Drawing;
using System.Windows.Forms;
using System.Diagnostics;
using System.Security.Cryptography;
using System.Threading;
using System.Runtime.InteropServices;
using System.Reflection;
[assembly: AssemblyTitle("景速览便携启动器")]
[assembly: AssemblyVersion("1.6.0.0")]
[assembly: System.Runtime.Versioning.TargetFramework(".NETFramework,Version=v4.8", FrameworkDisplayName=".NET Framework 4.8")]

// The archive is appended outside the executable image. It is expanded once to
// a version/hash-specific private directory, rather than on every process spawn.
static class Portable {
    const string PayloadHash="@PAYLOAD_SHA@";
    const string Version="1.6.0";
    const string Magic="JINGPEEK_PAYLOAD_V1";
    static volatile bool cancelled;
    static bool English() {
        string forced=Environment.GetEnvironmentVariable("JINGPEEK_LANG");
        if(!String.IsNullOrEmpty(forced))return forced=="en_US";
        try{using(var key=Microsoft.Win32.Registry.CurrentUser.OpenSubKey(@"Software\JingTongXue\JingPeek")){return key!=null && (string)key.GetValue("language","")=="en_US";}}catch{return false;}
    }
    static readonly bool english=English();
    static string L(string zh,string en){return english?en:zh;}
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] static extern IntPtr FindWindow(string cls,string title);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] static extern IntPtr GetProp(IntPtr hwnd,string name);
    [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr hwnd,out uint pid);

    static string Quote(string value) {
        if(value.Length>0 && value.IndexOfAny(new char[]{' ','\t','\n','\v','"'})<0)return value;
        StringBuilder b=new StringBuilder("\"");int slashes=0;
        foreach(char c in value){if(c=='\\'){slashes++;continue;}if(c=='"'){b.Append('\\',slashes*2+1);b.Append(c);}else{b.Append('\\',slashes);b.Append(c);}slashes=0;}
        b.Append('\\',slashes*2);b.Append('"');return b.ToString();
    }
    static string IOPath(string value) {
        if(value.StartsWith(@"\\?\"))return value;
        string full=Path.GetFullPath(value);
        return full.StartsWith(@"\\")?@"\\?\UNC\"+full.Substring(2):@"\\?\"+full;
    }
    static string Hex(byte[] bytes){return BitConverter.ToString(bytes).Replace("-","").ToLowerInvariant();}
    static bool Ready(string root) {
        try{return File.ReadAllText(IOPath(Path.Combine(root,"ready.txt")))==PayloadHash && File.Exists(IOPath(Path.Combine(root,"JingPeek.exe"))) && File.Exists(IOPath(Path.Combine(root,"_internal","office_runtime","program","soffice.bin")));}
        catch(IOException){return false;}catch(UnauthorizedAccessException){return false;}
    }
    static bool Resident(string executable) {
        try{
            IntPtr hwnd=FindWindow(null,"景速览 · 文件快速预览");
            if(hwnd==IntPtr.Zero)hwnd=FindWindow(null,"JingPeek · Quick File Preview");
            if(hwnd==IntPtr.Zero || GetProp(hwnd,"JingPeekResidentVersion")!=new IntPtr(160))return false;
            uint pid;GetWindowThreadProcessId(hwnd,out pid);
            return String.Equals(Process.GetProcessById((int)pid).MainModule.FileName,executable,StringComparison.OrdinalIgnoreCase);
        }catch{return false;}
    }
    static void Progress(Form form,Label label,ProgressBar bar,string text,int value){
        if(form.IsDisposed)return;
        try{form.BeginInvoke((Action)(()=>{label.Text=text;bar.Value=Math.Max(0,Math.Min(100,value));}));}catch(InvalidOperationException){}
    }
    static void Extract(string self,string root,Form form,Label label,ProgressBar bar) {
        string parent=Path.GetDirectoryName(root), staging=null;bool owns=false;
        using(Mutex mutex=new Mutex(false,"Local\\JingPeek-Prepare-"+PayloadHash.Substring(0,16)+"-"+Environment.UserName)){
            try{
                while(!owns){
                    if(cancelled)throw new OperationCanceledException();
                    try{owns=mutex.WaitOne(100);}catch(AbandonedMutexException){owns=true;}
                    if(!owns)Progress(form,label,bar,L("正在等待另一个景速览完成首次准备…","Waiting for another JingPeek setup\u2026"),0);
                }
                if(Ready(root))return;
                Directory.CreateDirectory(IOPath(parent));
                staging=Path.Combine(parent,"preparing-"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(IOPath(staging));
                using(FileStream file=File.OpenRead(self)){
                    byte[] magic=Encoding.ASCII.GetBytes(Magic);file.Seek(-magic.Length-8,SeekOrigin.End);
                    byte[] count=new byte[8];if(file.Read(count,0,8)!=8)throw new InvalidDataException(L("预览包不完整。","The preview package is incomplete."));
                    long length=BitConverter.ToInt64(count,0);byte[] actual=new byte[magic.Length];file.Read(actual,0,actual.Length);
                    if(Encoding.ASCII.GetString(actual)!=Magic || length<0 || length>file.Length-magic.Length-8)throw new InvalidDataException(L("预览包尾部校验失败。","Invalid preview package footer."));
                    long start=file.Length-magic.Length-8-length;
                    using(WindowStream payload=new WindowStream(file,start,length)){
                        Progress(form,label,bar,L("首次准备：正在校验完整离线预览引擎…","Verifying the offline preview engine\u2026"),0);
                        using(SHA256 sha=SHA256.Create()){if(Hex(sha.ComputeHash(payload))!=PayloadHash)throw new InvalidDataException(L("预览包校验失败，请重新获取完整 EXE。","Package verification failed. Download the complete EXE again."));}
                        payload.Position=0;
                        using(ZipArchive archive=new ZipArchive(payload,ZipArchiveMode.Read,true)){
                            long total=0,done=0;foreach(ZipArchiveEntry entry in archive.Entries)total+=entry.Length;
                            byte[] buffer=new byte[1024*1024];Stopwatch update=Stopwatch.StartNew();
                            string prefix=Path.GetFullPath(staging)+Path.DirectorySeparatorChar;
                            foreach(ZipArchiveEntry entry in archive.Entries){
                                if(cancelled)throw new OperationCanceledException();
                                string target=Path.GetFullPath(Path.Combine(staging,entry.FullName.Replace('/',Path.DirectorySeparatorChar)));
                                if(!target.StartsWith(prefix,StringComparison.OrdinalIgnoreCase) || entry.FullName.Contains(":"))throw new InvalidDataException(L("预览包路径无效。","Invalid package path."));
                                if(entry.Name.Length==0){Directory.CreateDirectory(IOPath(target));continue;}
                                Directory.CreateDirectory(IOPath(Path.GetDirectoryName(target)));
                                using(Stream input=entry.Open())using(FileStream output=new FileStream(IOPath(target),FileMode.CreateNew,FileAccess.Write,FileShare.None)){
                                    int n;while((n=input.Read(buffer,0,buffer.Length))>0){if(cancelled)throw new OperationCanceledException();output.Write(buffer,0,n);done+=n;}
                                }
                                if(update.ElapsedMilliseconds>=100){Progress(form,label,bar,L("首次准备离线预览引擎 · ","Preparing offline preview engine \u00b7 ")+(total==0?100:done*100/total)+"%",total==0?100:(int)(done*100/total));update.Restart();}
                            }
                        }
                    }
                }
                File.WriteAllText(IOPath(Path.Combine(staging,"ready.txt")),PayloadHash);
                // An incomplete previous cache is retained, never recursively
                // removed while an older process might still be using it.
                if(Directory.Exists(IOPath(root)))Directory.Move(IOPath(root),IOPath(root+"-incomplete-"+Guid.NewGuid().ToString("N")));
                Directory.Move(IOPath(staging),IOPath(root));staging=null;
            }finally{
                if(staging!=null && Path.GetDirectoryName(Path.GetFullPath(staging))==Path.GetFullPath(parent)){
                    try{Directory.Delete(IOPath(staging),true);}catch{}
                }
                if(owns)mutex.ReleaseMutex();
            }
        }
    }
    [STAThread] static int Main(string[] args) {
        AppContext.SetSwitch("Switch.System.IO.UseLegacyPathHandling",false);
        AppContext.SetSwitch("Switch.System.IO.BlockLongPaths",false);
        bool probe=Array.IndexOf(args,"--bootstrap-info")>=0,verify=Array.IndexOf(args,"--verify")>=0;
        Stopwatch timer=Stopwatch.StartNew();
        try{
            string self=Assembly.GetExecutingAssembly().Location;
            string data=Environment.GetEnvironmentVariable("JINGPEEK_DATA");
            if(String.IsNullOrEmpty(data))data=Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            string root=Path.Combine(data,"JingPeek","portable",Version+"-"+PayloadHash.Substring(0,12));bool hit=Ready(root);
            if(!hit && Array.IndexOf(args,"--quit")>=0)return 0;
            if(!hit){
                Application.EnableVisualStyles();
                using(Form form=new Form()){
                    form.Text=L("景速览 · 首次准备","JingPeek \u00b7 First-time setup");form.ClientSize=new Size(480,180);form.StartPosition=FormStartPosition.CenterScreen;form.FormBorderStyle=FormBorderStyle.FixedDialog;form.MaximizeBox=false;form.TopMost=true;form.BackColor=Color.FromArgb(247,250,255);form.Font=new Font("Microsoft YaHei UI",10);
                    Label title=new Label(){Text=L("景速览即将就绪","Getting JingPeek ready"),Location=new Point(24,22),AutoSize=true,Font=new Font("Microsoft YaHei UI",16,FontStyle.Bold),ForeColor=Color.FromArgb(35,62,100)};
                    Label label=new Label(){Text=L("只需首次释放，之后启动会直接复用。","One-time extraction. Later launches reuse this engine."),Location=new Point(26,68),Size=new Size(430,28)};
                    ProgressBar bar=new ProgressBar(){Location=new Point(26,110),Size=new Size(428,12)};
                    Label note=new Label(){Text=L("离线处理，不上传文件。关闭此窗口可取消准备。","Offline only. Close this window to cancel."),Location=new Point(26,140),AutoSize=true,ForeColor=Color.SlateGray};
                    form.Controls.AddRange(new Control[]{title,label,bar,note});Exception failure=null;Thread thread=null;
                    form.FormClosing+=(sender,e)=>{cancelled=true;};
                    form.Shown+=(sender,e)=>{
                        thread=new Thread(()=>{try{Extract(self,root,form,label,bar);}catch(Exception error){failure=error;}finally{try{form.BeginInvoke((Action)(()=>form.Close()));}catch{}}});thread.IsBackground=true;thread.Start();
                    };
                    Application.Run(form);if(thread!=null)thread.Join();
                    if(failure is OperationCanceledException)return 0;
                    if(failure!=null)System.Runtime.ExceptionServices.ExceptionDispatchInfo.Capture(failure).Throw();
                    if(!Ready(root))return 0;
                }
            }
            if(probe){Console.WriteLine("{\"cache_hit\":"+(hit?"true":"false")+",\"prepare_ms\":"+timer.ElapsedMilliseconds+",\"cache_dir\":\""+root.Replace("\\","\\\\")+"\"}");return 0;}
            string executable=Path.Combine(root,"JingPeek.exe");
            if(args.Length==0 && Resident(executable))return 0;
            StringBuilder command=new StringBuilder();foreach(string arg in args){if(command.Length>0)command.Append(' ');command.Append(Quote(arg));}
            ProcessStartInfo start=new ProcessStartInfo(executable,command.ToString()){UseShellExecute=false,CreateNoWindow=true,WorkingDirectory=root};
            // Leave the caller's working directory intact for relative file/CLI
            // arguments: absolute normalization is done by the application.
            start.WorkingDirectory=Environment.CurrentDirectory;
            using(Process child=Process.Start(start)){
                if(verify || Array.IndexOf(args,"--smoke-test")>=0 || Array.IndexOf(args,"--quit")>=0){child.WaitForExit();return child.ExitCode;}
            }
            return 0;
        }catch(Exception error){
            if(probe || verify)Console.Error.WriteLine(error.ToString());
            else MessageBox.Show(L("启动准备未完成：","Startup preparation failed: ")+error.Message,"景速览",MessageBoxButtons.OK,MessageBoxIcon.Error);
            return 1;
        }
    }
    sealed class WindowStream:Stream {
        readonly Stream source;readonly long offset,length;long position;
        public WindowStream(Stream source,long offset,long length){this.source=source;this.offset=offset;this.length=length;Position=0;}
        public override bool CanRead{get{return true;}}public override bool CanSeek{get{return true;}}public override bool CanWrite{get{return false;}}
        public override long Length{get{return length;}}public override long Position{get{return position;}set{if(value<0 || value>length)throw new IOException("Invalid payload offset");position=value;source.Position=offset+value;}}
        public override int Read(byte[] buffer,int index,int count){int n=source.Read(buffer,index,(int)Math.Min(count,length-position));position+=n;return n;}
        public override long Seek(long value,SeekOrigin origin){Position=(origin==SeekOrigin.Begin?0:origin==SeekOrigin.Current?position:length)+value;return position;}
        public override void Flush(){}public override void Write(byte[] buffer,int offset,int count){throw new NotSupportedException();}public override void SetLength(long value){throw new NotSupportedException();}
    }
}
