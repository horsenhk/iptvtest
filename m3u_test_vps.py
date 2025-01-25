import requests
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

# 输入和输出文件路径
input_file = "input.m3u"
output_file = "output.m3u"
error_log_file = "log.txt"

# 读取 .m3u 文件中的播放列表
def read_m3u_playlist(file_path):
    playlist = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 使用正则表达式解析 M3U 文件
        pattern = re.compile(r'#EXTINF:(.*?)(?: tvg-logo="(.*?)")?(?: group-title="(.*?)")?,(.*?)\n(.*?)\n', re.DOTALL)
        matches = pattern.findall(content)

        for match in matches:
            duration, logo, group, channel_name, url = match
            playlist.append({'duration': duration, 'logo': logo, 'group': group, 'channel_name': channel_name, 'url': url.strip()})
    except FileNotFoundError:
        print(f"Error: File not found - {file_path}")
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
    return playlist

# 测试直播源是否有效
def is_channel_live(item):
    url = item['url']
    try:
        response = requests.get(url, stream=True, timeout=10)  # 增加超时
        if response.status_code == 200:
            try:
                content = next(response.iter_content(1024 * 1))  # 尝试读取更多内容
                if content:
                    return item
            except StopIteration:
                return None
        return None
    except requests.RequestException as e:
        # 记录详细的异常信息
        with open(error_log_file, "a") as log_file:
            log_file.write(f"Error testing URL {url}\n")
        return None
    finally:
        if 'response' in locals():
            response.close()

# 写入有效直播源到 .m3u 文件
def write_to_file(item, output_file):
    with open(output_file, "a", encoding="utf-8") as f:
        f.write(f"#EXTINF:{item['duration']} tvg-logo=\"{item['logo']}\" group-title=\"{item['group']}\",{item['channel_name']}\n")
        f.write(f"{item['url']}\n")

# 主函数
if __name__ == "__main__":
    start_time = time.time()

    # 清空 error_log_file
    with open(error_log_file, "w") as log_file:
        log_file.write("")

    # 读取 .m3u 文件
    playlist = read_m3u_playlist(input_file)

    if not playlist:
        exit()

    # 初始化输出文件
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")

    # 使用多线程检查直播源状态
    with ThreadPoolExecutor(max_workers=50) as executor:
        future_to_url = {executor.submit(is_channel_live, item): item for item in playlist}
        for future in as_completed(future_to_url):
            item = future.result()
            if item:
                write_to_file(item, output_file)

    # 如果需要记录时间，可以使用日志记录而不是打印
    # end_time = time.time()
    # duration = end_time - start_time
    # with open("log.txt", "a") as log_file:
    #     log_file.write(f"Finished testing {len(playlist)} sources in {duration:.2f} seconds.\n")
