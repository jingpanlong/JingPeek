import pathlib,sys,unittest
from unittest.mock import Mock,patch
sys.path.insert(0,str(pathlib.Path(__file__).parents[1]))
from jingpeek import native,deskgo

class DesktopTests(unittest.TestCase):
    def test_desktop_without_focus_is_allowed_but_explorer_input_is_not(self):
        self.assertTrue(native.shell_focus_ready('Progman',''))
        self.assertTrue(native.shell_focus_ready('WorkerW','SysListView32',True))
        self.assertFalse(native.shell_focus_ready('CabinetWClass',''))
        for cls in ('Edit','SearchBox','RichEditD2DPT'):
            self.assertFalse(native.shell_focus_ready('Progman',cls))
        self.assertFalse(native.shell_focus_ready('Progman','SysListView32',menu=True))
    def test_shell_paths_do_not_guess_hidden_extensions(self):
        files=[Mock(IsFileSystem=True,Path='C:/OneDrive/Desktop/same.txt'),Mock(IsFileSystem=True,Path='C:/Users/Public/Desktop/same.docx')]
        class Items:
            Count=2
            def __iter__(self):return iter(files)
        with patch.object(native,'desktop_shell_view',return_value=Mock(SelectedItems=lambda:Items())):
            self.assertEqual(native.desktop_selection(),[pathlib.Path(x.Path) for x in files])
    def test_virtual_desktop_icons_have_an_explicit_message(self):
        class Items:
            Count=1
            def __iter__(self):return iter([Mock(IsFileSystem=False,Path='::{virtual}')])
        with patch.object(native,'desktop_shell_view',return_value=Mock(SelectedItems=lambda:Items())):
            with self.assertRaisesRegex(ValueError,'系统图标'):native.desktop_selection()
    def test_captured_desktop_window_is_used_after_focus_changes(self):
        with patch.object(native.win32gui,'GetAncestor',return_value=42),patch.object(native.win32gui,'GetClassName',return_value='Progman'),patch.object(native,'desktop_selection',return_value=[pathlib.Path('file.txt')]) as selected:
            self.assertEqual(native.selection(42),[pathlib.Path('file.txt')]);selected.assert_called_once()
    def test_deskgo_does_not_accept_other_tencent_apps_or_input(self):
        with patch.object(deskgo,'desktop_process',return_value=False):self.assertFalse(deskgo.ready(1))
        for cls in ('Edit','SearchBox'):
            self.assertFalse(deskgo.ready(1,cls))
        self.assertFalse(deskgo.ready(1,'TXMiniSkin',caret=True));self.assertFalse(deskgo.ready(1,menu=True))
    def test_deskgo_only_accepts_full_desktop_surface(self):
        with patch.object(deskgo,'desktop_process',return_value=True),patch.object(deskgo.win32gui,'GetClassName',return_value='TXMiniSkin'),patch.object(deskgo.win32api,'MonitorFromWindow',return_value=1),patch.object(deskgo.win32api,'GetMonitorInfo',return_value={'Monitor':(0,0,1920,1080)}),patch.object(deskgo.win32gui,'EnumChildWindows'):
            with patch.object(deskgo.win32gui,'GetWindowRect',return_value=(0,0,1920,1080)):self.assertTrue(deskgo.ready(1))
            with patch.object(deskgo.win32gui,'GetWindowRect',return_value=(0,0,600,400)):self.assertFalse(deskgo.ready(1))
    def test_new_clipboard_data_is_never_overwritten(self):
        backup=deskgo.ClipboardBackup()
        with patch.object(deskgo.u,'GetClipboardSequenceNumber',return_value=101),patch.object(deskgo.u,'OpenClipboard') as opened:
            self.assertFalse(backup.restore(100));opened.assert_not_called()
    def test_copy_is_not_sent_if_foreground_changed(self):
        with patch.object(deskgo.u,'GetForegroundWindow',return_value=99),patch.object(deskgo.u,'SendInput') as sent:
            self.assertFalse(deskgo._copy(42));sent.assert_not_called()
    def test_cancelled_preview_does_not_touch_clipboard(self):
        with patch.object(deskgo,'ready',return_value=True),patch.object(deskgo,'ClipboardBackup') as backup:
            self.assertEqual(deskgo.selection(42,cancelled=lambda:True),[]);backup.assert_not_called()
    def test_selection_transaction_releases_lock_on_failure(self):
        lock=Mock();lock.acquire.return_value=True
        with patch.object(deskgo,'_selection_lock',lock),patch.object(deskgo,'_read_selection',side_effect=RuntimeError('failure')):
            with self.assertRaises(RuntimeError):deskgo.selection(42)
        lock.release.assert_called_once()
    def test_shutdown_allows_pending_selection_cleanup(self):
        from jingpeek.background import Background
        worker=Background();thread=Mock();thread.is_alive.side_effect=[True,False];worker.selection_threads=[thread]
        with patch('jingpeek.background.QCoreApplication.processEvents'):worker.close()
        self.assertTrue(worker.closed);self.assertIsNone(worker.selection_generation);thread.join.assert_called_once()
    def test_delegated_file_copy_restores_original_clipboard(self):
        backup=Mock(sequence=10)
        with patch.object(deskgo,'ready',return_value=True),patch.object(deskgo,'ClipboardBackup',return_value=Mock(save=lambda:backup)),patch.object(deskgo,'_copy',return_value=True),patch.object(deskgo,'_open'),patch.object(deskgo.u,'GetAsyncKeyState',return_value=0),patch.object(deskgo.u,'GetClipboardSequenceNumber',side_effect=[10,11,12]),patch.object(deskgo.u,'GetClipboardOwner',return_value=99),patch.object(deskgo.u,'GetForegroundWindow',return_value=42),patch.object(deskgo.u,'IsClipboardFormatAvailable',return_value=True),patch.object(deskgo.u,'CloseClipboard'),patch.object(deskgo.win32process,'GetWindowThreadProcessId',side_effect=lambda hwnd:(1,2 if hwnd==99 else 1)),patch.object(deskgo.win32clipboard,'GetClipboardData',return_value=('C:/Desktop/file.docx',)):
            self.assertEqual(deskgo.selection(42),[pathlib.Path('C:/Desktop/file.docx')])
        backup.restore.assert_called_once_with(12);backup.dispose.assert_called_once()

if __name__=='__main__':unittest.main()
