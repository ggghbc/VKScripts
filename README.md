# VKScripts
*various useful scripts for vk.com*

## VK Community Tool

A script for automatically transferring community subscriptions from one VK account to another.

### 📌 Features

- Collecting a list of open communities from the specified page  
- Subscribing to communities  
- Captcha handling  
- Subscription caching (faster re-runs)  
- Logging to file  
- Retrieving a list of closed communities

### 🛠️ Installation

0. The script is written in Python 3.13.2

1. Install dependencies:
```bash
pip install vk_api
```

2. Clone the project:
```bash
git clone https://github.com/ggghbc/vkscripts.git
cd vkscripts
```

3. Open `vk_community_tool.py` and set:
```python
TOKEN = "your_token"
SOURCE_USER_ID = 11111111  # ID of the source account
```

### 🚀 Run
```bash
python vk_group_transfer.py
```

### ⚙️ How to get a token

1. Go to: [vkhost.github.io](https://vkhost.github.io/)

2. Select **VK Admin** or **Kate Mobile**, confirm authorization

3. Copy the `access_token` with required permissions (`groups`, `offline`)

4. Paste the token into the `TOKEN` variable as shown above

### 🧠 Notes

- The script works in blocks of 1000 communities (API limit)  
- Logs are saved to `vk_group_transfer.log`  
- Subscription cache is saved in `subs_cache.json`  
- Subscription errors are saved to `failed_groups.txt`  
- Closed/deleted/blocked communities are saved to `blocked_or_closed_groups.txt`

## License

This project is released under [The Unlicense](./LICENSE).
