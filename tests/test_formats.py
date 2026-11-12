import unittest, pathlib, tempfile, sys, zipfile, tarfile, io, gzip
sys.path.insert(0,str(pathlib.Path(__file__).parents[1]))
from jingpeek import formats as f

class FormatTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def put(self,name,body):p=self.root/name;p.write_text(body,encoding='utf-8');return p
    def test_text_markdown_code(self):
        self.assertIn('标题',f.render_html(self.put('readme.md','# 标题\n\n|A|B|\n|-|-|\n|1|2|')))
        self.assertIn('<span',f.render_html(self.put('a.py','print("中文")')))
        self.assertIn('&lt;script&gt;',f.render_html(self.put('a.txt','<script>bad()</script>')))
    def test_csv_escaping(self):self.assertIn('&lt;bad&gt;',f.render_html(self.put('a.csv','a,b\n<bad>,2')))
    def test_archives(self):
        p=self.root/'test.zip'
        with zipfile.ZipFile(p,'w') as z:z.writestr('../unsafe.txt','never extract');z.writestr('中文.txt','hello')
        self.assertIn('../unsafe.txt',f.render_html(p));self.assertFalse((self.root.parent/'unsafe.txt').exists())
        p=self.root/'a.tar'
        with tarfile.open(p,'w') as z:
            i=tarfile.TarInfo('x.txt');i.size=3;z.addfile(i,io.BytesIO(b'abc'))
        self.assertIn('x.txt',f.render_html(p))
        import py7zr
        p=self.root/'test.7z'
        with py7zr.SevenZipFile(p,'w') as z:z.writestr('hi','x.txt')
        self.assertIn('x.txt',f.render_html(p))
        p=self.root/'text.gz'
        with gzip.open(p,'wb') as z:z.write(b'compressed hello')
        self.assertIn('compressed hello',f.render_html(p))
    def test_office(self):
        from docx import Document
        d=Document();d.add_paragraph('Word 示例');d.add_table(rows=1,cols=1).cell(0,0).text='表格';p=self.root/'a.docx';d.save(p);out=f.render_html(p);self.assertIn('Word 示例',out);self.assertIn('表格',out)
        from openpyxl import Workbook
        w=Workbook();w.active.append(['Excel 示例',123]);p=self.root/'a.xlsx';w.save(p);self.assertIn('Excel 示例',f.render_html(p))
        from pptx import Presentation
        r=Presentation();s=r.slides.add_slide(r.slide_layouts[0]);s.shapes.title.text='PPT 示例';p=self.root/'a.pptx';r.save(p);self.assertIn('PPT 示例',f.render_html(p))
    def test_failures_limits(self):
        p=self.put('broken.zip','bad')
        with self.assertRaises(zipfile.BadZipFile):f.render_html(p)
        p=self.put('big.txt','x'*(2*1024*1024+10));text,trunc=f.read_text(p);self.assertTrue(trunc);self.assertEqual(len(text),2*1024*1024)
        p=self.put('gbk.txt','');p.write_bytes('中文'.encode('gb18030'));self.assertEqual(f.read_text(p)[0],'中文')
        p=self.root/'bomb.docx'
        with zipfile.ZipFile(p,'w',compression=zipfile.ZIP_DEFLATED) as z:z.writestr('huge','0'*(151*1024*1024))
        with self.assertRaisesRegex(ValueError,'安全预览上限'):f.render_html(p)

if __name__=='__main__':unittest.main()
