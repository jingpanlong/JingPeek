"""Collect full upstream notices, retaining distribution paths to avoid collisions."""
import importlib.metadata as md, pathlib, shutil, sys
root=pathlib.Path(__file__).parent/'licenses';root.mkdir(exist_ok=True)
for dist in md.distributions():
    name=dist.metadata.get('Name','unknown');out=root/name
    for path in dist.files or []:
        if any(word in str(path).lower() for word in ('license','copying','notice','copyright')) and str(path).lower().endswith(('.txt','.md','.rst','.html','.bsd','.mit','.gpl','.lgpl','license','copying','notice','copyright','.json')):
            src=pathlib.Path(dist.locate_file(path))
            if src.is_file():
                target=out/pathlib.Path(str(path));target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,target)
for path in (pathlib.Path(sys.base_prefix)/'LICENSE.txt',pathlib.Path(sys.base_prefix)/'LICENSE'):
    if path.exists():shutil.copy2(path,root/'Python-LICENSE.txt')
print('Collected upstream license texts in',root)
