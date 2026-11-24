import ipaddress
import re
from urllib.parse import quote, unquote, urlsplit

import json
import subprocess
from pathlib import Path
from datetime import datetime
from ipaddress import IPv4Network


def address_fields(dev, tr):
    fields = []
    if hardware := dev.get_hw_address():
        fields.append((tr("物理地址", "Physical address"), hardware))
    active = dev.get_active_connection()
    profile = active.get_connection() if active else None
    methods = {"auto": tr("自动", "Automatic"), "manual": tr("手动", "Manual"),
               "disabled": tr("已禁用", "Disabled"), "ignore": tr("忽略", "Ignored"),
               "link-local": tr("仅本地链路", "Link-local only"), "shared": tr("共享", "Shared"),
               "dhcp": "DHCP"}
    for family, config in [("IPv4", dev.get_ip4_config()), ("IPv6", dev.get_ip6_config())]:
        setting = profile.get_setting_by_name(family.lower()) if profile else None
        method = setting.get_method() if setting else None
        if method:
            fields.append((family + tr(" 配置方式", " configuration"), methods.get(method, method)))
        waiting = tr("等待分配", "Awaiting assignment") if method in ("auto", "dhcp") else "—"
        if config:
            addresses = config.get_addresses()
            fields.append((family, "\n".join(f"{a.get_address()}/{a.get_prefix()}" for a in addresses) or waiting))
            if family == "IPv4" and addresses:
                masks = [str(IPv4Network((0, a.get_prefix())).netmask) for a in addresses]
                fields.append((tr("IPv4 子网掩码", "IPv4 subnet mask"), "\n".join(masks)))
            fields.extend([(family + tr(" 网关", " gateway"), config.get_gateway() or "—"),
                           (family + " DNS", "\n".join(config.get_nameservers()) or "—")])
        elif method in ("auto", "dhcp"):
            fields.append((family, waiting))
    dhcp = dev.get_dhcp4_config()
    if dhcp:
        if server := dhcp.get_one_option("dhcp_server_identifier"):
            fields.append((tr("DHCP 服务器", "DHCP server"), server))
        expiry = dhcp.get_one_option("expiry")
        if expiry:
            try:
                end = datetime.fromtimestamp(int(expiry)).astimezone()
            except (OSError, ValueError, OverflowError):
                pass
            else:
                fields.append((tr("租约到期时间", "Lease expires"), end.strftime("%Y-%m-%d %H:%M:%S %Z")))
    return fields


def lan_addresses():
    try:
        output = subprocess.check_output(["ip", "-j",
                                          "address", "show", "up", "scope", "global"],
                                         text=True, timeout=2)
        adapters = json.loads(output)
    except (OSError, subprocess.SubprocessError, ValueError):
        return
    for adapter in adapters:
        interface = adapter["ifname"]
        if not (Path("/sys/class/net") / interface / "device").exists():
            continue
        for info in adapter.get("addr_info", []):
            if info.get("family") in ("inet", "inet6") and not any(
                    info.get(flag) for flag in ("tentative", "dadfailed", "deprecated")):
                yield interface, info["local"]


def windows_location(uri):
    try:
        parts = urlsplit(uri)
        host = parts.hostname
        if (parts.scheme != "smb" or not host or parts.port not in (None, 445)
                or parts.query or parts.fragment):
            return None
        if ":" in host:
            # Link-local scope identifiers refer to interfaces on the originating machine.
            if "%" in host or ipaddress.IPv6Address(host).is_link_local:
                return None
            host = ipaddress.IPv6Address(host).compressed.replace(":", "-") + ".ipv6-literal.net"
        path = unquote(parts.path, errors="strict")
        if re.search(r'[\\:*?"<>|\x00-\x1f]', host + path) or re.search(r"%2f", parts.path, re.I):
            return None
        return "\\\\" + host + path.replace("/", "\\")
    except ValueError:
        return None


def smb_uri(text, tr):
    target = text.strip()
    if len(target) >= 2 and target[0] == target[-1] == '"':
        target = target[1:-1]
    if target.startswith(("\\\\", "//")):
        host, separator, path = target[2:].replace("\\", "/").partition("/")
        if host.startswith("[") and host.endswith("]"):
            host = f"[{ipaddress.IPv6Address(host[1:-1])}]"
        elif not re.fullmatch(r"[\w.-]+", host) or host in (".", ".."):
            raise ValueError(tr("共享路径中的计算机名无效。", "Invalid computer name in the share path."))
        target = "smb://" + host + separator + quote(path, safe="/")
    elif "://" not in target:
        host, separator, path = target.replace("\\", "/").partition("/")
        if re.fullmatch(r"[\w.-]+", host) and host not in (".", ".."):
            target = "smb://" + host + separator + quote(path, safe="/")
    parsed = urlsplit(target)
    literal_suffix = ".ipv6-literal.net"
    if re.fullmatch(r"[0-9a-f-]+\.ipv6-literal\.net", parsed.netloc, re.I):
        literal = parsed.netloc[:-len(literal_suffix)].replace("-", ":")
        try:
            host = ipaddress.IPv6Address(literal)
        except ValueError:
            pass
        else:
            parsed = parsed._replace(netloc=f"[{host}]")
            target = parsed.geturl()
    try:
        port = parsed.port
    except ValueError:
        raise ValueError(tr("共享地址中的端口无效。", "Invalid port in the share address.")) from None
    if port == 0 or parsed.scheme != "smb" or not parsed.hostname or parsed.password is not None:
        raise ValueError(tr("请输入 SMB 地址或 Windows 共享路径。", "Enter an SMB address or Windows share path."))
    return target
