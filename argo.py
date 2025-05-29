import argparse

def install(uuid_arg=None, port_arg=None, domain_arg=None, token_arg=None):
    if not os.path.exists(str(INSTALL_DIR)):
        os.makedirs(str(INSTALL_DIR), exist_ok=True)

    os.chdir(str(INSTALL_DIR))
    write_debug_log("开始安装过程")

    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "linux":
        if "x86_64" in machine or "amd64" in machine:
            arch = "amd64"
        elif "aarch64" in machine or "arm64" in machine:
            arch = "arm64"
        elif "armv7" in machine:
            arch = "armv7"
        else:
            arch = "amd64"
    else:
        print("不支持的系统类型: {}".format(system))
        sys.exit(1)

    try:
        version_info = http_get("https://api.github.com/repos/SagerNet/sing-box/releases/latest")
        if version_info:
            version_data = json.loads(version_info)
            sbcore = version_data.get("tag_name", "v1.6.0").lstrip("v")
        else:
            sbcore = "1.6.0"
    except:
        sbcore = "1.6.0"

    singbox_path = str(INSTALL_DIR / "sing-box")
    if not os.path.exists(singbox_path):
        sbname = f"sing-box-{sbcore}-linux-{arch}"
        singbox_url = f"https://github.com/SagerNet/sing-box/releases/download/v{sbcore}/{sbname}.tar.gz"
        tar_path = str(INSTALL_DIR / "sing-box.tar.gz")

        if not download_file(singbox_url, tar_path):
            backup_url = f"https://github.91chi.fun/https://github.com//SagerNet/sing-box/releases/download/v{sbcore}/{sbname}.tar.gz"
            if not download_file(backup_url, tar_path):
                print("sing-box 下载失败")
                sys.exit(1)

        import tarfile
        with tarfile.open(tar_path) as tar:
            tar.extractall(path=str(INSTALL_DIR))
        shutil.move(str(INSTALL_DIR / sbname / "sing-box"), singbox_path)
        shutil.rmtree(str(INSTALL_DIR / sbname))
        os.remove(tar_path)
        os.chmod(singbox_path, 0o755)

    cloudflared_path = str(INSTALL_DIR / "cloudflared")
    if not os.path.exists(cloudflared_path):
        cloudflared_url = f"https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-{arch}"
        if not download_binary("cloudflared", cloudflared_url, cloudflared_path):
            backup_url = f"https://github.91chi.fun/https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-{arch}"
            if not download_binary("cloudflared", backup_url, cloudflared_path):
                print("cloudflared 下载失败")
                sys.exit(1)

    uuid_str = uuid_arg if uuid_arg else str(uuid.uuid4())
    port_vm_ws = port_arg if port_arg else 8001

    config_data = {
        "uuid_str": uuid_str,
        "port_vm_ws": port_vm_ws,
        "install_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    with open(str(CONFIG_FILE), 'w') as f:
        json.dump(config_data, f, indent=2)

    create_sing_box_config(port_vm_ws, uuid_str)

    # 根据参数创建 cloudflared 启动脚本
    cf_start_script = INSTALL_DIR / "start_cf.sh"
    if domain_arg and token_arg:
        # 固定域名方式
        with open(str(cf_start_script), 'w') as f:
            f.write(f'''#!/bin/bash
cd {INSTALL_DIR}
./cloudflared tunnel --url http://localhost:{port_vm_ws}/ --no-autoupdate run --token {token_arg} > argo.log 2>&1 & echo $! > sbargopid.log
''')
    else:
        # 临时域名方式
        with open(str(cf_start_script), 'w') as f:
            f.write(f'''#!/bin/bash
cd {INSTALL_DIR}
./cloudflared tunnel --url http://localhost:{port_vm_ws}/ --edge-ip-version auto --no-autoupdate --protocol http2 > argo.log 2>&1 & echo $! > sbargopid.log
''')
    os.chmod(str(cf_start_script), 0o755)

    create_startup_script(port_vm_ws)
    setup_autostart()
    start_services()

    if domain_arg and token_arg:
        b64 = generate_links(domain_arg, port_vm_ws, uuid_str)
        print(b64)
    else:
        domain = get_tunnel_domain()
        if domain:
            b64 = generate_links(domain, port_vm_ws, uuid_str)
            print(b64)
        else:
            print("无法获取tunnel域名")
            sys.exit(1)

# 修改 main 增加参数解析
def main():
    print_info()

    parser = argparse.ArgumentParser()
    parser.add_argument("action", nargs="?", default="install")
    parser.add_argument("--uuid", help="指定UUID")
    parser.add_argument("--port", type=int, help="指定VMess端口")
    parser.add_argument("--domain", help="指定Argo固定域名")
    parser.add_argument("--token", help="指定Argo固定域名Token")
    args = parser.parse_args()

    if args.action == "install":
        install(uuid_arg=args.uuid, port_arg=args.port, domain_arg=args.domain, token_arg=args.token)
    elif args.action in ["del", "uninstall"]:
        uninstall()
    elif args.action == "status":
        check_status()
    elif args.action == "cat":
        all_nodes_file = INSTALL_DIR / "allnodes.txt"
        if all_nodes_file.exists():
            print(all_nodes_file.read_text())
        else:
            print("节点列表不存在，请先安装")
    else:
        print(f"未知命令: {args.action}")
        print_usage()

if __name__ == "__main__":
    main()
