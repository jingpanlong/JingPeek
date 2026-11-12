"""A bounded local cache of completed static Office previews, never originals."""
import pathlib,json,hashlib,shutil,time

class OfficeCache:
    def __init__(self,directory):self.directory=pathlib.Path(directory)
    def stem(self,key):return hashlib.sha256(('layout-v3:'+repr(key)).encode('utf-8')).hexdigest()
    def get(self,key):
        stem=self.stem(key);pdf=self.directory/(stem+'.pdf');meta=self.directory/(stem+'.json')
        try:
            info=json.loads(meta.read_text(encoding='utf-8'))
            with pdf.open('rb') as stream:
                if stream.read(5)!=b'%PDF-':return None
            if info['bytes']!=pdf.stat().st_size:return None
            meta.touch();return str(pdf),info['info']
        except (OSError,ValueError,KeyError):return None
    def put(self,key,path,info):
        try:
            source=pathlib.Path(path)
            if source.stat().st_size>32*1024*1024:return
            self.directory.mkdir(parents=True,exist_ok=True);stem=self.stem(key)
            pdf=self.directory/(stem+'.pdf');meta=self.directory/(stem+'.json')
            shutil.copyfile(source,pdf)
            meta.write_text(json.dumps({'bytes':pdf.stat().st_size,'info':info},ensure_ascii=False),encoding='utf-8')
            entries=sorted(self.directory.glob('*.json'),key=lambda p:p.stat().st_mtime,reverse=True);total=0
            for i,item in enumerate(entries):
                sibling=item.with_suffix('.pdf');size=sibling.stat().st_size if sibling.exists() else 0;total+=size
                if i>=16 or total>256*1024*1024:
                    try:sibling.unlink(missing_ok=True);item.unlink(missing_ok=True)
                    except OSError:pass
        except OSError:pass # A cache write must never prevent previewing a file.
    def clear(self):
        for item in self.directory.glob('*'):
            if item.suffix in ('.pdf','.json') and len(item.stem)==64:
                try:int(item.stem,16);item.unlink()
                except (OSError,ValueError):pass
