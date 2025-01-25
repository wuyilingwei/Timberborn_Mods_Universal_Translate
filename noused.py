def get_steam_install_path():
    try:
        reg_path = r"SOFTWARE\WOW6432Node\Valve\Steam"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path) as key:
            install_path, reg_type = winreg.QueryValueEx(key, "InstallPath")
            logger.info(f"Get steam install path from reg: {install_path}")
            steam_path.set(install_path)
            update_config(steam_path, "steam.installPath")
            return None
    except FileNotFoundError:
        logger.error("Steam not found in registry")
        return None
    except Exception as e:
        logger.error(f"Error: {e}")
        return None
    

    
def check_accessibility():
    git_status = "Unknown"
    openai_status = "Unknown"
    steam_status = "Unknown"
    logger.info("Checking accessibility...")
    gitDomain = get_domain(configs["sync"]["API"])
    openaiDomain = get_domain(configs["LLM"]["API"])
    logger.debug(f"Git Source: {gitDomain}")
    logger.debug(f"OpenAI: {openaiDomain}")
    logger.debug(f"Steam: store.steampowered.com")

    # Check Git accessibility
    try:
        response = requests.get(f"https://{gitDomain}", timeout=5, proxies=proxies)
        if response.status_code == 200:
            git_status = "Accessible"
            logger.info(f"Sync: {git_status}")
        else:
            git_status = "Not Accessible"
            logger.info(f"Sync: {git_status}")
            logger.info(f"Response: {response}")
    except requests.RequestException as e:
        git_status = "Not Accessible"
        logger.info(f"Sync: {git_status}")
        logger.info(f"Error: {e}")

    # Check LLM accessibility
    LLMStatus = requestLLM(text="Hello", prompt="Reply me \"Hi\"")
    if LLMStatus["code"] == 200:
        openai_status = "Accessible"
        logger.info(f"LLM: {openai_status}")
    else:
        openai_status = "Not Accessible"
        logger.info(f"LLM: {openai_status}")
        logger.info(f"Response: {LLMStatus}")

    # Check Steam accessibility
    try:
        response = requests.get(f"https://store.steampowered.com", timeout=5, proxies=proxies)
        if response.status_code == 200:
            steam_status = "Accessible"
            logger.info(f"Steam: {steam_status}")
        else:
            steam_status = "Not Accessible"
            logger.info(f"Steam: {steam_status}")
            logger.info(f"Response: {response}")
    except requests.RequestException as e:
        steam_status = "Not Accessible"
        logger.info(f"Steam: {steam_status}")
        logger.info(f"Error: {e}")

    git_label.config(text=f"Sync: {git_status}")
    LLM_label.config(text=f"LLM: {openai_status}")
    steam_label.config(text=f"Steam: {steam_status}")

network_frame = tk.LabelFrame(root, text="API Access", padx=5, pady=5)
network_frame.place(x=10, y=500, width=100, height=180)

git_label = tk.Label(network_frame, text="Sync: Unknown")
git_label.pack(pady=5)

LLM_label = tk.Label(network_frame, text="LLM: Unknown")
LLM_label.pack(pady=5)

steam_label = tk.Label(network_frame, text="Steam: Unknown")
steam_label.pack(pady=5)

check_button = tk.Button(network_frame, text="Try Again", command=check_accessibility)
check_button.pack(pady=10)
"""