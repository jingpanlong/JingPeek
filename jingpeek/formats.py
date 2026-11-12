from .i18n import tr
"""Bounded, read-only content parsers. Never extract archives or execute documents."""
import html, pathlib, zipfile, tarfile, csv, io, re, mimetypes, time
from xml.etree import ElementTree as ET

IMAGE = set('png jpg jpeg bmp gif webp tif tiff ico svg avif heic heif hif psd dds tga pcx ppm pgm pbm pnm jp2 j2k icns qoi fli flc fits'.split())
MEDIA = set('mp3 wav flac aac m4a ogg opus mp4 mkv avi mov webm wmv m4v wma mpg mpeg mts m2ts ts vob flv 3gp 3g2 aif aiff ape amr ac3 dts alac mp2 m2v mxf rm rmvb caf au mka ogv'.split())
OFFICE = {'docx', 'xlsx', 'pptx', 'odt', 'ods', 'odp','xls','xlsb','xlt','xltx','xltm','dotx','dotm','potx','potm','pps','ppsx','ppsm'}
LEGACY = {'doc', 'ppt', 'rtf', 'docm', 'xlsm', 'pptm'}
ARCHIVE = {'zip', '7z', 'rar', 'tar', 'gz', 'bz2', 'xz', 'tgz'}
TEXT = set('txt log csv tsv json xml yaml yml toml ini cfg conf py js jsx ts tsx java c cpp h hpp cs css html htm sql sh ps1 bat cmd rs go rb php swift kt vue svelte gitignore dockerfile md markdown rst tex'.split())
MAX_FILE = 100 * 1024 * 1024
LIMIT = 2000
def esc(x): return html.escape(str(x))
def size(n):
    for u in ['B','KB','MB','GB','TB']:
        if n < 1024: return f'{n:.1f} {u}'
        n /= 1024
    return f'{n:.1f} PB'
def natural(p): return [int(s) if s.isdigit() else s.casefold() for s in re.split(r'(\d+)', p.name)]
def kind(p):
    if p.is_dir(): return 'folder'
    e=p.suffix.lower().lstrip('.')
    if e=='ts':
        try:
            with p.open('rb') as stream:raw=stream.read(8192)
            if probable_text(raw) is not None:return 'text'
        except OSError:pass
    for group, values in [('image', IMAGE),('media',MEDIA),('office',OFFICE),('legacy',LEGACY),('archive',ARCHIVE),('text',TEXT)]:
        if e in values: return group
    if e=='pdf': return 'pdf'
    try:
        with p.open('rb') as stream:raw=stream.read(8192)
        if raw.startswith(b'%PDF-'):return 'pdf'
        if raw.startswith((b'\x89PNG\r\n\x1a\n',b'\xff\xd8\xff',b'GIF87a',b'GIF89a',b'BM',b'II*\0',b'MM\0*')):return 'image'
        if raw.startswith(b'PK\x03\x04'):return 'archive'
        if raw[4:8]==b'ftyp' and raw[8:12] in (b'heic',b'heix',b'hevc',b'hevx',b'mif1',b'msf1',b'avif',b'avis'):return 'image'
        if raw.startswith(b'RIFF') and raw[8:12]==b'WEBP':return 'image'
        if raw[4:8]==b'ftyp' or raw.startswith((b'\x1aE\xdf\xa3',b'OggS',b'fLaC',b'ID3',b'FLV')) or (raw.startswith(b'RIFF') and raw[8:12] in (b'WAVE',b'AVI ')):return 'media'
        if probable_text(raw) is not None:return 'text'
    except OSError:pass
    return 'unknown'

def probable_text(raw):
    if not raw:return ''
    encodings=['utf-16'] if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else ['utf-8-sig','gb18030']
    if b'\x00' in raw and encodings!=['utf-16']:return None
    for encoding in encodings:
        try:
            value=raw.decode(encoding)
            if sum(c.isprintable() or c in '\r\n\t' for c in value)/max(1,len(value))>=.97:return value
        except UnicodeError:pass
    return None

