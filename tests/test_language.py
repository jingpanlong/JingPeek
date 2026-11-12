import ast,json,pathlib,sys,unittest,tempfile,multiprocessing
sys.path.insert(0,str(pathlib.Path(__file__).parents[1]))
from jingpeek.i18n import tr,set_language,get_language,apply_language,Message
from jingpeek.localized_widgets import QLabel,QPushButton,QMenu,QComboBox
from PySide6.QtWidgets import QApplication
class LanguageTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
 def tearDown(self):apply_language('zh_CN')
 def test_catalog_covers_all_explicit_messages(self):
  root=pathlib.Path(__file__).parents[1];catalog=json.loads((root/'assets/en_US.json').read_text(encoding='utf-8'));missing=[]
  for p in (root/'jingpeek').glob('*.py'):
   for n in ast.walk(ast.parse(p.read_text(encoding='utf-8-sig'))):
    if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='tr' and n.args and isinstance(n.args[0],ast.Constant):
     if n.args[0].value not in catalog:missing.append((p.name,n.lineno,n.args[0].value))
  self.assertEqual(missing,[])
 def test_dynamic_message_round_trip(self):
  message=tr('第 {p0} 页 / 共 {p1} 页',p0=2,p1=12);self.assertEqual(str(message),'第 2 页 / 共 12 页')
  set_language('en_US');self.assertEqual(message.render(),'Page 2 of 12');set_language('zh_CN');self.assertEqual(message.render(),str(message))
 def test_only_bound_messages_change(self):
  generated=QLabel(tr('设置'));filename=QLabel('设置');filename.setToolTip('设置');apply_language('en_US')
  self.assertEqual(generated.text(),'Settings');self.assertEqual(filename.text(),'设置');self.assertEqual(filename.toolTip(),'设置')
  generated.setText('用户自写设置');apply_language('zh_CN');self.assertEqual(generated.text(),'用户自写设置')
 def test_nested_values_and_concatenation(self):
  message='File '+tr('文件夹')+' 设置'
  apply_language('en_US');self.assertEqual(message.render(),'File Folder 设置')
 def test_menu_button_and_page_labels_switch(self):
  button=QPushButton(tr('完成'));menu=QMenu();action=menu.addAction(tr('设置'));combo=QComboBox();combo.addItems([tr('第 {p0} 页 / 共 {p1} 页',p0=1,p1=2),'设置'])
  apply_language('en_US');self.assertEqual(button.text(),'Done');self.assertEqual(action.text(),'Settings');self.assertEqual(combo.itemText(0),'Page 1 of 2');self.assertEqual(combo.itemText(1),'设置')
  combo.clear();combo.addItem('完成');apply_language('zh_CN');self.assertEqual(combo.itemText(0),'完成')
 def test_progress_signals_keep_live_translation_binding(self):
  from jingpeek.office_render import OfficeRenderer
  from jingpeek.media_compat import MediaCompat
  with tempfile.TemporaryDirectory() as tmp:
   office=OfficeRenderer(tmp);media=MediaCompat(tmp);office_label=QLabel();media_label=QLabel()
   office.progress.connect(office_label.setText);media.progress.connect(lambda percent,message:media_label.setText(message))
   office.progress.emit(tr('正在保留页面、图片、图表与原有排版…'));media.progress.emit(0,tr('正在检测媒体编码…'))
   apply_language('en_US');self.assertEqual(office_label.text(),'Preserving pages, images, charts and original layout…');self.assertEqual(media_label.text(),'Detecting media codecs…');office.cancel();media.cancel()
 def test_parser_worker_receives_language_and_preserves_user_text(self):
  from jingpeek.parse_worker import worker
  with tempfile.TemporaryDirectory() as tmp:
   p=pathlib.Path(tmp)/'设置.doc';p.write_text('用户内容：设置',encoding='utf-8');parent,child=multiprocessing.Pipe(False)
   process=multiprocessing.Process(target=worker,args=(str(p),tmp,child,'en_US'));process.start();child.close();self.assertTrue(parent.poll(15));status,result=parent.recv();process.join(5);self.assertEqual(process.exitcode,0);self.assertEqual(status,'ok');self.assertIn('Text detection',result[1]);self.assertIn('用户内容：设置',result[1]);parent.close();process.close()
if __name__=='__main__':unittest.main()

