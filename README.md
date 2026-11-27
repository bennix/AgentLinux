# AgentLinux

在开始菜单中选择“帮助和支持”，或按 **Win + F1**，可打开新版中英文离线帮助中心。Agent 也可通过 `agentlinux-components app/agentlinux-xp-help.desktop --launch` 打开帮助。选择左侧主题即可查看文件、网络、打印机和键鼠操作说明。字体样张支持分页打印，也可按 Win + R 输入 `shell:Fonts` 打开字体文件夹。控制面板会记住上次的视图，添加打印机时会检查队列名称。

Open **Help and Support** from Start or press **Win + F1** for offline help in English or Chinese. Agents can open the same window with `agentlinux-components app/agentlinux-xp-help.desktop --launch`. Select a topic on the left for instructions on files, networking, printers, or input devices. Font samples now support multipage printing. To open Fonts, press Win + R and enter `shell:Fonts`. Control Panel remembers the selected view, and the Add Printer wizard validates queue names.

XP 资源管理器支持移除无父驱动器的卷，中文右键菜单支持“新建 → 文件夹”。字体样张从顶部打开，“运行”支持 control appwiz.cpl,,3，中文桌面的网络断开通知使用系统翻译。

XP Explorer handles removal of volumes without a parent drive. Its Chinese context menu includes New Folder. Font previews open at the top, Run recognizes control appwiz.cpl,,3, and network disconnection notifications follow the Chinese desktop locale.

XP 控制面板现在支持用快捷键选择 HTTP、HTTPS、邮件、文本和 PDF 的默认应用。字体样张支持 Alt+P、字符预览和十档字号。此版也修正了关于窗口的关闭按钮翻译，并清理了任务栏中多余的 Qt 辅助窗口。

The XP Control Panel now supports keyboard selection of default apps for HTTP, HTTPS, email, text and PDF. Alt+P opens the font sample with character rows and ten point sizes. This release also localizes the About dialog’s Close button and hides a stray Qt helper window from the taskbar.

XP 桌面的 Wi-Fi 属性支持键盘配置 IPv4 和 DNS。添加打印机向导可创建 IPP 队列并发送测试页。Agent 可以区分“共享文件夹”主窗口和“共享此文件夹”对话框，也可以通过 system/power 读取外接电源、充电状态和电量。

The XP desktop supports keyboard configuration of IPv4 and DNS. The Add Printer Wizard can create an IPP queue and send a test page. The desktop agent distinguishes the Chinese folder-sharing dialog from its parent window. The system/power component reports external power, battery charge state and percentage.

系统属性新增高级页。控制面板支持键盘循环切页。设备管理器可通过 F5 或操作菜单刷新硬件列表。声音属性保留长设备名称的下拉按钮。

System Properties adds an Advanced tab. Keyboard shortcuts cycle between property pages. Device Manager refreshes via F5 or the Action menu. Audio selectors keep their arrows visible for long device names.

任务管理器支持 Alt+F、N 创建新任务。声音属性新增语音页。经典控制面板可以按首字母定位图标。

从桌面双击“我的文档”即可打开个人文档目录。用记事本保存文本后，可在“开始”菜单的最近文档中重新打开。

Agent 可直接打开显示属性、系统设置、文件夹选项和界面语言。笔记本上的 24 个控制面板入口均已通过中英文启动实测。

Agents can open Display Properties, System Settings, Folder Options and Display Language directly. All 24 Control Panel entries were launched on a physical laptop in Chinese and English.

新版「关于 AgentLinux」显示学院标识、系统版本、内核与架构。可运行 `winver`，也可通过 Agent 组件目录打开。

About AgentLinux now shows the college emblem, operating system version, kernel and architecture. Open it with `winver` or from the agent component catalog.

系统设置采用 XP 经典图标布局，可从开始菜单或终端命令 `control settings` 打开。

Open the classic XP System Settings grid from the Start menu or with `control settings`.

XP 风格桌面提供中英文控制面板、无线网络连接和添加打印机向导。在 x86-64 UEFI 虚拟机中，正式版 `v2026.11.27.2` 已全新安装到 48 GiB 虚拟硬盘。移除 ISO 后，测试账户成功从硬盘登录中文 XP 风格桌面。

