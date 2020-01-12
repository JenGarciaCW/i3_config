#!/usr/bin/env python
# -*- coding: utf-8 -*-

import subprocess
import time
import calendar
import json
import re
from datetime import datetime


normal_background = '#121212'
normal_color = '#FFFFFF'
set_background = '#FFDE03'
set_color = '#000000'
warn_background = '#FF6F00'
warn_color = '#000000'
danger_background = '#B00020'
danger_color = '#FAFAFA'

def parse_sensors():
    sensors_lines = subprocess.check_output('sensors', shell=True).splitlines()
    sensors_dict = dict()
    for line in sensors_lines:
        if 'Physical' in line:
            temp_regex = r'^\s*Physical.*:\s+\+(\d+.\d+).*\s+\(high\s+=\s+\+(\d+.\d+).*,\s+crit\s+=\s+\+?(\d+.\d+).*\)'
            result = re.match(temp_regex, line)
            if result:
                sensors_dict['temp'] = int(float(result.group(1)))
                sensors_dict['high'] = int(float(result.group(2)))
                sensors_dict['crit'] = int(float(result.group(3)))
                result.groups()
        elif 'fan' in line:
            fan_regex = r'fan\d+:\s+(\d+\s+RPM)'
            result = re.match(fan_regex, line)
            if result:
                sensors_dict['fan'] = result.group(1)
    return sensors_dict

def parse_mem(line, mem_str):
    mem_regex = r'^\s*{}:\s+(\d+)\s+(\d+)\s+(\d+).*$'.format(mem_str)
    result = re.match(mem_regex, line)
    ret_dict = dict()
    if result:
        ret_dict['total'] = float(result.group(1))
        ret_dict['used'] = float(result.group(2))
        ret_dict['free'] = float(result.group(3))
        ret_dict['free_percentage'] = round(ret_dict['free'] / ret_dict['total'] * 100, 1)
    return ret_dict

def parse_ifconfig(interface):
    ifconfig_lines = subprocess.check_output('/sbin/ifconfig {}'.format(interface), shell=True).splitlines()
    ifconfig_dict = {"status": False}
    for line in ifconfig_lines:
        if 'flags' in line:
            flags_regex = r'^[^\s]*:\s+flags=\d+<(.*)>\s.*$'
            result = re.match(flags_regex, line)
            if result:
                if 'RUNNING' in result.group(1):
                    ifconfig_dict["status"] = True

        elif ('inet' in line) and (ifconfig_dict["status"]):
            ip_regex = r'^\s+inet (\d+.\d+.\d+.\d+).*$'
            result = re.match(ip_regex, line)
            if result:
                ifconfig_dict['ip'] = result.group(1)

        elif ('packets' in line) and (ifconfig_dict["status"]):
            status_regex = r'^\s+(.X)\s+packets\s+(\d+).*\((\d+.\d\s.*)\).*$'
            result = re.match(status_regex, line)
            if result:
                ifconfig_dict[result.group(1)] = {"packets": result.group(2), "bytes": result.group(3)}

    return ifconfig_dict

def parse_leds():
    pass

def parse_hdd():
    df_lines = subprocess.check_output('df', shell=True).splitlines()
    df_dict = dict()
    for line in df_lines:
        if '/dev/' in line:
            temp_regex = r'\/dev.*?\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+%)\s(\/\w*)\s*$'
            result = re.match(temp_regex, line)
            if result:
                if result.group(5) is '/':
                    key = 'root'
                elif 'home' in result.group(5):
                    key = 'home'
                else:
                    key = None
                one_gig = 1024.0*1024.0
                if key:
                    df_dict[key] = {
                        "blocks": round(int(result.group(1))/one_gig, 2),
                        "used": round(int(result.group(2))/one_gig, 2),
                        "available": round(int(result.group(3))/one_gig, 2),
                        "use": result.group(4)
                    }

    return df_dict               #sensors_dict['temp'] = result.group(1)


def get_value(key, line):
    element_regex = r'^\s+{}:\s+(.+)\s*$'.format(key)
    result = re.match(element_regex, line)
    if result:
        return result.group(1)

