import requests
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

# 输入和输出文件路径
input_file = "input.m3u"  # 原始 .m3u 文件
output_file = "output.m3u"  # 有效的直播源保存到此文件
error_log_file = "log.txt"  # 异常日志文件

# 读取 .m3u 文件中的播放列表
def read_m3u(file_path):
    playlist = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # 确保第一行为 #EXTM3U
        if not lines or not lines[0].startswith("#EXTM3U"):
            raise ValueError("Invalid M3U file format")

        # 解析 .m3u 文件，忽略空行和无效行
        for i in range(1, len(lines) - 1):  # 从第二行开始处理
            if lines[i].startswith("#EXTINF") and (i + 1 < len(lines)) and lines[i + 1].startswith("http"):
                playlist.append((lines[i].strip(), lines[i + 1].strip()))  # 保存 (描述, URL)
    except Exception as e:
        with open(error_log_file, "a") as log_file:
            log_file.write(f"Error reading file {file_path}: {e}\n")
    return playlist

# 测试直播源是否有效（无代理和有代理两次测试）
def is_channel_live(url, proxy_url=None):
    try:
        # 测试直播源有效性
        proxies = None
        if proxy_url:
            proxies = {
                "http": proxy_url,
                "https": proxy_url,
            }
        response = requests.get(url, stream=True, timeout=10, proxies=proxies)
        if response.status_code == 200:
            try:
                content = next(response.iter_content(1024 * 1))  # 尝试读取更多内容
                if content:
                    return True
            except StopIteration:
                return False
        return False
    except requests.RequestException as e:
        # 记录详细的异常信息
        with open(error_log_file, "a") as log_file:
            log_file.write(f"Error testing URL {url}\n")
        return False
    finally:
        if 'response' in locals():
            response.close()

# 保存单个直播源到输出文件
def append_to_file(extinf, url, output_file):
    try:
        with open(output_file, "a", encoding="utf-8") as f:  # 使用 "a" 模式追加内容
            f.write(extinf + "\n")
            f.write(url + "\n")
    except Exception as e:
        with open(error_log_file, "a") as log_file:
            log_file.write(f"Error writing to file {output_file}: {e}\n")

# 主函数
if __name__ == "__main__":
    start_time = time.time()

    # 清空 error_log_file
    with open(error_log_file, "w") as log_file:
        log_file.write("")

    # 读取 .m3u 文件
    playlist = read_m3u(input_file)
    if len(playlist) == 0:
        exit()

    # 初始化输出文件，确保文件头正确
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")

    proxy_url = "socks5://127.0.0.1:1081"  # 替换为你的代理信息

    # 使用多线程检查直播源状态
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = []
        for extinf, url in playlist:
            futures.append((extinf, url, executor.submit(is_channel_live, url, None), executor.submit(is_channel_live, url, proxy_url)))

        for extinf, url, future_no_proxy, future_proxy in futures:
            try:
                if future_no_proxy.result() or future_proxy.result():  # 无代理或有代理测试成功
                    append_to_file(extinf, url, output_file)
            except Exception as e:
                with open(error_log_file, "a") as log_file:
                    log_file.write(f"Error processing URL {url}: {e}\n")

    # 如果需要记录时间，可以使用日志记录而不是打印
    # end_time = time.time()
    # duration = end_time - start_time
    # with open("log.txt", "a") as log_file:
    #     log_file.write(f"Finished testing {len(playlist)} sources in {duration:.2f} seconds.\n")