import pathlib,sys,tempfile,time,unittest
from unittest.mock import patch,Mock
sys.path.insert(0,str(pathlib.Path(__file__).parents[1]))
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from jingpeek.app import Window
from jingpeek.native import file_area_focus
from jingpeek.office_cache import OfficeCache

class PreviewSpeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])
        if '--verify' not in sys.argv:sys.argv.append('--verify')
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name);self.window=Window();self.window.tray.hide()
    def tearDown(self):
        self.window.quit_app()
        import shiboken6
        shiboken6.delete(self.window);self.tmp.cleanup()
    def test_frame_is_immediate_before_shell_lookup(self):
        w=self.window
        with patch.object(w.background,'resolve') as resolve,patch('jingpeek.native.u.GetForegroundWindow',return_value=0):
            start=time.perf_counter();w.from_explorer();elapsed=time.perf_counter()-start
            self.assertLess(elapsed,.25);self.assertTrue(w.isVisible());self.assertTrue(w.windowFlags() & Qt.WindowStaysOnTopHint)
            import win32gui
            self.assertTrue(win32gui.IsWindowVisible(int(w.winId())));self.assertFalse(win32gui.IsIconic(int(w.winId())))
            self.assertIn('正在读取选中文件',w.browser.toPlainText());resolve.assert_called_once()
            generation=w._request;w.hide_preview();w.selection_ready(generation,[self.root/'file.xyz'],None,'')
            self.assertFalse(w.isVisible());self.assertIsNone(w.path)
    def test_queue_is_bounded_while_arrow_navigation_keeps_all_files(self):
        w=self.window;w.paths=[self.root/('file'+str(i)+'.bin') for i in range(10000)];w.path=w.paths[-1]
        w.populate_queue(w.path);self.assertLessEqual(w.files.count(),1000)
        with patch.object(w,'preview') as preview:w.step(1);preview.assert_called_once_with(w.paths[0])
    def test_every_extension_reaches_a_visible_preview(self):
        w=self.window
        for suffix in ('.exe','.sys','.bin','.specialformat','','.png','.pdf'):
            path=self.root/('sample'+suffix);path.write_bytes(bytes(range(128))*4)
            w.load_paths([path],popup=True);deadline=time.monotonic()+12
            while w.proc and time.monotonic()<deadline:QTest.qWait(40)
            self.assertIsNone(w.proc);self.assertTrue(w.isVisible());self.assertTrue(w.windowFlags() & Qt.WindowStaysOnTopHint)
            self.assertIs(w.stack.currentWidget(),w.browser);self.assertIn('十六进制',w.browser.toPlainText())
        w.dashboard();self.assertTrue(w.windowFlags() & Qt.WindowStaysOnTopHint)
    def test_windows_11_file_focus_and_text_input_guards(self):
        for cls in ('DirectUIHWND','SysListView32','Microsoft.UI.Input.InputSite.WindowClass','Windows.UI.Core.CoreWindow'):
            self.assertTrue(file_area_focus(cls))
        for cls in ('Edit','RichEditD2DPT','SearchBox','ToolbarWindow32','ComboBox'):
            self.assertFalse(file_area_focus(cls))
        self.assertFalse(file_area_focus('Microsoft.UI.Input.InputSite.WindowClass',True))
    def test_typescript_is_not_misclassified_as_video(self):
        from jingpeek.formats import kind
        path=self.root/'example.ts';path.write_text('export const answer: number = 42;',encoding='utf-8')
        self.assertEqual(kind(path),'text');path.write_bytes(b'\x47\x00\x00\x00'*100);self.assertEqual(kind(path),'media')
    def test_startup_does_not_probe_unavailable_recent_paths(self):
        settings=Mock();settings.value.side_effect=lambda key,*a,**kw:['Z:/offline-history/file.docx'] if key=='recent' else False
        exists=pathlib.Path.exists
        def checked(path):
            if 'offline-history' in str(path):raise AssertionError('Startup accessed an unavailable history path')
            return exists(path)
        other=None
        try:
            with patch('jingpeek.app.QSettings',return_value=settings),patch.object(pathlib.Path,'exists',checked):other=Window()
            self.assertIn('offline-history',other.recent[0])
        finally:
            if other:
                other.quit_app()
                import shiboken6
                shiboken6.delete(other)
    def test_office_cache_survives_instances_and_invalidates_by_file_identity(self):
        cache=OfficeCache(self.root/'cache');pdf=self.root/'result.pdf';pdf.write_bytes(b'%PDF-1.7\nfixture')
        key=('doc.docx',99,100);info={'family':'document','names':[]};cache.put(key,pdf,info)
        second=OfficeCache(cache.directory);self.assertEqual(second.get(key)[1],info);self.assertIsNone(second.get(('doc.docx',99,101)))
        foreign=cache.directory/'unrelated.txt';foreign.write_text('keep');second.clear();self.assertTrue(foreign.exists());self.assertIsNone(second.get(key))

if __name__=='__main__':unittest.main()
