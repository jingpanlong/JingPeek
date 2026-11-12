import multiprocessing, sys, pathlib, logging, os
if __name__=='__main__':
    multiprocessing.freeze_support()
    logdir=pathlib.Path(os.environ.get('JINGPEEK_DATA',os.environ.get('LOCALAPPDATA',str(pathlib.Path.cwd()))))/'JingPeek'
    logdir.mkdir(parents=True,exist_ok=True)
    logging.basicConfig(filename=logdir/'app.log',level=logging.WARNING,encoding='utf-8')
    try:
        from jingpeek.app import run
        sys.exit(run())
    except Exception:
        logging.exception('fatal')
        if '--verify' in sys.argv:sys.exit(1)
        import ctypes
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\JingTongXue\JingPeek') as key:language=winreg.QueryValueEx(key,'language')[0]
        except OSError:language='zh_CN'
        english=os.environ.get('JINGPEEK_LANG',language)=='en_US'
        ctypes.windll.user32.MessageBoxW(None,('Startup failed. See log: ' if english else '启动失败，请查看日志：')+str(logdir/'app.log'),'JingPeek' if english else '景速览',16)
