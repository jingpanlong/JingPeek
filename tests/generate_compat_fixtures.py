"""Generate real codec samples for the compatibility regression tests.

Run tests/integration.py first to generate the base fixtures. Optional XLS fixture:
pip install xlwt==1.3.0. No test files contain user data.
"""
import pathlib,subprocess,sys
sys.path.insert(0,str(pathlib.Path(__file__).parents[1]))
from jingpeek.media_compat import ffmpeg_executable
from PIL import Image
from pillow_heif import register_heif_opener
root=pathlib.Path(sys.argv[1]) if len(sys.argv)>1 else pathlib.Path(__file__).parents[2]/'fixtures'
root.mkdir(parents=True,exist_ok=True)
for name,codec,extra in [('12-video.mp4','libx264',['-pix_fmt','yuv420p']),('13-hevc-10bit.mp4','libx265',['-pix_fmt','yuv420p10le','-x265-params','pools=1:frame-threads=1']),('14-vp9.mp4','libvpx-vp9',['-pix_fmt','yuv420p','-deadline','realtime','-cpu-used','8']),('15-av1.mp4','libaom-av1',['-pix_fmt','yuv420p','-cpu-used','8','-row-mt','1'])]:
    subprocess.run([ffmpeg_executable(),'-hide_banner','-loglevel','error','-y','-f','lavfi','-i','testsrc2=size=320x180:rate=12:duration=2','-c:v',codec,'-threads','2',*extra,str(root/name)],check=True,creationflags=subprocess.CREATE_NO_WINDOW)
register_heif_opener();Image.new('RGB',(160,100),'#81a2ed').save(root/'16-photo.heic')
(root/'17-generic.unknown').write_bytes(bytes(range(256))*30);(root/'18-empty.custom').touch()
if (root/'04-document.pdf').exists():(root/'19-extensionless').write_bytes((root/'04-document.pdf').read_bytes())
(root/'20-unfamiliar-code.custom').write_text('Hello, arbitrary extension!\n',encoding='utf-8')
(root/'21-corrupt.mp4').write_bytes(b'not a valid MP4\x00'+bytes(range(256)))
try:
    import xlwt
    w=xlwt.Workbook();s=w.add_sheet('Legacy');s.write(0,0,'Legacy XLS');s.write(1,0,123);w.save(str(root/'22-legacy.xls'))
except ImportError:pass
print('Compatibility fixtures generated in',root)
