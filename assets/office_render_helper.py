"""Executed by the bundled LibreOffice Python, inside an isolated Windows job."""
import sys,pathlib,subprocess,time,uuid,json,ctypes
# Inherited by soffice: failures are reported to the preview, never through WER UI.
ctypes.windll.kernel32.SetErrorMode(0x0001|0x0002|0x8000)
sys.stdout.reconfigure(encoding='utf-8',errors='replace');sys.stderr.reconfigure(encoding='utf-8',errors='replace')
import uno
from com.sun.star.beans import PropertyValue
from com.sun.star.document.MacroExecMode import NEVER_EXECUTE
from com.sun.star.document.UpdateDocMode import NO_UPDATE

def prop(name,value):
    p=PropertyValue();p.Name=name;p.Value=value;return p

def main():
    english=len(sys.argv)>5 and sys.argv[5]=='en_US'
    def message(zh,en):return en if english else zh
    source,output,profile,program=map(pathlib.Path,sys.argv[1:5]);pipe='JingPeek_'+uuid.uuid4().hex
    args=[str(program/'soffice.com'),'-env:UserInstallation='+profile.resolve().as_uri(),'--headless','--nologo','--nodefault','--norestore','--nofirststartwizard','--accept=pipe,name='+pipe+';urp;StarOffice.ServiceManager']
    child=subprocess.Popen(args,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
    desktop=None;doc=None
    try:
        context=uno.getComponentContext();resolver=context.ServiceManager.createInstanceWithContext('com.sun.star.bridge.UnoUrlResolver',context)
        deadline=time.monotonic()+45
        while True:
            try:remote=resolver.resolve('uno:pipe,name='+pipe+';urp;StarOffice.ComponentContext');break
            except Exception:
                if child.poll() is not None or time.monotonic()>deadline:raise RuntimeError(message('文档引擎启动失败或超时。','The document engine failed to start or timed out.'))
                time.sleep(.1)
        desktop=remote.ServiceManager.createInstanceWithContext('com.sun.star.frame.Desktop',remote)
        options=(prop('Hidden',True),prop('ReadOnly',True),prop('MacroExecutionMode',NEVER_EXECUTE),prop('UpdateDocMode',NO_UPDATE))
        doc=desktop.loadComponentFromURL(source.resolve().as_uri(),'_blank',0,options)
        if not doc:raise RuntimeError(message('文档无法读取，可能需要密码或格式已损坏。','Cannot read the document. It may require a password or be damaged.'))
        info={'family':'document','names':[],'hidden':[]};filters=[prop('UseLosslessCompression',True),prop('ReduceImageResolution',False),prop('ExportBookmarks',True)]
        if doc.supportsService('com.sun.star.sheet.SpreadsheetDocument'):
            name='calc_pdf_Export';info['family']='spreadsheet';sheets=doc.getSheets()
            for sheet_name in sheets.getElementNames():
                sheet=sheets.getByName(sheet_name);info['names'].append(sheet_name);info['hidden'].append(not sheet.IsVisible)
            # Whole-sheet PDF: preserves column widths, cell formatting and drawings,
            # without cropping content to a pre-existing print area.
            filters.append(prop('SinglePageSheets',True))
        elif doc.supportsService('com.sun.star.presentation.PresentationDocument'):
            name='impress_pdf_Export';info['family']='presentation';filters.append(prop('ExportHiddenSlides',True))
        elif doc.supportsService('com.sun.star.text.TextDocument'):name='writer_pdf_Export'
        else:raise RuntimeError(message('该文档没有可用的 Office 版式渲染器。','No Office layout renderer is available for this document.'))
        doc.storeToURL(output.resolve().as_uri(),(prop('FilterName',name),prop('Overwrite',True),prop('FilterData',uno.Any('[]com.sun.star.beans.PropertyValue',tuple(filters)))))
        output.with_suffix('.json').write_text(json.dumps(info,ensure_ascii=False),encoding='utf-8')
        print('Rendered',source.name,flush=True)
    finally:
        # storeToURL is synchronous and has closed the completed PDF. Calling
        # close/dispose on imported documents can crash inside the UNO bridge.
        # The parent owns the whole process tree in a Windows job and terminates
        # it after this helper exits, including cancellation and failure paths.
        pass

if __name__=='__main__':
    # UNO bridge finalizers may wait for already-terminated office threads during
    # interpreter shutdown. All files and document handles are closed in main().
    import os,traceback
    try:main()
    except Exception:traceback.print_exc();sys.stderr.flush();os._exit(1)
    sys.stdout.flush();sys.stderr.flush();os._exit(0)
