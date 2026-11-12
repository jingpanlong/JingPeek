"""Build a single EXE with a native, once-only extraction cache launcher."""
import pathlib,sys,zipfile,hashlib,subprocess,struct,shutil,json,time
def main():
    stage=pathlib.Path(sys.argv[1]).resolve();out=pathlib.Path(sys.argv[2]).resolve();work=pathlib.Path(sys.argv[3]).resolve();work.mkdir(parents=True,exist_ok=True);out.parent.mkdir(parents=True,exist_ok=True)
    payload=work/'payload.zip'
    if '--reuse-payload' not in sys.argv[4:] or not payload.is_file():
        with zipfile.ZipFile(payload,'w',zipfile.ZIP_DEFLATED,compresslevel=1) as z:
            for path in sorted(stage.rglob('*')):
                if path.is_file():z.write(path,path.relative_to(stage).as_posix())
    with payload.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
    root=pathlib.Path(__file__).parent;source=work/'launcher.cs';source.write_text((root/'portable_launcher.cs').read_text(encoding='utf-8').replace('@PAYLOAD_SHA@',digest),encoding='utf-8')
    compiler=pathlib.Path(r'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe');launcher=work/'launcher.exe'
    subprocess.run([str(compiler),'/nologo','/target:winexe','/platform:x64','/out:'+str(launcher),'/win32icon:'+str(root/'icon.ico'),'/reference:System.Windows.Forms.dll','/reference:System.Drawing.dll','/reference:System.IO.Compression.dll','/reference:System.IO.Compression.FileSystem.dll',str(source)],check=True)
    with out.open('wb') as target:
        with launcher.open('rb') as stream:shutil.copyfileobj(stream,target)
        with payload.open('rb') as stream:shutil.copyfileobj(stream,target)
        target.write(struct.pack('<q',payload.stat().st_size));target.write(b'JINGPEEK_PAYLOAD_V1')
    (work/'payload-manifest.json').write_text(json.dumps({'sha256':digest,'bytes':payload.stat().st_size},indent=2),encoding='utf-8');print('Created',out,flush=True)
if __name__=='__main__':main()
