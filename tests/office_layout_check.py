"""Verify real Office-to-PDF pages, pictures, chart colors and unchanged sources."""
import sys,pathlib,time,hashlib,json,re
sys.path.insert(0,str(pathlib.Path(__file__).parents[1]))
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from PySide6.QtCore import QSize
from PySide6.QtPdf import QPdfDocument
from jingpeek.office_render import OfficeRenderer

def main():
    root=pathlib.Path(sys.argv[1]).resolve();out=pathlib.Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True);app=QApplication([]);r=OfficeRenderer(out);results=[]
    for name,minimum,family in [('23-layout.docx',2,'document'),('24-layout.xlsx',3,'spreadsheet'),('25-layout.pptx',2,'presentation')]:
        source=root/name;before=hashlib.sha256(source.read_bytes()).hexdigest();ok=[];errors=[]
        def ready(path,info):ok.append((path,info))
        def failed(reason):errors.append(reason)
        r.ready.connect(ready);r.failed.connect(failed);r.start(source);deadline=time.monotonic()+125
        while not ok and not errors and time.monotonic()<deadline:QTest.qWait(80)
        try:
            assert ok,errors
            path,info=ok[0];pdf=QPdfDocument();assert pdf.load(path)==QPdfDocument.Error.None_;assert pdf.pageCount()>=minimum,(name,pdf.pageCount());assert info['family']==family
            if family=='spreadsheet':assert pdf.pageCount()==3,('expected one page per sheet',pdf.pageCount())
            text=''.join(pdf.getAllText(i).text() for i in range(pdf.pageCount()))
            if family=='spreadsheet':assert 'Sales chart' in text,'Excel chart was replaced by an OLE placeholder'
            if family=='presentation':assert 'Values' in text,'PowerPoint chart was replaced by an OLE placeholder'
            page=pdf.pagePointSize(0);scale=min(1200/page.width(),1000/page.height());image=pdf.render(0,QSize(round(page.width()*scale),round(page.height()*scale)));assert not image.isNull();image.save(str(out/(name+'.png')))
            image_objects=len(re.findall(rb'/Subtype\s*/Image',pathlib.Path(path).read_bytes()));assert image_objects>=1,'embedded banner image missing'
            colors=set()
            for y in range(0,image.height(),8):
                for x in range(0,image.width(),8):
                    c=image.pixelColor(x,y)
                    if c.alpha()>150 and max(c.red(),c.green(),c.blue())-min(c.red(),c.green(),c.blue())>45:colors.add((c.red()//32,c.green()//32,c.blue()//32))
            assert len(colors)>4,'pictures / colored charts were not rendered'
            assert hashlib.sha256(source.read_bytes()).hexdigest()==before,'original changed'
            results.append({'file':name,'passed':True,'pages':pdf.pageCount(),'family':family,'image_objects':image_objects,'color_buckets':len(colors),'sheets':info['names']});pdf.close()
        except Exception as e:results.append({'file':name,'passed':False,'error':str(e)})
        r.ready.disconnect(ready);r.failed.disconnect(failed)
    r.cancel();(out/'report.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(results,ensure_ascii=False))

if __name__=='__main__':main()