def parse_bat():
    bat_lines = subprocess.check_output('upower -i /org/freedesktop/UPower/devices/battery_BAT0', shell=True).splitlines()
    bat_data = dict()
    for line in bat_lines:
        if 'state' in line:
            bat_data['state'] = get_value('state', line)
        elif 'capacity' in line:
            bat_data['capacity'] = float(get_value('capacity', line).replace('%', ''))
        elif 'energy:' in line:
            bat_data['energy'] = float(get_value('energy', line).replace('Wh', ''))
        elif 'energy-full:' in line:
            bat_data['energy-full'] = float(get_value('energy-full', line).replace('Wh', ''))
        elif 'energy-rate:' in line:
            bat_data['energy-rate'] = float(get_value('energy-rate', line).replace('W', ''))
    return bat_data

def get_caps_status(leds_dict):
    caps_status_dict = {
        "name": "caps",
        "full_text": " CAPS ",
        "short_text": " CAPS ",
        "separator": True
    }
    try:
        # Check led array in string 1 is set 0 is unset
        led_mask_regex = r'([0-9]{8})[\s]*$'
        xset_string = subprocess.check_output('xset q | grep LED', shell=True)
        led_mask = re.search(led_mask_regex, xset_string)
        # block num 0x2

        caps_key = bool(int(led_mask.group(1)) & 1)


        if caps_key:
            caps_status_dict["color"] = set_color
            caps_status_dict["background"] = set_background
        else:
            caps_status_dict["color"] = normal_color
            caps_status_dict["background"] = normal_background
    except Exception as e:
        caps_status_dict["full_text"] = " CAPS_E "
        caps_status_dict["short_text"] = "CAPS_E"
        caps_status_dict["color"] = danger_color
        caps_status_dict["background"] = danger_background

    return caps_status_dict


def get_num_status(leds_dict):
    num_status_dict = {
        "name": "num",
        "full_text": " NUM ",
        "short_text": " NUM ",
        "separator": True
    }
    # Check led array in string 1 is set 0 is unset
    led_mask_regex = r'([0-9]{8})[\s]*$'
    xset_string = subprocess.check_output('xset q | grep LED', shell=True)
    led_mask = re.search(led_mask_regex, xset_string)
    # block num 0x2

    num_key = bool(int(led_mask.group(1)) & 0x2)

    if num_key:
        num_status_dict["color"] = set_color
        num_status_dict["background"] = set_background
    else:
        num_status_dict["color"] = normal_color
        num_status_dict["background"] = normal_background

    return num_status_dict



def get_scroll_status(leds_dict):
    scroll_status_dict = {
        "name": "num",
        "full_text": " NUM ",
        "short_text": "NUM",
        "separator": True
    }
    scroll_status_dict["background"] = normal_background

    return scroll_status_dict


def get_net_status(interface):

    if interface.lower().startswith('e'):
        interface = 'enp0s25'
        iface_str = 'E'
    elif interface.lower().startswith('w'):
        interface = 'wlp3s0'
        iface_str = 'W'

    iface_status = parse_ifconfig(interface)

    if iface_status['status']:
        iface_str = '{}: ({})'.format(iface_str, iface_status['ip'])
    else:
        iface_str = '{}: {}'.format(iface_str, 'OFF')

    iface_status_dict = {
        "full_text": iface_str,
        "short_text": iface_str,
        "color": normal_color,
        "background": normal_background,
        "name": "{}_iface".format(interface),
        "separator": True,
    }
    return iface_status_dict

def get_mem_status():
    free_lines = subprocess.check_output('free', shell=True).splitlines()
    free_dict = dict()
    for line in free_lines:
        if 'Mem' in line:
            free_dict['mem'] = parse_mem(line, 'Mem')
        elif 'Swap' in line:
            free_dict['swap'] = parse_mem(line, 'Swap')

    mem_str = "MM {}Gb {}%".format(round(free_dict['mem']['free']/1024.0/1024.0, 2), free_dict['mem']['free_percentage'])
    if free_dict['swap']['used'] > 0 :
        mem_str += " SW {}Gb {}%".format(round(free_dict['swap']['free']/1024.0/1024.0, 2), free_dict['swap']['free_percentage'])
    mem_status_dict = {
    "full_text": mem_str,
    "short_text": mem_str,
    "color": normal_color,
    "background": normal_background,
    "name": "memory",
    "separator": True,
}
    return mem_status_dict

