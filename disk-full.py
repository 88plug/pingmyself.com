import requests
import time
import re
import subprocess
import socket

def send_pushover_notification(app_token, user_key, message):
    url = "https://api.pushover.net/1/messages.json"
    data = {
        "token": app_token,
        "user": user_key,
        "message": message
    }
    response = requests.post(url, data=data)
    return response.status_code, response.json()

def get_disk_usage(disk_path):
    try:
        output = subprocess.check_output(["df", "-h", disk_path]).decode("utf-8")
        lines = output.split("\n")
        if len(lines) >= 2:
            fields = lines[1].split()
            if len(fields) >= 5:
                percent_used = float(fields[4].rstrip("%"))
                return percent_used
        print(f"Debugging: Unable to parse df output for {disk_path}.")
        return None
    except subprocess.CalledProcessError:
        print(f"Debugging: Disk path {disk_path} not found.")
        return None

def get_disk_info(disk_path):
    try:
        blkid_output = subprocess.check_output(["blkid", disk_path]).decode("utf-8").strip()
        fstab_output = subprocess.check_output(["cat", "/etc/fstab"]).decode("utf-8")
        fdisk_output = subprocess.check_output(["fdisk", "-l", disk_path]).decode("utf-8")

        disk_info = f"blkid: {blkid_output}\n\n"
        disk_info += f"/etc/fstab:\n{fstab_output}\n\n"
        disk_info += f"fdisk -l {disk_path}:\n{fdisk_output}"

        return disk_info
    except subprocess.CalledProcessError as e:
        print(f"Debugging: Error occurred while getting disk information for {disk_path}: {str(e)}")
        return None

def get_public_ip():
    try:
        command = "ifconfig | grep inet | cut -d: -f2 | awk '{print $2}' | grep -v -E \"^127\\.|^172\\.|^192\\.168\\.|^10\\.\" | xargs"
        output = subprocess.check_output(command, shell=True).decode("utf-8").strip()
        if output:
            return output
        else:
            print("Debugging: No public IP address found.")
            return None
    except subprocess.CalledProcessError as e:
        print(f"Debugging: Error occurred while getting public IP address: {str(e)}")
        return None

def get_location(ip_address):
    try:
        url = f"https://ipapi.co/{ip_address}/json/"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        city = data.get("city", "Unknown")
        region = data.get("region", "Unknown")
        country = data.get("country_name", "Unknown")
        return f"{city}, {region}, {country}"
    except requests.exceptions.RequestException as e:
        print(f"Debugging: Error occurred while getting location for {ip_address}: {str(e)}")
        return "Unknown"

def parse_time(time_str):
    units = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400, 'y': 31536000}
    match = re.match(r"(\d+)([smhdy])", time_str)
    if not match:
        raise ValueError("Invalid time format")
    value, unit = match.groups()
    return int(value) * units[unit]

def monitor_disk_usage(disk_path, interval_str, threshold, nag_interval_str, app_token, user_key):
    interval = parse_time(interval_str)
    nag_interval = parse_time(nag_interval_str)
    last_nag_time = 0
    last_status_above_threshold = False

    hostname = socket.gethostname()
    ip_address = get_public_ip()
    location = get_location(ip_address)

    while True:
        usage_percent = get_disk_usage(disk_path)
        disk_info = get_disk_info(disk_path)

        if usage_percent is None or disk_info is None:
            print(f"Debugging: Skipping monitoring for {disk_path} as an error occurred.")
            time.sleep(interval)
            continue

        current_time = time.time()
        print(f"Debugging: Current disk usage for {disk_path}: {usage_percent:.2f}%")

        if usage_percent > threshold:
            if not last_status_above_threshold:
                message = f"Disk Usage Warning!\n\nHostname: {hostname}\nIP Address: {ip_address}\nLocation: {location}\n\nDisk: {disk_path}\nUsage: {usage_percent:.2f}%\n\nPlease take action to free up disk space."
                status_code, response = send_pushover_notification(app_token, user_key, message)
                print(f"Debugging: Notification sent. Status code: {status_code}, Response: {response}")
                last_nag_time = current_time
                last_status_above_threshold = True
            elif current_time - last_nag_time >= nag_interval:
                message = f"Reminder: Disk usage on {disk_path} is still above {threshold}% at {usage_percent:.2f}% capacity.\n\nHostname: {hostname}\nIP Address: {ip_address}\nLocation: {location}"
                status_code, response = send_pushover_notification(app_token, user_key, message)
                print(f"Debugging: Reminder notification sent. Status code: {status_code}, Response: {response}")
                last_nag_time = current_time
        else:
            if last_status_above_threshold:
                message = f"Disk usage on {disk_path} is back to normal ({usage_percent:.2f}%).\n\nHostname: {hostname}\nIP Address: {ip_address}\nLocation: {location}"
                status_code, response = send_pushover_notification(app_token, user_key, message)
                print(f"Debugging: Issue resolved notification sent. Status code: {status_code}, Response: {response}")
                last_status_above_threshold = False

        time.sleep(interval)

if __name__ == "__main__":
    # This is just an example. In a real case, ensure to pass secure app_token and user_key.
    monitor_disk_usage('/dev/sda1', '15s', 15, '1h', 'your_app_token', 'your_user_key')
    # drive to monitor, monitor interval, % full threshold, nag timer - to notify again.
