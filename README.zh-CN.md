# 景速览 JingPeek 1.6.0

> GitHub 项目主页（源码 / 反馈）：<https://github.com/jingpanlong/JingPeek>　｜　[最新版本下载](https://github.com/jingpanlong/JingPeek/releases/latest)　｜　[English README](README.md)

为 Windows 10/11 x64 设计的本地文件快速预览工具，灵感来自 macOS Quick Look。

1.6.0 新增中英文即时切换：在偏好设置中选择简体中文或 English，主界面、托盘、预览提示及设置同步更新，自动记住语言。安装程序提供两种语言；文件正文和文件名保持原样。

保留 1.5.1 桌面兼容修复：支持原生 Windows 桌面、重定向/公共桌面，并适配腾讯桌面整理 DeskGo。键盘事件传递按下瞬间的来源窗口，避免弹框后丢失桌面上下文；桌面无焦点句柄、重命名及菜单状态分别处理。原生桌面优先使用 Shell 的真实文件路径，不再依赖图标显示名称猜文件。

腾讯桌面整理使用自绘界面，没有标准选中文件接口。兼容模式仅在已核对的 DesktopMgr64.exe 桌面主窗口工作，临时调用复制以读取文件路径，随后恢复原剪贴板；检测到期间发生其他复制时，不覆盖新的剪贴板内容。不操作 QQ 聊天窗口，不在搜索/重命名输入时响应。设置可关闭该兼容模式；剪贴板被占用或无法安全备份时会明确提示，可改用资源管理器查看同一文件。此电脑/回收站等系统虚拟图标不是普通文件。

保留 1.5.0 的后台加载、始终置顶、首次释放单文件运行缓存、Office 跨启动预览缓存及任意可读取文件基础查看。

单文件版采用原生 C# 启动器：只在首次运行时释放完整离线引擎，以后直接复用按版本和校验值隔离的本地缓存。第一次仍需要磁盘空间与准备时间，会显示进度并可取消；后续不再重复释放约 1.7 GB 文件。软件已经常驻时再次双击同一单文件，会复用当前服务。Word、Excel、PPT 仍默认显示包含图片与图表的完整静态排版，并新增跨启动的 Office 预览缓存。

## 本次修复与“所有类型”的含义

任何当前账户可读取的普通文件，都可显示基础预览：文件属性、可识别文本（前 64 KB）或十六进制内容（前 4 KB）。空文件、没有扩展名和未知扩展名也有可用展示。专用解析失败时会自动回到基础查看，避免只留下无法预览的错误页。

这不代表所有专有格式都能还原为原软件的版式。DRM、损坏或加密媒体、加密文档、专有设计/工程文件仍可能只能查看基础内容；没有读取权限的文件无法读取。

对于截图中的 MP4 缺编解码器错误：优先使用系统后端快速播放，失败后启动内置 FFmpeg，转换为 H.264 / AAC MP4（音频转 PCM WAV）后在同一预览框播放。无需用户安装 codec pack，不调用外部播放器，不修改原文件，不主动联网。首次兼容准备可能需要等待，可查看进度、取消、按 Esc 或切换文件；切换/关闭会终止当前解码。

兼容预览将视频宽度限制在 1280 像素内，音频为双声道，以便快速查看；不作为无损导出。单次兼容准备最长 180 秒、临时输出小于 1 GB，超过限制会提示并保留基础查看。当前会话最多保留 3 个兼容缓存，正常退出清理。更多菜单中的“尝试内置媒体兼容解码”可手动使用；“查看文件原始内容”适用于任意文件。

微信公众号：**景同志**　｜　小红书：**景同学**

## 使用

运行便携版 EXE，或安装安装版，只需启动一次。**启动后直接常驻系统托盘，不弹出软件主界面。** 在资源管理器里单击选中一个文件（例如 SHA256SUMS.txt），再按 **空格**，即在该文件旁边弹出小型内容预览框。并非只在软件内部选择文件，也不是调用资源管理器原有的右侧预览窗格。

预览框始终置顶，先出现加载提示，再展示内容。预览框默认为 600 × 460 逻辑像素，优先放在所选文件右侧，右侧空间不足时放在左侧或屏幕内。可拖动标题区域移动、拖右下角改变大小。Esc / 再按空格收起，回车使用默认程序打开；方向键继续浏览文件，Ctrl + 滚轮缩放图片。文件区域没有可用定位信息时，按鼠标所在位置定位。

右键系统托盘里的景速览图标，可打开设置、软件介绍、关于与联系作者；不需要进入这些页面才能预览。双击托盘图标打开使用说明。没有 Python 环境也能运行。