def get_hdd_status(in_dir, hdd_data):
    data_dict = hdd_data[in_dir]
    hdd_color = normal_color
    hdd_back = normal_background
    available_percentage = round(data_dict['available'] / data_dict['blocks'] * 100, 0)

    if data_dict['available'] < 5 or available_percentage < 30:
        hdd_color = warn_color
        hdd_back = warn_background
    elif data_dict['available'] < 3 or available_percentage < 10:
        hdd_color = danger_color
        hdd_back = danger_background

    home_status_dict = {
        "full_text": " /{} {}Gb {}% ".format(in_dir, data_dict['available'], available_percentage),
        "short_text": "/{} {}Gb ".format(in_dir, data_dict['available']),
        "color": hdd_color,
        "background": hdd_back,
        "name": "{}_hhd".format(in_dir),
        "separator": True,
    }
    return home_status_dict

def get_cpu_temp_status():
    sensors_data = parse_sensors()
    temp_color = normal_color
    temp_back = normal_background

    if sensors_data['temp'] > sensors_data['high']:
        temp_color = warn_color
        temp_back = warn_background
    if sensors_data['temp'] > sensors_data['crit']:
        temp_color = danger_background
        temp_back = danger_background
    temp_status_dict = {
        "full_text": " {}[C] {} ".format(sensors_data['temp'], sensors_data['fan']),
        "short_text": " {}[C] ".format(sensors_data['temp']),
        "color": temp_color,
        "background": temp_back,
        "name": "cpu_temp",
        "separator": True,
    }

    return temp_status_dict

def get_batt_status():
    bat_data = parse_bat()
    percentage = bat_data['energy']/bat_data['energy-full']*bat_data['capacity']
    bat_color = normal_color
    bat_back = normal_background
    time = 0

    if 'discharging' in bat_data['state']:

        status = 'BAT'
        if bat_data['energy-rate'] != 0:
            time = bat_data['energy'] / bat_data['energy-rate']
        if time < 1 and time >= 0.5:
            bat_color = warn_color
            bat_back = warn_background
        elif time < 0.5:
            bat_color = danger_color
            bat_back = danger_background

    else:
        status = 'CHR'
        if bat_data['energy-rate'] != 0:
            time = (bat_data['energy-full'] - bat_data['energy'])/bat_data['energy-rate']

    hours = int(time)
    minutes = int((time * 60) % 60)
    seconds = int((time * 3600) % 60)

    bat_status_dict = {
        "full_text": " %s %0.2f%c %02d:%02d:%02d " % (status, round(percentage, 2), '%', hours, minutes, seconds),
        "short_text": " %s %d%c %02d:%02d " % (status[0], int(percentage), '%', hours, minutes),
        "color": bat_color,
        "background": bat_back,
        "name": "battery",
        "separator": True,
    }
    return bat_status_dict

def get_date(now):
    date = " {} {}, {} ".format(calendar.month_abbr[now.month], now.day, now.year)
    short_date = " {}/{}/{} ".format(now.day, now.month, str(now.year)[2:])

    date_dict = {
        "full_text": date,
        "short_text": short_date,
        "color": normal_color,
        "background": normal_background,
        "name": "date",
        "separator": True,
    }

    return date_dict

def get_hour(now):
    hour = now.strftime(' %I:%M:%S %p ')
    short_hour = now.strftime(' %H:%M ')
    hour_dict = {
        "full_text": hour,
        "short_text": short_hour,
        "color": normal_color,
        "background": normal_background,
        "name": "hour",
        "separator": True,
    }

    return hour_dict


def main():
    print '{ "version": 1 }'
    print '['
    print '[]'
    while True:
        now = datetime.now()
        hdd_data = parse_hdd()
        status_list = list()
        status_list.append(get_caps_status(""))
        status_list.append(get_num_status(""))
        status_list.append(get_net_status('wifi'))
        status_list.append(get_net_status('ethernet'))
        status_list.append(get_hdd_status('home', hdd_data))
        status_list.append(get_hdd_status('root', hdd_data))
        status_list.append(get_mem_status())
        status_list.append(get_cpu_temp_status())
        status_list.append(get_batt_status())
        status_list.append(get_date(now))
        status_list.append(get_hour(now))
        print ',{}'.format(json.dumps(status_list))
        time.sleep(1)


if __name__ == '__main__':
    main()
