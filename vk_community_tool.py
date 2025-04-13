import vk_api
from vk_api.exceptions import VkApiError, Captcha
import time
from datetime import datetime
import webbrowser
import json
import os

''' Settings '''
TOKEN = "" # your VK API token
SOURCE_USER_ID = 0 # ID of source page (11111111 for example)
LOG_FILE = "vk_group_transfer.log"
GROUPS_FILE = "source_groups.json"
SUBS_CACHE_FILE = "subs_cache.json"
BLOCKED_FILE = "blocked_or_closed_groups.txt"
REQUEST_DELAY = 1.8 # optimal values from 1.5 to 2 
API_VERSION = "5.154"

""" Logging """
def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

""" Timer """
def smart_sleep(multiplier=1.0):
    time.sleep(REQUEST_DELAY * multiplier)

""" Captcha """
def captcha_handler(captcha):
    log(f"Captcha required: {captcha.get_url()}")
    webbrowser.open(captcha.get_url())
    captcha_key = input("Enter captcha: ").strip()
    return captcha.try_again(captcha_key)

""" Authorization """
def auth_vk(token):
    try:
        vk_session = vk_api.VkApi(
            token=token,
            captcha_handler=captcha_handler,
            api_version=API_VERSION
        )
        vk = vk_session.get_api()
        vk.users.get()
        return vk, vk_session
    except Exception as e:
        log(f"Authorization error: {e}")
        return None, None

""" Caching communities to speed up future launches """
def load_cache(filename):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_cache(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(sorted(list(data)), f)

""" Collecting a list of source communities """
def get_all_groups(vk):
    all_groups = []
    offset = 0
    empty_counter = 0
    while True:
        try:
            response = vk.groups.get(
                user_id=SOURCE_USER_ID,
                extended=1,
                fields="is_closed,deactivated,name",
                count=1000,
                offset=offset
            )
            items = response.get("items", [])
            if not items:
                empty_counter += 1
                if empty_counter >= 3:
                    break
                offset += 1000
                continue
            empty_counter = 0
            for g in items:
                group = {
                    "id": g["id"],
                    "name": g.get("name", f"id{g['id']}")
                }
                if not g.get("is_closed", 1) and not g.get("deactivated"):
                    all_groups.append(group)
            offset += 1000
            smart_sleep()
        except Exception as e:
            log(f"Error while collecting communities: {e}")
            break
    with open(GROUPS_FILE, "w", encoding="utf-8") as f:
        json.dump(all_groups, f, ensure_ascii=False, indent=2)
    log(f"Saved {len(all_groups)} opened communities to {GROUPS_FILE}")

""" List of communities that are already subscribed to """
def get_current_subs(vk):
    subs = set()
    offset = 0
    while True:
        try:
            resp = vk.groups.get(extended=0, offset=offset, count=1000)
            items = resp.get("items", [])
            subs.update(map(abs, items))
            if len(items) < 1000:
                break
            offset += 1000
            time.sleep(0.3)
        except Exception as e:
            log(f"Ошибка получения подписок: {e}")
            break
    return subs


""" Join groups """
def join_groups(vk, session, groups, existing_subs):
    success = failed = skipped = 0
    failed_groups = []
    start_time = time.time()

    for i, group in enumerate(groups, 1):
        gid = abs(group["id"])
        name = group["name"]
        if gid in existing_subs:
            skipped += 1
            continue
        try:
            session.method("groups.join", {"group_id": gid})
            existing_subs.add(gid)
            log(f"Success - {name} (id {gid}) - {i}/{len(groups)} communities")
            success += 1
        except VkApiError as e:
            msg = str(e)
            if "Access denied: you are already in this community" not in msg:
                log(f"Failed - {name} (id {gid}) - {msg}, {i}/{len(groups)} communities")
            failed_groups.append(f"{name} (id {gid})")
            failed += 1
            smart_sleep(2)
        except Exception as e:
            log(f"Critical error - {name} (id {gid}) - {e}")
            failed_groups.append(f"{name} (id {gid})")
            failed += 1
            smart_sleep(3)

    # Results
    elapsed_time = time.time() - start_time
    log(f"Completed. Total communities: {len(groups)}")
    log(f"Subscribed successfully: {success}")
    log(f"Skiped (already subscribed or for other reasons): {skipped}")
    log(f"Failed to subscribe: {failed}")
    log(f"Total execution time: {elapsed_time:.2f} seconds")

    # Saving unsuccessful communities
    with open("failed_groups.txt", "w", encoding="utf-8") as f:
        for line in failed_groups:
            f.write(line + "\n")
        f.write(f"\nTotal failed: {failed}, success: {success}\n")


""" Collection of closed communities """
def get_closed(vk):
    result = []
    offset = 0
    empty_counter = 0
    while True:
        try:
            response = vk.groups.get(
                user_id=SOURCE_USER_ID,
                extended=1,
                fields="is_closed,deactivated,name",
                count=1000,
                offset=offset
            )
            items = response.get("items", [])
            if not items:
                empty_counter += 1
                if empty_counter >= 3:
                    break
                offset += 1000
                continue
            empty_counter = 0
            for g in items:
                if g.get("is_closed", 0) or g.get("deactivated"):
                    name = g.get("name", f"id{g['id']}")
                    url = f"https://vk.com/public{g['id']}" if g['id'] > 0 else f"https://vk.com/club{abs(g['id'])}"
                    result.append(f"{name} — {url}")
            offset += 1000
            smart_sleep()
        except Exception as e:
            log(f"Error while collecting closed communities: {e}")
            break
    with open(BLOCKED_FILE, "w", encoding="utf-8") as f:
        for line in result:
            f.write(line + "\n")
    log(f"Saved {len(result)} closed communities to {BLOCKED_FILE}")

def main():
    vk, session = auth_vk(TOKEN)
    if not vk:
        return

    while True:
        print("\n== VK COMMUNITY TOOL ==")
        print("1 — Collect communities to JSON file")
        print("2 — Subscribe to communities from JSON file")
        print("3 — Collect closed communities")
        print("q — Exit")

        choice = input("Your choice: ").strip().lower()
        if choice in {"q", "exit"}:
            print("Exiting...")
            break

        if choice == "1":
            get_all_groups(vk)

        elif choice == "2":
            try:
                with open(GROUPS_FILE, "r", encoding="utf-8") as f:
                    all_groups = json.load(f)
                assert isinstance(all_groups, list) and all("id" in g for g in all_groups)
            except Exception as e:
                log(f"Loading error {GROUPS_FILE}: {e}")
                continue

            total_blocks = len(all_groups) // 1000 + (1 if len(all_groups) % 1000 != 0 else 0)
            print(f"Total available blocks by 1000: {total_blocks}")
            try:
                offset_block = int(input(f"Enter block number (0-{total_blocks - 1}): ").strip())
                if offset_block < 0 or offset_block >= total_blocks:
                    log("Invalid block number!")
                    continue
            except ValueError:
                log("Invalid input format")
                continue

            block = all_groups[offset_block * 1000: (offset_block + 1) * 1000]

            cache = load_cache(SUBS_CACHE_FILE)
            if not cache:
                log("Subscription cache not found, loading...")
                cache = get_current_subs(vk)
                save_cache(SUBS_CACHE_FILE, list(cache))

            join_groups(vk, session, block, cache)
            save_cache(SUBS_CACHE_FILE, list(cache))

        elif choice == "3":
            get_closed(vk)

        else:
            print("Invalid choice. Try again.")

if __name__ == "__main__":
    main()