| 快捷键 | 功能 |
|---|---|
| 空格 | 资源管理器/桌面唤起，预览窗口中隐藏 |
| Esc | 隐藏预览并返回原来的资源管理器；托盘服务继续运行 |
| Enter | 使用系统关联程序打开当前文件 |
| 左/上、右/下 | 上一个、下一个文件，循环切换 |
| Ctrl + 滚轮 | 图片 / PDF 缩放 |
| Ctrl + O | 选择文件 |
| Ctrl + F | 查找当前文本内容；PDF 暂无内置搜索 |
| F11 | 切换全屏 |

单选文件后，后台建立预览队列，按同目录文件的自然名称排序（不继承资源管理器当前排序）；多选时只浏览所选队列。选择文件夹则列出目录。压缩包预览只列目录，不解压文件。文本、表格可以选择并复制。

小预览框标题栏有置顶、打开、更多菜单和关闭。更多菜单提供适应窗口、原始比例、静态图片旋转、全屏、文件信息等功能。媒体区有播放暂停、进度拖动、音量调节。文件信息面板支持复制路径、资源管理器定位、保存当前可见预览截图（媒体除外）、计算并复制 SHA-256（100 MB 内）。介绍界面仍保留文件列表、最近记录和完整工具栏；超大目录按需显示列表的一部分，方向键仍可切换完整队列，设置提供自动播放、登录启动、Office 原版式预览开关。

关闭窗口和 Esc 只结束当前可见预览；完全退出请使用托盘菜单「退出景速览」。也可执行 `JingPeek.exe --quit`。默认就是后台启动；`--background` 静默后台启动，`--dashboard` 显示介绍界面。

## 实际格式支持及边界

| 类别 | 支持与限制 |
|---|---|
| 图片 | PNG/JPEG/BMP/GIF/WebP/TIFF/ICO/SVG/AVIF，新增 HEIC/HEIF、PSD 合成图、DDS、TGA、PCX、PNM、JPEG 2000、ICNS 等 Pillow 可解码格式；不还原 PSD 图层。GIF 动态播放，静态图片可旋转。超过 8,000 万像素改为基础查看 |
| 音视频 | MP4/MKV/AVI/MOV/WebM/WMV/FLV/MPEG/TS/M2TS/3GP/MXF/RM 等容器及 MP3/WAV/FLAC/AAC/M4A/OGG/Opus/WMA/APE/AMR/AC3/DTS 等音频。系统后端失败后自动使用内置 FFmpeg 兼容解码；具体是否能解码取决于文件本身与内置 FFmpeg 的能力，失败仍可基础查看 |
| PDF | 多页滚动、适应宽度、原始比例、Ctrl + 滚轮缩放；不支持密码输入、编辑、注释、签名和 OCR |
| Word / 文本办公文档 | DOC/DOCX/DOCM/DOTX/DOTM/RTF/ODT：完整静态页面、图片和表格，支持翻页、整页适应与缩放 |
| Excel / 电子表格 | XLS/XLSX/XLSM/XLSB/XLT/XLTX/XLTM/ODS：保留合并单元格、格式、图片、图表；每个工作表整体显示为一页，顶部下拉框切换工作表，隐藏工作表也会标明并展示 |
| PPT / 演示文稿 | PPT/PPTX/PPTM/PPS/PPSX/PPSM/POTX/POTM/ODP：完整静态幻灯片与图片图表，包括隐藏幻灯片；不播放动画、切换效果或内嵌音视频 |
| 代码 | Python、JS/TS、C/C++、C#、Java、Rust、Go、SQL、HTML/CSS、Shell、PowerShell、JSON/YAML 等常见文本格式，Pygments 高亮和行号；HTML 作为源代码显示 |
| Markdown | 标题、列表、表格、链接、引用、围栏代码；本地同目录及子目录图片。使用 Qt 富文本排版，不保证浏览器 CSS 一致；不执行原始 HTML/脚本，不自动加载网络图片 |
| 表格 | CSV/TSV 展示前 500 行 × 40 列 |
| 压缩包 | ZIP/7Z/RAR/TAR/TAR.GZ/TGZ 等目录，最多 2,000 项；单独 GZ/BZ2/XZ 流显示解压后前 64 KB；不解压到磁盘、不支持压缩包内二次预览；加密头需密码时不支持 |
| 文件夹/其他 | 文件夹前 2,000 项目录；任意可读取文件显示属性以及文本探测/十六进制内容；常见 PDF、图片、ZIP、媒体可按文件签名识别，无需扩展名 |

Office 预览是完整静态渲染，不是可编辑的 Office。缺失字体、特殊公式、SmartArt、专有嵌入对象或不同排版引擎可能造成差异，不能保证与 Microsoft Office 逐像素一致。工作表很大时可缩放查看；不执行宏、不更新外部链接。转换失败会明确提示，可重试或主动选择“文字提取预览”，不会悄悄降级成纯文字。

