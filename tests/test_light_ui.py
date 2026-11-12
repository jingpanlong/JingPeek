import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).parents[1]))
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from jingpeek.ui import install_theme,Switch,svg_icon

class LightUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([]);install_theme(cls.app)
    def test_palette_has_light_surfaces(self):
        for role in (QPalette.Window,QPalette.Base,QPalette.Button):self.assertGreater(self.app.palette().color(role).lightness(),230)
        self.assertLess(self.app.palette().color(QPalette.Text).lightness(),100)
    def test_switch_retains_checkbox_behavior(self):
        switch=Switch('自动播放');events=[];switch.toggled.connect(events.append)
        switch.show();QTest.mouseClick(switch,Qt.LeftButton);self.assertTrue(switch.isChecked());QTest.mouseClick(switch,Qt.LeftButton);self.assertFalse(switch.isChecked());self.assertEqual(events,[True,False]);switch.close()
    def test_line_icons_are_renderable(self):
        for name in ('home','clock','settings','info','file','audio'):self.assertFalse(svg_icon(name).isNull())

if __name__=='__main__':unittest.main()
