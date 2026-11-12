import pathlib,sys,tempfile,unittest
sys.path.insert(0,str(pathlib.Path(__file__).parents[1]))
from jingpeek import formats as f
from jingpeek.media_compat import probe_info,ffmpeg_executable

class UniversalTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def test_any_binary_gets_hex_and_metadata(self):
        p=self.root/'arbitrary.custom';p.write_bytes(bytes(range(256))*40)
        self.assertEqual(f.kind(p),'unknown');out=f.universal_html(p)
        for token in ['十六进制','00000000','00 01 02 03','application/octet-stream','arbitrary.custom']:self.assertIn(token,out)
        self.assertNotIn('00001000  ',out)
    def test_unknown_text_and_escaped_markup(self):
        p=self.root/'notes.weird';p.write_text('hello <script>alert(1)</script>',encoding='utf-8');self.assertEqual(f.kind(p),'text');self.assertIn('&lt;script&gt;',f.universal_html(p))
    def test_empty_and_missing(self):
        p=self.root/'empty.any';p.touch();self.assertIn('空文件',f.universal_html(p));self.assertIn('无法读取',f.universal_html(self.root/'absent'))
    def test_signature_without_extension(self):
        samples=[(b'%PDF-1.7','pdf'),(b'\x89PNG\r\n\x1a\n','image'),(b'\0\0\0\x18ftypisom\0\0\0\0','media'),(b'\0\0\0\x18ftypheic\0\0\0\0','image')]
        for index,(raw,kind) in enumerate(samples):
            p=self.root/str(index);p.write_bytes(raw);self.assertEqual(f.kind(p),kind)
    def test_probe_audio_video_and_bundled_binary(self):
        video=probe_info('Duration: 00:01:02.50\nStream #0:0: Video: hevc\nStream #0:1: Audio: aac')
        self.assertEqual(video,{'video':True,'audio':True,'duration':62.5});self.assertFalse(probe_info('Stream #0:0: Audio: opus')['video'])
        with self.assertRaises(ValueError):probe_info('Invalid data found when processing input')
        self.assertTrue(pathlib.Path(ffmpeg_executable()).is_file())

if __name__=='__main__':unittest.main()