def universal_html(p,reason=''):
    """Every readable file has a useful, bounded baseline preview, including empty files."""
    p=pathlib.Path(p)
    try:
        st=p.stat()
        with p.open('rb') as stream:raw=stream.read(65536)
    except OSError as e:return tr('<h2>无法读取文件</h2><p>')+esc(e)+tr('</p><p>文件可能已移动，或当前账户没有读取权限。</p>')
    mime=mimetypes.guess_type(p.name)[0] or 'application/octet-stream'
    body='<h2>'+esc(p.name)+'</h2>'
    if reason:body+='<p style="color:#9a753a">'+esc(reason)+'</p>'
    body+=tr('<p>当前格式没有内置专用预览器时，仍可查看文件信息、文本探测和原始字节。</p>')
    body+=table([tr('属性'),tr('内容')],[(tr('文件大小'),size(st.st_size)),(tr('类型推测'),mime),(tr('修改时间'),time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(st.st_mtime))),(tr('完整路径'),str(p))])
    text=probable_text(raw)
    if not raw:body+=tr('<h3>空文件</h3><p>该文件没有数据内容。</p>')
    elif text is not None:body+=tr('<h3>文本探测</h3><p>最多读取前 64 KB；不会执行文件内容。</p><pre>')+esc(text)+'</pre>'
    else:
        rows=[]
        for offset in range(0,min(len(raw),4096),16):
            chunk=raw[offset:offset+16];rows.append(f'{offset:08X}  '+(' '.join(f'{b:02X}' for b in chunk)).ljust(47)+'  '+''.join(chr(b) if 32<=b<127 else '.' for b in chunk))
        body+=tr('<h3>十六进制内容</h3><p>左侧为偏移，中间为原始字节，右侧为可打印字符；最多显示前 4 KB。</p><pre>')+esc('\n'.join(rows))+'</pre>'
    body+=tr('<p><a href="jingpeek:media-compat">尝试内置媒体兼容解码 →</a>\u3000 按 Enter 使用默认程序打开</p>')
    return body
def read_text(p):
    with p.open('rb') as stream: raw=stream.read(2*1024*1024)
    for enc in ('utf-8-sig','utf-16' if raw[:2] in (b'\xff\xfe',b'\xfe\xff') else 'utf-8','gb18030'):
        try: return raw.decode(enc), p.stat().st_size>len(raw)
        except UnicodeError: pass
    return raw.decode('utf-8',errors='replace'), p.stat().st_size>len(raw)
def table(headers, rows):
    return '<table border="0" cellspacing="0" cellpadding="8"><tr>'+''.join('<th>'+esc(x)+'</th>' for x in headers)+'</tr>'+''.join('<tr>'+''.join('<td>'+esc(c)+'</td>' for c in r)+'</tr>' for r in rows)+'</table>'
def archive_rows(p):
    e=p.suffix.lower()
    if e=='.zip' or zipfile.is_zipfile(p):
        with zipfile.ZipFile(p) as z: return [(x.filename, size(x.file_size), tr('目录') if x.is_dir() else tr('文件')) for x in z.infolist()[:LIMIT]]
    if e=='.7z':
        import py7zr
        with py7zr.SevenZipFile(p) as z: return [(x.filename,size(x.uncompressed or 0),tr('目录') if x.is_directory else tr('文件')) for x in z.list()[:LIMIT]]
    if e=='.rar':
        import rarfile
        with rarfile.RarFile(p) as z: return [(x.filename,size(x.file_size),tr('目录') if x.isdir() else tr('文件')) for x in z.infolist()[:LIMIT]]
    with tarfile.open(p) as z:
        rows=[]
        for x in z:
            rows.append((x.name,size(x.size),tr('目录') if x.isdir() else tr('文件')))
            if len(rows)>=LIMIT: break
        return rows