Release `v2026.11.27.2` was installed on a blank 48 GiB virtual disk in an x86-64 UEFI VM. After the ISO was removed, the test account signed in to the Chinese XP-style desktop from that disk.

快捷方式向导支持含空格的路径和同名文件。右键点击已连接的 Wi-Fi 可查看连接状态和 TCP/IPv4 属性。

The shortcut wizard handles paths with spaces and existing filenames. Right-click a connected Wi-Fi network to view its status and TCP/IPv4 properties.

**[完整 ISO 单文件 / Download full ISO](https://huggingface.co/datasets/Bennixzp2024/AgentLinux/resolve/v2026.11.28.3/AgentLinux-24.04.5-desktop-amd64.iso?download=true)** · [SHA-256](https://huggingface.co/datasets/Bennixzp2024/AgentLinux/resolve/v2026.11.28.3/AgentLinux-24.04.5-desktop-amd64.iso.sha256?download=true) · [Hugging Face](https://huggingface.co/datasets/Bennixzp2024/AgentLinux)


MyIME 支持用上下方向键选词和 Esc 取消输入。添加打印机向导提供佳能 LBP6030w 官方驱动下载和网络设置指引。Live、简装与标准安装均包含修复。

MyIME supports Up and Down for candidate selection and Esc to cancel composition. The Add Printer Wizard links to the official Canon LBP6030w driver and explains network setup. The update is included in all three desktop layers.

Studio 主题提供原创桌面图标、顶部菜单栏、Dock、窗口边框和浅色控制面板。从 **控制面板 → 外观和主题 → 桌面主题** 可即时切换 XP 和 Studio。两种切换方向均已在 UEFI Live 会话实测。

Studio adds original desktop icons, a top menu bar, a dock, window decorations, and a light Control Panel. Switch between XP and Studio via **Control Panel → Appearance and Themes → Desktop Theme**. Both directions were verified in a UEFI Live session.

Studio 顶部菜单将常用入口置顶，其余应用按用途分组。

The Studio menu keeps frequent launchers at the top and groups other applications by category.

ISO SHA-256 (v2026.11.28.3)

`96913aec32668957ff69b2a83f8f4df0cd1514974bdce68f33545fae243c57ee`

| 启动方式 / Boot mode | 用户名 / Username | 密码 / Password |
| --- | --- | --- |
| Live 桌面 / Live desktop | `agentlinux` | 默认自动登录，手动登录时留空 / Automatic sign-in, leave blank if prompted |
| 预装 SanDisk U 盘 / Preinstalled SanDisk USB | `agent` | `agentfudan` |
| 自行安装到硬盘 / Installation on your own disk | 安装时创建 / Set during installation | 安装时设置 / Set during installation |

[产品官网（中文）](https://bennix.github.io/AgentLinux/) · [English website](https://bennix.github.io/AgentLinux/en.html) · [下载完整 ISO](https://huggingface.co/datasets/Bennixzp2024/AgentLinux/resolve/v2026.11.28.3/AgentLinux-24.04.5-desktop-amd64.iso?download=true)

基于 Ubuntu Kylin 24.04.5 LTS，适用于 Intel / AMD x86-64 电脑和 x86-64 虚拟机。Apple Silicon 需要使用 x86-64 模拟。将 ISO 挂载到虚拟光驱后启动，可试用中文桌面，也可双击桌面的“安装到硬盘”启动安装器。

![AgentLinux XP 风格桌面预览](docs/assets/xp-desktop.jpg)

## 桌面助手

在应用菜单搜索 **ZenMux 桌面助手**。在设置页输入 ZenMux API Key 和平台上的完整模型 ID，点击保存。输入另一个 ID 并保存即可扩充模型列表。没有密钥时，设置页提供[邀请注册链接](https://zenmux.ai/invite/GBQMC5)。接口为 `https://zenmux.ai/api/v1/chat/completions`。

勾选允许桌面操作后，可输入“打开主目录”“在主目录创建名为笔记的文件夹”或“查看系统信息”。助手还可查询已安装应用、启动应用、列出和切换窗口、查看并激活支持辅助功能的具名按钮，以及查询网络连接、磁盘空间和失败的服务。每个工具调用都需确认，结果返回给所选模型以继续任务，单轮用户请求最多进行八轮工具调用。所选模型需要支持工具调用。助手会显示操作并请求确认。中文输入支持 Fcitx 5 和 MyIME，可在任务栏切换。MyIME 提供宋体候选、联想和词频学习。

API 密钥与模型设置保存在当前用户主目录的 `~/.config/zenmux-agent/settings.json`，文件权限为 0600，内容以明文存储。请在安装后的系统内保存以跨重启使用。普通 Live 试用会话使用临时主目录，关机后会丢失设置。

## 浏览器隐私

镜像为自带的 Firefox 配置系统策略，锁定关闭 WebRTC（media.peerconnection.enabled）。这会停用依赖 WebRTC 的网页通话、屏幕共享和对等连接。在 Firefox 的 about:policies 页面可以查看启用的策略。

## 构建

需要 Python 3.9+、xorriso 和支持 xz 的 squashfs-tools。将[官方底包](https://cdimage.ubuntu.com/ubuntukylin/releases/24.04/release/ubuntukylin-24.04.5-desktop-amd64.iso)放在 `build/base.iso`。项目中的 `overlay/` 包含已准备好的 ZenCode、Obscura Firefox、Cage 安装包、输入法配置和系统集成文件。运行 `python3 build-iso.py`。脚本验证底包 SHA-256，生成附加 SquashFS 层，更新 Live 引导参数、两种安装源和校验清单，输出 ISO 和 SHA-256 文件。

### 检查 XP 镜像的构建层

上面的 `build-iso.py` 生成基础 Agent 层。XP 版本另外打入桌面组件、登录界面和启动主题。要从已有 XP 镜像核对实际打包内容，可在一个新建目录中执行：

```sh
xorriso -indev /path/to/AgentLinux-XP.iso -osirrox on -extract /casper/minimal.standard.agent.apps.xp.squashfs xp-standard.squashfs
unsquashfs -ll xp-standard.squashfs
```

标准硬盘安装使用上述 XP 层。Live 桌面和最小安装分别使用 `minimal.standard.live.agent.apps.xp.squashfs` 和 `minimal.agent.apps.xp.squashfs`。桌面组件的打包映射见 [stage-components.py](packaging/xp-desktop/stage-components.py)，Live 启动主题的生成步骤见 [build-live-initrd.py](packaging/xp-desktop/boot/build-live-initrd.py)。

## Claude Cage

应用菜单中的 **Claude Cage 隔离工作台设置** 使用镜像随附的官方 0.2.0-rc amd64 安装包。首次打开时确认安装，随后可选择联网安装本机虚拟机组件。工作台以普通用户运行。使用本机客机需要可读写的 /dev/kvm、虚拟磁盘空间及首次客机下载；在 Apple Silicon 上模拟 x86 桌面无法提供该 x86 KVM 环境。账号使用须遵循服务商规则。详见[官方项目](https://github.com/Lee-xeo/Claude-Cage)。

## 定制版信息

默认浏览器采用 Obscura Firefox 0.3.14，保留上游手动更新方式。系统选择它处理 HTTP、HTTPS 和 HTML。简体中文分别使用 Noto Sans CJK SC、Noto Serif CJK SC 和 Noto Sans Mono CJK SC。

桌面菜单、Ctrl+Alt+T、Win+T、文件管理器的终端动作以及系统默认终端入口使用 Cage。首次使用会打开安装和配置工作台；配置完成后再开终端，即通过 claude-cage shell 连接 Cage 环境。每个窗口是独立会话，同一 Cage 配置共用一台持久客机。桌面入口不执行传入的宿主命令。系统 TTY 和 SSH 登录仍用于维护。

助手首次使用 ZenMux。设置页也可填写其他 OpenAI Chat Completions 兼容供应商的名称、Base URL、API Key 和模型 ID。每个供应商独立保存密钥和模型列表。请填写不含 /chat/completions 的接口前缀。改动 Base URL 后需重新填写密钥；更换供应商或地址后开启新对话。HTTP 仅限本机接口。

## 微信操作与 Agent 工作台

登录桌面后启动 ZenCode 3.14.45，也可在应用菜单或桌面助手中打开。先在 ZenCode 设置自己的模型提供商，再打开工作区，使用“手机控制”中的微信配对入口扫码，选择允许的账号和工作区。远程操作依赖该用户图形会话、网络和正在运行的 ZenCode Host。手机与桌面续接同一任务，可查看进度、回答权限请求、指定文件并通过微信接收。文件回传由上游校验工作区、接收目标、文件大小与会话令牌。原生电脑控制在 ZenCode 内开启，并受图形会话权限和应用可访问性限制。桌面助手与 ZenCode 各自管理供应商凭据。

## 发布与完整构建层 / Release and complete build layer

[中文产品页](https://bennix.github.io/AgentLinux/) · [English landing page](https://bennix.github.io/AgentLinux/en.html) · [Release](https://github.com/bennix/AgentLinux/releases/tag/v2026.11.28.3)

运行 `python3 download-iso.py` 下载、续传、合并并校验完整 ISO。请为 ISO 预留至少 9 GB 可用空间。Allow at least 9 GB of free space for the ISO. Run the same command from a writable directory to download and verify the complete image. The ISO contains every bundled component. Ordinary Git tracks the integration sources; the release carries the complete filesystem layer, including third-party packages and browser modifications.

在干净的克隆中按以下步骤还原构建层。Restore the full layer before rebuilding from a clean clone (Linux, xorriso and squashfs-tools):

```sh
python3 download-iso.py
mkdir -p build
xorriso -osirrox on -indev AgentLinux-24.04.5-desktop-amd64.iso -extract /casper/minimal.agent.squashfs build/agent.squashfs
unsquashfs -d build/restored-overlay build/agent.squashfs
cp -a build/restored-overlay/. overlay/
```

然后按上文下载官方底包并运行构建脚本。After restoring the layer, download the official base ISO as described above, apply any source changes, and run the builder. Bundled upstream applications retain their respective notices and licenses.

### 上游版本 / Upstream releases

- [ZenCode 3.14.45](https://github.com/bennix/ZCode/releases/tag/v3.14.45)
- [Obscura Firefox 0.3.14](https://github.com/bennix/ObscuraFirefox/releases/tag/firefox-v0.3.14)
- [Claude Cage 0.2.0-rc](https://github.com/Lee-xeo/Claude-Cage/releases/tag/v0.2.0-rc)

## Claude Code 隐私

主机使用 Claude Code 的 managed-settings.d 策略关闭使用指标、错误上报和反馈调查。重新启动支持策略片段的 Claude Code 后生效。Claude 网站、第三方浏览器、独立 Cage 客机与服务端记录有自己的数据处理方式。使用 Cage 中的 CLI 时，可在**客机**内的 /etc/claude-code/managed-settings.d/ 安装相同的 [策略文件](overlay/etc/claude-code/managed-settings.d/40-agentlinux-privacy.json)。Claude 原生 Remote Control 的可用性可能受关闭指标和功能标志影响。[Claude Code 官方数据说明](https://code.claude.com/docs/en/data-usage)

### MyIME 中文输入法（x86-64 Linux 版）

新版镜像的默认中文输入法使用 macOS 版的 Swift IMEKit、原始 SQLite 词库和 Emoji 数据。Fcitx 5 负责 Linux 桌面的按键、预编辑、翻页和候选选择。按 Ctrl+空格启用输入，按空格选中候选，再按空格或数字键选择联想续写。单击 Shift 切换中英文。系统拼音仍可在 Fcitx 中选择。

从应用菜单打开“MyIME 输入法设置”，可以调整个人词频、系统词频、上下文权重，选择模糊音、繁体和英文释义，并导入或导出用户词组。用户数据库保存在 `$XDG_DATA_HOME/myime/user.sqlite`（默认 `~/.local/share/myime/user.sqlite`）。已安装系统可跨重启保留学习记录；普通非持久化 Live 会话的主目录随关机清除。

已有 AgentLinux 可运行 `sudo apt install ./agentlinux-myime_1.0.14-1_amd64.deb`，重新登录，在 Fcitx 5 配置中添加 MyIME。字体和配色由 Linux 桌面的 Fcitx 候选面板控制，英文拼写建议使用系统 Enchant 英语词典。

从源码重建时，在 Ubuntu 24.04 amd64 准备 Swift 6.1、clang++、pkg-config 和 libsqlite3-dev、libfcitx5core-dev、libjson-c-dev、libenchant-2-dev、libglib2.0-dev，运行 `packaging/myime/stage.sh /path/to/MyIME overlay`（原版代码基线 d5e38ef），再运行 `python3 build-iso.py --output AgentLinux-24.04.5-myime-amd64.iso`。

### 腾讯微信 Linux 客户端

含微信的 x86-64 镜像在应用菜单提供“微信”，可从桌面打开并用手机扫码登录。2026-11-20 核对腾讯官网，页面标注版本 4.1.13，官方 amd64 Debian 包版本为 4.1.13.26。MyIME 与微信一同内置。客户端的账号登录和 AgentLinux 的微信遥控配对各自独立。

重建时从[腾讯微信 Linux 官网](https://linux.weixin.qq.com/)下载 x86_64 的 Debian 包，执行 `packaging/wechat/stage.sh WeChatLinux_x86_64.deb overlay`，再运行 ISO 构建脚本。此版官方包的 SHA-256 为 `a0db8caeee8d1e6cfe0aa5ce58710270f8d74a90ff4920f53a3fc22aa0956fe9`。

### ZenOffice

MyIME、微信和 ZenOffice 合集镜像在“办公”菜单中提供 ZenOffice 0.6.108，可直接启动。该版本来自项目发布的 amd64 Debian 包。构建脚本校验上游 SHA-256，并把应用、菜单入口及随包的 AppArmor 配置加入 Live、最小安装和标准安装的文件系统层。

```sh
python3 packaging/zenoffice/build-image.py AgentLinux-24.04.5-myime-wechat-amd64.iso zenoffice_0.6.108_amd64.deb AgentLinux-24.04.5-myime-wechat-zenoffice-amd64.iso --obscura-firefox ObscuraFirefox-0.3.14-linux-amd64.deb --claude-cage Cage-0.2.0-rc-linux-amd64.deb
```

[ZenOffice 产品主页](https://bennix.github.io/GenZenMuxAIOffice/) · [对应版本](https://github.com/bennix/GenZenMuxAIOffice/releases/tag/v0.6.108)

### 硬盘安装与桌面合集

笔记本合盖时，系统默认保持运行，UKUI 关闭内屏。此设置适用于外接电源和电池供电。

从 U 盘进入 Live 桌面，打开 Ubuntu Kylin 安装器，选择安装目标硬盘；安装完成后拔下启动盘，从硬盘重启。镜像的标准安装源和最小安装源均包含 AgentLinux 定制层和办公应用层，安装后的主目录用于保存个人文件和应用设置。

### Cage 首次安装

先在 Cage 工作台创建或解锁本地账户，按工作台提示完成安装。

应用菜单中的“本机终端”（Host Terminal）打开独立的宿主机 shell。Ctrl+Alt+T 仍打开默认的 Cage 终端。

在系统托盘展开已连接的 Wi-Fi，点击“属性”查看当前 IP、网关和 DNS，或进入网络连接编辑器。

### 界面语言与输入法

要切换中英文界面，按 Win+R，输入 `control intl.cpl`，选择「简体中文」或「English」。点击「确定」，注销后重新登录即可生效。

To change the desktop language, press Win+R, enter `control intl.cpl`, select English or 简体中文, and click OK. Sign out and sign back in to apply the change.

AgentLinux 自有设置界面支持中英文。UKUI 登录时启动 Fcitx 5 并注册输入法托盘，异常退出后会自动重启。
