import pathlib,sys,tempfile,unittest
sys.path.insert(0,str(pathlib.Path(__file__).parents[1]))
from PySide6.QtCore import QCoreApplication
from PySide6.QtTest import QTest
from jingpeek.media_compat import MediaCompat

class MediaCancelTests(unittest.TestCase):
    def setUp(self):
        self.app=QCoreApplication.instance() or QCoreApplication([]);self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name);self.source=self.root/'input.mp4';self.source.write_bytes(b'not media\x00');self.decoder=MediaCompat(self.root);self.ready=[];self.failed=[];self.decoder.ready.connect(lambda *args:self.ready.append(args));self.decoder.failed.connect(self.failed.append)
    def tearDown(self):self.decoder.cancel();self.tmp.cleanup()
    def test_active_probe_is_terminated(self):
        self.decoder.start(self.source);self.assertIsNotNone(self.decoder.proc);self.decoder.cancel();QTest.qWait(150);self.assertIsNone(self.decoder.proc);self.assertEqual(self.ready,[]);self.assertEqual(self.failed,[])
    def test_cancel_suppresses_cached_ready_callback(self):
        output=self.root/'cached.mp4';output.write_bytes(b'test');st=self.source.stat();key=(str(self.source.resolve()),st.st_size,st.st_mtime_ns);self.decoder.cache[key]=(str(output),False)
        self.decoder.start(self.source);self.decoder.cancel();QTest.qWait(80);self.assertEqual(self.ready,[])

if __name__=='__main__':unittest.main()
