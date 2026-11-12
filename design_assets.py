"""Reproducible native-style application and light installer artwork."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
root=Path(__file__).parent
blue='#3973ed'
logo=Image.new('RGBA',(256,256));d=ImageDraw.Draw(logo);d.rounded_rectangle((8,8,248,248),radius=58,fill=blue);d.ellipse((44,84,212,177),fill='white');d.ellipse((105,106,155,156),fill=blue)
logo.save(root/'icon.ico',sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
image=Image.new('RGB',(328,628));d=ImageDraw.Draw(image)
for y in range(628):
    t=y/627;d.line((0,y,328,y),fill=(round(241-15*t),round(247-12*t),round(255-4*t)))
d.ellipse((120,360,480,720),fill='#e2ecff');d.ellipse((-160,440,180,780),fill='#d7e5ff');d.ellipse((185,440,385,640),outline='#bfd3fc',width=2)
image.paste(logo.resize((76,76)),(30,44),logo.resize((76,76)))
font=lambda size:ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',size)
d.text((30,148),'JingPeek',font=font(42),fill='#203454');d.text((32,214),'JING PEEK',font=font(19),fill='#6385bb')
d.text((30,282),'PRESS SPACE',font=font(25),fill='#2b568f');d.text((30,327),'TAKE A LOOK',font=font(25),fill='#2b568f');d.text((30,550),'Windows Quick Preview',font=font(17),fill='#6d89b2');d.text((30,580),'LOCAL PREVIEW / 1.6.0',font=font(13),fill='#7d99c2')
image.save(root/'installer-large.bmp')
small=Image.new('RGB',(110,110),'white');mark=logo.resize((82,82));small.paste(mark,(14,14),mark);small.save(root/'installer-small.bmp')
print('Generated light application and installer assets')
