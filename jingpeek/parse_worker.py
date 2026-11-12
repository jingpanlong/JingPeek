from .i18n import tr
"""Content workers avoid importing the GUI and multimedia stack on each file."""
import pathlib
def worker(path,output,conn,language='zh_CN'):
    from .i18n import set_language
    set_language(language)
    try:
        from . import formats as f
        p=pathlib.Path(path)
        result=('html',f.universal_html(p,tr('旧版 Office 的文字模式仅提供基础查看。')) if f.kind(p)=='legacy' else f.render_html(p))
        conn.send(('ok',result))
    except Exception as e:conn.send(('error',f'{type(e).__name__}: {e}'))
    finally:conn.close()
