"""Rich documents used to verify pictures, charts, pagination and sheet structure."""
from pathlib import Path
import sys
from PIL import Image,ImageDraw
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).parents[2]/'fixtures'
root.mkdir(parents=True,exist_ok=True)
image=Image.new('RGB',(800,220),'#315b95');d=ImageDraw.Draw(image);d.rectangle((32,32,240,188),fill='#6fd2ba');d.ellipse((450,25,635,205),fill='#ffca6a');d.line((40,185,735,40),fill='white',width=6);image.save(root/'office-banner.png')
from docx import Document
from docx.shared import Inches,RGBColor,Pt
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
doc=Document();doc.styles['Normal'].font.name='Arial';doc.add_heading('WORD LAYOUT TEST',0);doc.add_paragraph('This page must preserve the banner picture and styled table.');doc.add_picture(str(root/'office-banner.png'),width=Inches(6))
t=doc.add_table(rows=4,cols=3);t.style='Light Shading Accent 1'
for row,values in zip(t.rows,[['ITEM','COUNT','STATE'],['Pictures','1','PRESERVED'],['Table style','3 columns','PRESERVED'],['Pagination','2 pages','PRESERVED']]):
    for cell,value in zip(row.cells,values):cell.text=value
doc.add_page_break();doc.add_heading('SECOND PAGE',0);doc.add_paragraph('Second page content must remain available.');doc.save(root/'23-layout.docx')
from openpyxl import Workbook
from openpyxl.styles import PatternFill,Font,Alignment,Border,Side
from openpyxl.chart import BarChart,Reference
from openpyxl.drawing.image import Image as SheetImage
w=Workbook();s=w.active;s.title='Dashboard';s.merge_cells('A1:F2');s['A1']='EXCEL LAYOUT TEST';s['A1'].fill=PatternFill('solid',fgColor='315B95');s['A1'].font=Font(size=22,bold=True,color='FFFFFF');s['A1'].alignment=Alignment(horizontal='center',vertical='center')
for c in 'ABCDEF':s.column_dimensions[c].width=16
for row in [['Month','Sales'],['Jan',14],['Feb',22],['Mar',31],['Apr',26]]:s.append(row)
chart=BarChart();chart.title='Sales chart';chart.add_data(Reference(s,min_col=2,min_row=3,max_row=7),titles_from_data=True);chart.set_categories(Reference(s,min_col=1,min_row=4,max_row=7));s.add_chart(chart,'H3')
im=SheetImage(str(root/'office-banner.png'));im.width=480;im.height=132;s.add_image(im,'A11');s2=w.create_sheet('Detail');s2.append(['SECOND SHEET','Must be shown with its own page']);s2['A1'].fill=PatternFill('solid',fgColor='70D2BA');s2.column_dimensions['A'].width=30;s2.column_dimensions['B'].width=55
hidden=w.create_sheet('Hidden data');hidden['A1']='HIDDEN SHEET';hidden.sheet_state='hidden';w.save(root/'24-layout.xlsx')
from pptx import Presentation
from pptx.util import Inches as PI,Pt as PP
from pptx.dml.color import RGBColor as PC
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE
r=Presentation();r.slide_width=PI(12.8);r.slide_height=PI(7.2)
for n in range(2):
    slide=r.slides.add_slide(r.slide_layouts[6]);slide.background.fill.solid();slide.background.fill.fore_color.rgb=PC.from_string('17365D' if n==0 else 'EAF2FF')
    box=slide.shapes.add_textbox(PI(.6),PI(.4),PI(11),PI(.8));p=box.text_frame.paragraphs[0];p.text='PPT LAYOUT TEST' if n==0 else 'SECOND SLIDE';p.font.size=PP(32);p.font.bold=True;p.font.color.rgb=PC.from_string('FFFFFF' if n==0 else '17365D')
    slide.shapes.add_picture(str(root/'office-banner.png'),PI(.7),PI(1.6),width=PI(5.2))
    data=CategoryChartData();data.categories=['A','B','C'];data.add_series('Values',[12,23,17]);slide.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED,PI(6.4),PI(1.6),PI(5.5),PI(4),data)
r.save(root/'25-layout.pptx')
print('Generated rich DOCX, XLSX and PPTX fixtures')
