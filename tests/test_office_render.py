import pathlib,sys,tempfile,unittest
sys.path.insert(0,str(pathlib.Path(__file__).parents[1]))
from PySide6.QtCore import QCoreApplication
from PySide6.QtTest import QTest
from jingpeek.office_render import OfficeRenderer,write_profile

class OfficeRenderTests(unittest.TestCase):
    def setUp(self):
        self.app=QCoreApplication.instance() or QCoreApplication([])
        self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name)
        self.renderer=OfficeRenderer(self.root);self.ready=[];self.failed=[]
        self.renderer.ready.connect(lambda *args:self.ready.append(args));self.renderer.failed.connect(self.failed.append)
    def tearDown(self):self.renderer.cancel();self.tmp.cleanup()
    def test_profile_disables_macros_without_hiding_static_charts(self):
        write_profile(self.root/'profile');text=(self.root/'profile/user/registrymodifications.xcu').read_text()
        self.assertIn('DisableMacrosExecution',text);self.assertIn('MacroSecurityLevel',text)
        self.assertNotIn('DisableActiveContent',text)
    def test_cancel_suppresses_queued_cached_document(self):
        source=self.root/'test.docx';source.write_bytes(b'test');pdf=self.root/'cache.pdf';pdf.write_bytes(b'%PDF-')
        st=source.stat();key=(str(source.resolve()),st.st_size,st.st_mtime_ns)
        self.renderer.cache[key]=(str(pdf),{'family':'document','names':[]})
        self.renderer.start(source);self.renderer.cancel();QTest.qWait(30)
        self.assertEqual(self.ready,[]);self.assertFalse(self.renderer.running)
    def test_missing_document_reports_error_without_process(self):
        self.renderer.start(self.root/'missing.docx');self.assertTrue(self.failed);self.assertFalse(self.renderer.running)

if __name__=='__main__':unittest.main()