内置 LibreOffice 使用独立临时配置和 Windows 作业对象运行，取消、切换文件或超时会结束本次渲染进程，不关闭用户已打开的 Office/WPS。Office 输入最大 200 MB、输出 PDF 最大 512 MB、每次最长 120 秒，进程组内存上限 2 GB。当前会话保留最近 8 个渲染结果，临时目录在退出时清理。另外最多缓存 16 份、总计 256 MB 的 Office 静态预览（单份不超过 32 MB），文档路径、大小或修改时间改变后重新生成，可在设置中“清除预览缓存”。大文本最多读取前 2 MB；普通解析 25 秒超时。

## 隐私与系统集成

- 本地解析文件，不上传文件，不主动联网。网页链接点击后会询问，再用系统浏览器打开。
- 不修改原文件，不自动执行压缩包内容或文档宏。默认程序打开是用户主动按 Enter 的操作。
- 设置与最近路径保存在 `HKCU\Software\JingTongXue\JingPeek`；日志位于 `%LOCALAPPDATA%\JingPeek\app.log`。Office 临时 PDF 位于系统临时目录，正常退出清理；可复用的排版缓存位于 `%LOCALAPPDATA%\JingPeek\cache\office-v2`，可在设置清除。
- 登录启动在 `HKCU\Software\Microsoft\Windows\CurrentVersion\Run\JingPeek`，可在设置中关闭。移动便携版后需重新开关登录启动。安装时可选右键菜单与桌面快捷方式。
- 空格钩子仅在普通 Windows Explorer 文件区和桌面响应，输入框不抢占。第三方文件管理器、提权资源管理器、虚拟目录、桌面虚拟图标可能无法读取；仍可拖入/选择真实文件。
- 完整 Office 渲染引擎随 EXE 离线提供，压缩包约数百 MB、运行时约 1.7 GB。单文件版仅首次或版本更新时释放到 `%LOCALAPPDATA%\JingPeek\portable\版本-校验值`，后续启动复用；首次速度受磁盘和安全软件影响。此目录是运行文件缓存，运行期间请勿删除；完全退出后可删除，下次会重新准备。安装版也保留，适合固定位置使用。
- 本版未购买代码签名证书，EXE 未签名；发布前建议由发行者签名。

## 源码运行与构建

需要 Windows 10/11 x64、Python 3.12、系统自带的 .NET Framework 4.8 C# 编译器、Inno Setup 6（构建安装版）。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -c "from comtypes.client import GetModule; GetModule('UIAutomationCore.dll')"
.\prepare_office_engine.ps1
.\.venv\Scripts\python.exe main.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe tests\integration.py
.\.venv\Scripts\python.exe tests\generate_compat_fixtures.py
.\build.ps1 -Python .\.venv\Scripts\python.exe -ISCC 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe'
```

源码 ZIP 不重复包含约 1.5 GB 的第三方二进制 Office 引擎。prepare_office_engine.ps1 会从文档基金会官方地址下载固定版本 26.8.2，核对 SHA-256 和签名后提取到 office_runtime；不安装 LibreOffice、不改变文件关联。首次构建需要联网，最终 EXE 运行不需要联网。引擎许可证和 NOTICE 随二进制包完整保留。

build.ps1 生成目录版 stage/JingPeek、单文件便携 EXE 和安装版 EXE。依赖版本固定在 requirements.txt，完整许可放在 licenses/。原始程序源码采用 MIT，第三方组件各自许可独立。

源码结构：`main.py` 启动/打包入口；`jingpeek/app.py` 界面与预览；`jingpeek/native.py` Windows 集成及选中文件位置；`jingpeek/positioning.py` 浮动框定位和混合 DPI 坐标转换；`jingpeek/background.py` 非阻塞选中项与目录读取；`portable_launcher.cs` / `build_portable.py` 首次释放的原生单文件启动器；`jingpeek/formats.py` 格式解析；`jingpeek/office_render.py` 隔离渲染调度；`assets/office_render_helper.py` UNO 静态 PDF 导出；`installer.iss` 安装器；`tests/` 解析与界面集成测试。

技术参考：[Qt PDF](https://doc.qt.io/qtforpython-6/PySide6/QtPdf/index.html)、[Qt Multimedia](https://doc.qt.io/qtforpython-6/PySide6/QtMultimedia/QMediaPlayer.html)、[PyInstaller](https://pyinstaller.org/en/stable/usage.html)。


## 中英文切换 / Language

在「偏好设置 → 界面语言」选择「简体中文」或「English」，立即生效，无需重新启动。主界面、浮动预览、设置、托盘菜单、文件信息及提示支持两种语言，选择会自动保存。文件名、文档正文、作者账号和工作表原名保持不变。安装程序同样支持中文和英文；已有软件语言选择不会被安装程序覆盖。第三方引擎和 Windows 原生错误信息可能使用其自身语言。

Open **Preferences → Interface language**, then choose **简体中文** or **English**. Changes apply immediately and are saved for future launches. File names, document content, author account names and original sheet names are preserved. The installer also supports both languages. Existing app language preferences are retained during installation. Third-party engines and Windows errors may use their own language.
