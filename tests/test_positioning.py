import sys,pathlib,unittest
sys.path.insert(0,str(pathlib.Path(__file__).parents[1]))
from PySide6.QtCore import QRect,QSize
from jingpeek.positioning import popup_geometry

class PlacementTests(unittest.TestCase):
    def test_right_of_selected_file(self):
        row=QRect(24,150,620,28);screen=QRect(0,0,1920,1040)
        popup=popup_geometry(row,screen)
        self.assertGreater(popup.left(),row.right());self.assertEqual(popup.size(),QSize(600,460));self.assertTrue(screen.contains(popup))
    def test_left_at_right_edge(self):
        row=QRect(1700,700,180,25);screen=QRect(0,0,1920,1040)
        popup=popup_geometry(row,screen)
        self.assertLess(popup.right(),row.left());self.assertTrue(screen.contains(popup))
    def test_small_screen(self):
        screen=QRect(0,0,480,320);popup=popup_geometry(QRect(200,300,200,20),screen)
        self.assertTrue(screen.contains(popup))
    def test_negative_monitor_and_taskbar(self):
        screen=QRect(-1920,0,1920,1000);popup=popup_geometry(QRect(-300,980,280,20),screen)
        self.assertTrue(screen.contains(popup));self.assertEqual(popup.bottom(),screen.bottom())
    def test_other_monitor_origin(self):
        screen=QRect(1920,-400,2560,1400);popup=popup_geometry(QRect(4000,-380,450,24),screen)
        self.assertTrue(screen.contains(popup));self.assertGreaterEqual(popup.top(),-400)

if __name__=='__main__':unittest.main()