def office_html(p):
    if p.stat().st_size>MAX_FILE: raise ValueError(tr('Office 文件超过 100 MB，请使用默认程序打开。'))
    if p.suffix.lower()=='.xls':
        import xlrd
        w=xlrd.open_workbook(str(p),on_demand=True)
        try:return tr('<p>旧版 Excel 内容预览 · 每表最多 200 行 × 30 列</p>')+''.join('<h2>'+esc(s.name)+'</h2>'+table([],[[s.cell_value(r,c) for c in range(min(s.ncols,30))] for r in range(min(s.nrows,200))]) for s in w.sheets()[:30])
        finally:w.release_resources()
    with zipfile.ZipFile(p) as z:
        entries=z.infolist()
        if len(entries)>20000 or sum(i.file_size for i in entries)>150*1024*1024:
            raise ValueError(tr('Office 解压内容超过安全预览上限（150 MB / 20,000 项）'))
    e=p.suffix.lower()
    if e=='.docx':
        from docx import Document
        d=Document(p)
        out=[tr('<p class="note">Word 内容预览 · 不还原分页、浮动对象和完整排版</p>')]
        out += ['<p>'+esc(x.text)+'</p>' for x in d.paragraphs[:5000]]
        for t in d.tables[:50]: out.append(table([],[[c.text for c in r.cells] for r in t.rows[:200]]))
        return ''.join(out)
    if e=='.xlsx':
        from openpyxl import load_workbook
        w=load_workbook(p, read_only=True, data_only=True, keep_links=False)
        try:
            out=[tr('<p>Excel 内容预览 · 每表最多 200 行 × 30 列，公式显示文件缓存值</p>')]
            for s in w.worksheets[:30]:
                out.append('<h2>'+esc(s.title)+'</h2>')
                out.append(table([], [['' if v is None else str(v)[:2000] for v in row] for row in s.iter_rows(max_row=min(s.max_row or 1,200),max_col=min(s.max_column or 1,30),values_only=True)]))
            return ''.join(out)
        finally: w.close()
    if e=='.pptx':
        from pptx import Presentation
        r=Presentation(p)
        return tr('<p>PowerPoint 文本预览 · 不还原幻灯片布局、图片和动画</p>')+''.join(tr('<h2>幻灯片 ')+str(i+1)+'</h2>'+''.join('<p>'+esc(s.text)+'</p>' for s in slide.shapes if s.has_text_frame) for i,slide in enumerate(list(r.slides)[:300]))
    with zipfile.ZipFile(p) as z:
        info=z.getinfo('content.xml')
        if info.file_size>20*1024*1024: raise ValueError(tr('文档内容过大'))
        root=ET.fromstring(z.read(info))
        texts=[el.text for el in root.iter() if el.tag.endswith(('}p','}h')) and el.text]
        return tr('<p>OpenDocument 文本预览</p>')+''.join('<p>'+esc(x)+'</p>' for x in texts[:5000])
def render_html(p):
    k=kind(p)
    if k=='folder':
        from itertools import islice
        items=list(islice(p.iterdir(),2000))
        return '<h2>'+esc(p.name)+tr('</h2><p>文件夹目录 · 最多 2,000 项</p>')+table([tr('名称'),tr('类型'),tr('大小')],[(x.name,tr('目录') if x.is_dir() else x.suffix,size(x.stat().st_size) if x.is_file() else '—') for x in items])
    if k=='unknown':return universal_html(p)
    if k=='office': return office_html(p)
    if k=='archive':
        if p.suffix.lower() in ('.gz','.bz2','.xz') and not tarfile.is_tarfile(p):
            import gzip,bz2,lzma
            opener={'.gz':gzip.open,'.bz2':bz2.open,'.xz':lzma.open}[p.suffix.lower()]
            with opener(p,'rb') as stream: raw=stream.read(65536)
            return tr('<h2>压缩流内容</h2><p>最多读取解压后的前 64 KB；二进制内容可能无法显示。</p><pre>')+esc(raw.decode('utf-8',errors='replace'))+'</pre>'
        return tr('<h2>压缩包目录</h2><p>只读目录 · 最多显示 2,000 项 · 不解压、不执行</p>')+table([tr('名称'),tr('大小'),tr('类型')],archive_rows(p))
    text,truncated=read_text(p)
    e=p.suffix.lower()
    if e in ('.md','.markdown'):
        import markdown
        # QTextBrowser never executes scripts; strip embedded HTML and remote image references.
        text=re.sub(r'<[^>]*>','',text)
        body=markdown.markdown(text,extensions=['tables','fenced_code','sane_lists'])
    elif e in ('.csv','.tsv'):
        rows=list(csv.reader(io.StringIO(text),delimiter='\t' if e=='.tsv' else ','))[:500]
        body=table([], [r[:40] for r in rows])
    else:
        from pygments import highlight
        from pygments.lexers import get_lexer_for_filename, TextLexer
        from pygments.formatters import HtmlFormatter
        try: lexer=get_lexer_for_filename(p.name)
        except Exception: lexer=TextLexer()
        body=highlight(text,lexer,HtmlFormatter(noclasses=True,style='friendly',linenos='table'))
    return (tr('<p>内容过长，仅显示前 2 MB</p>') if truncated else '')+body
