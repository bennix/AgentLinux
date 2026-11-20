# ZenMux 中文桌面 ISO

**[完整 ISO 单文件 / Download full ISO](https://huggingface.co/datasets/Bennixzp2024/AgentLinux/resolve/v2026.11.20.4/AgentLinux-24.04.5-desktop-amd64.iso?download=true)** · [SHA-256](https://huggingface.co/datasets/Bennixzp2024/AgentLinux/resolve/v2026.11.20.4/AgentLinux-24.04.5-desktop-amd64.iso.sha256?download=true) · [Hugging Face](https://huggingface.co/datasets/Bennixzp2024/AgentLinux)


[产品官网（中文）](https://bennix.github.io/AgentLinux/) · [English website](https://bennix.github.io/AgentLinux/en.html) · [下载完整 ISO](https://github.com/bennix/AgentLinux/releases/tag/v2026.11.20.4)

基于 Ubuntu Kylin 24.04.5 LTS，适用于 Intel / AMD x86-64 电脑和 x86-64 虚拟机。Apple Silicon 需要使用 x86-64 模拟。将 ISO 挂载到虚拟光驱后启动，可试用中文桌面，也可通过底座安装器安装到磁盘。

## 桌面助手

在应用菜单搜索 **ZenMux 桌面助手**。在设置页输入 ZenMux API Key 和平台上的完整模型 ID，点击保存。输入另一个 ID 并保存即可扩充模型列表。没有密钥时，设置页提供[邀请注册链接](https://zenmux.ai/invite/GBQMC5)。接口为 `https://zenmux.ai/api/v1/chat/completions`。

勾选允许桌面操作后，可输入“打开主目录”“在主目录创建名为笔记的文件夹”或“查看系统信息”。所选模型需要支持工具调用。助手会显示操作并请求确认。中文输入使用 Fcitx 5 拼音，通常可用 Ctrl+空格切换。

## 代理和订阅

在设置中粘贴单个 VLESS 链接或 HTTPS 机场订阅地址，点击“导入 / 刷新节点”，选择节点，勾选“ZenMux 请求使用代理”后保存。支持 Mihomo 可解析的 Clash YAML 节点、URI 列表和 Base64 节点列表。点击“测速并选择最佳节点”可让每个节点分别向 ZenMux 首页和 Google generate_204 发起三次 HTTPS 延迟探测。两个目标分别显示成功次数和延迟中位数。列表优先比较 ZenMux 成功次数和延迟，平局时比较 Google 结果，自动选中本轮表现最佳的可用节点，仍可手动选择，点击保存后生效。测速反映当下的可达性与响应延迟，不测下载带宽。刷新订阅需要能直接访问订阅服务器。模型请求按所选节点发出，代理失败会显示错误。代理范围为桌面助手内的 ZenMux 请求。

密钥、订阅地址和节点数据保存在当前用户主目录的 `~/.config/zenmux-agent/settings.json`，文件权限为 0600，内容以明文存储。请在安装后的系统内保存以跨重启使用。普通 Live 试用会话使用临时主目录，关机后会丢失设置。

## 浏览器隐私

镜像为自带的 Firefox 配置系统策略，锁定关闭 WebRTC（media.peerconnection.enabled）。这会停用依赖 WebRTC 的网页通话、屏幕共享和对等连接。在 Firefox 的 about:policies 页面可以查看启用的策略。此策略范围限于 Firefox；助手的代理设置只用于模型请求，浏览器普通网页访问仍遵循浏览器及系统自身的网络配置。

## 构建

需要 Python 3.9+、xorriso 和支持 xz 的 squashfs-tools。将[官方底包](https://cdimage.ubuntu.com/ubuntukylin/releases/24.04/release/ubuntukylin-24.04.5-desktop-amd64.iso)放在 `build/base.iso`。项目中的 `overlay/` 包含已准备好的 ZenCode、Obscura Firefox、Mihomo、Cage 安装包、输入法配置和系统集成文件。运行 `python3 build-iso.py`。脚本验证底包 SHA-256，生成附加 SquashFS 层，更新 Live 引导参数、两种安装源和校验清单，输出 ISO 和 SHA-256 文件。

## Claude Cage

应用菜单中的 **Claude Cage 隔离工作台设置** 使用镜像随附的官方 0.1.8 amd64 安装包。首次打开时确认安装，随后可选择联网安装本机虚拟机组件。工作台以普通用户运行。使用本机客机需要可读写的 /dev/kvm、虚拟磁盘空间及首次客机下载；在 Apple Silicon 上模拟 x86 桌面无法提供该 x86 KVM 环境。Cage 通过自己的界面单独配置代理，助手中的节点不会自动传入 Cage。账号使用须遵循服务商规则。详见[官方项目](https://github.com/Lee-xeo/Claude-Cage)。

## 定制版信息

出品方：复旦大学计算与智能创新学院（依项目指定署名）。默认主页为[学院网站](https://cs.fudan.edu.cn/)。

默认浏览器采用 Obscura Firefox 0.3.7，保留上游手动更新方式。系统选择它处理 HTTP、HTTPS 和 HTML。简体中文分别使用 Noto Sans CJK SC、Noto Serif CJK SC 和 Noto Sans Mono CJK SC。

桌面菜单、Ctrl+Alt+T、Win+T、文件管理器的终端动作以及系统默认终端入口使用 Cage。首次使用会打开安装和配置工作台；配置完成后再开终端，即通过 claude-cage shell 连接 Cage 环境。每个窗口是独立会话，同一 Cage 配置共用一台持久客机。桌面入口不执行传入的宿主命令。系统 TTY 和 SSH 登录仍用于维护。

助手首次使用 ZenMux。设置页也可填写其他 OpenAI Chat Completions 兼容供应商的名称、Base URL、API Key 和模型 ID。每个供应商独立保存密钥和模型列表。请填写不含 /chat/completions 的接口前缀。改动 Base URL 后需重新填写密钥；更换供应商或地址后开启新对话。HTTP 限本机直连接口。节点测速仍固定探测 ZenMux 和 Google。

## 微信操作与 Agent 工作台

登录桌面后启动 ZenCode 3.14.44，也可在应用菜单或桌面助手中打开。先在 ZenCode 设置自己的模型提供商，再打开工作区，使用“手机控制”中的微信配对入口扫码，选择允许的账号和工作区。远程操作依赖该用户图形会话、网络和正在运行的 ZenCode Host。手机与桌面续接同一任务，可查看进度、回答权限请求、指定文件并通过微信接收。文件回传由上游校验工作区、接收目标、文件大小与会话令牌。原生电脑控制在 ZenCode 内开启，并受图形会话权限和应用可访问性限制。桌面助手与 ZenCode 各自管理供应商凭据。

“桌面网络使用代理”作用于遵循 GNOME 系统代理设置的应用，使用选定节点，仅监听回环地址。关闭时恢复启用前的系统代理配置。“AI 请求使用代理”独立控制桌面助手的模型请求。Cage 虚拟机和使用自身网络设置的软件各自配置代理。

## 发布与完整构建层 / Release and complete build layer

[中文产品页](https://bennix.github.io/AgentLinux/) · [English landing page](https://bennix.github.io/AgentLinux/en.html) · [Release](https://github.com/bennix/AgentLinux/releases/tag/v2026.11.20.4)

运行 `python3 download-iso.py` 下载、续传、合并并校验完整 ISO。需要至少 8 GB 可用空间。Run the same command from a writable directory to download and verify the complete image. The ISO contains every bundled component. Ordinary Git tracks the integration sources; the release carries the complete filesystem layer, including third-party packages and browser modifications.

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

- [ZenCode 3.14.44](https://github.com/bennix/ZCode/releases/tag/v3.14.44)
- [Obscura Firefox 0.3.7](https://github.com/bennix/ObscuraFirefox/releases/tag/firefox-v0.3.7)
- [Claude Cage 0.1.8](https://github.com/Lee-xeo/Claude-Cage/releases/tag/v0.1.8)
- [Mihomo 1.19.34](https://github.com/MetaCubeX/mihomo/releases/tag/v1.19.34)

## 系统网络连接与 Claude Code 隐私

已安装 2026.11.19 发行版的用户可下载[系统网络升级包](https://github.com/bennix/AgentLinux/releases/download/v2026.11.19/agentlinux-system-network.deb)，在 AgentLinux 内运行 `sudo apt install ./agentlinux-system-network.deb`。新构建的网络版镜像已集成此功能。旧发行版的 29 个分卷仍对应原始 ISO。

1. 在 ZenMux 助手中导入订阅，选择节点并保存。
2. 在系统设置分类中打开 **系统网络 · 机场代理**，点击“使用已保存的节点连接”。首次需管理员授权，重新选择节点后可再次点击以应用。
3. NetworkManager 的“机场代理 (AgentLinux)”连接可随时启停；命令行为 `nmcli con up uuid 0e7b6bb9-91e3-46f6-bfc5-00f7c33a7978` 或 `nmcli con down uuid 0e7b6bb9-91e3-46f6-bfc5-00f7c33a7978`。连接默认手动启用。

启用后，主机默认网络命名空间的应用 TCP/UDP 通过 Mihomo TUN 和单个所选节点路由。IPv4/IPv6 出站过滤保留回环、隧道核心带标记的连接、DHCP 与必要的 IPv6 邻居发现。域名解析经隧道；解析代理服务器名称本身会使用引导 DNS。隧道停机时过滤继续生效，主动断开 NetworkManager 连接后撤销。主机应用中的“直连”仍受系统隧道路由；同时启用应用自己的代理可能形成二次代理。容器转发、独立网络命名空间与 Cage 客机需要各自配置和验收。

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

MyIME、微信和 ZenOffice 合集镜像在“办公”菜单中提供 ZenOffice 0.6.107，可直接启动。该版本来自项目发布的 amd64 Debian 包。构建脚本校验上游 SHA-256，并把应用、菜单入口及随包的 AppArmor 配置加入 Live、最小安装和标准安装的文件系统层。

```sh
python3 packaging/zenoffice/build-image.py AgentLinux-24.04.5-myime-wechat-amd64.iso zenoffice_0.6.107_amd64.deb AgentLinux-24.04.5-myime-wechat-zenoffice-amd64.iso
```

[ZenOffice 产品主页](https://bennix.github.io/GenZenMuxAIOffice/) · [对应版本](https://github.com/bennix/GenZenMuxAIOffice/releases/tag/v0.6.107)

### 硬盘安装与桌面合集

`AgentLinux-24.04.5-desktop-amd64.iso` 还包含Clash Verge Rev 2.5.10（初始订阅列表为空）。联网后在“网络”菜单打开 Clash Verge，可自行添加订阅。在“系统网络 · 机场代理”窗口查看已连接 Wi-Fi 的 IPv4 和 IPv6 地址。Obscura Firefox 的书签工具栏提供“火烧云 PRO 官网”和“火烧云 PRO 邀请注册”，使用所提供品牌图中的红橙色云朵标识。

从 U 盘进入 Live 桌面，打开 Ubuntu Kylin 安装器，选择安装目标硬盘；安装完成后拔下启动盘，从硬盘重启。镜像的标准安装源和最小安装源均包含 AgentLinux 定制层和办公应用层，安装后的主目录用于保存个人文件和应用设置。重建合集时在 ZenOffice 镜像构建命令后加入 `--clash-verge Clash.Verge_2.5.10_amd64.deb`。

[Clash Verge Rev 发布页](https://github.com/clash-verge-rev/clash-verge-rev/releases/tag/v2.5.10)

### Cage 首次安装

先在 Cage 工作台创建或解锁本地账户。在应用菜单打开 **Claude Cage · 代理设置**。如果 Cage 没有节点，可以复制 Clash Verge 当前配置中的节点；选择节点后，工具会验证代理已启动，再返回工作台安装。复制的是本地快照。

应用菜单中的“本机终端”（Host Terminal）打开独立的宿主机 shell。Ctrl+Alt+T 仍打开默认的 Cage 终端。

在系统托盘展开已连接的 Wi-Fi，点击“属性”查看当前 IP、网关和 DNS，或进入网络连接编辑器。
