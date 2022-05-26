from netmiko import ConnectHandler
import textfsm
import time
import datetime
import fasteners
import sys

def measure_drop(net_connect):
  dropped = []
  dir_path = "/home/ec2-user/yokogushi_contents_team/zto_bandwidth"
  for i in range(2):
    output = net_connect.send_command("show interfaces ethernet eth1 queue")
    interface_queue_template = open(f"{dir_path}/vyos_interface_queue.textfsm", "r")
    parser = textfsm.TextFSM(interface_queue_template)
    dropped.append(parser.ParseText(output)[1][1])
    time.sleep(10)
  return dropped

def get_initial_policy(net_connect):
  command = "show configuration commands | match 'eth1 traffic-policy in'"
  output = net_connect.send_command(command)
  dir_path = "/home/ec2-user/yokogushi_contents_team/zto_bandwidth"
  config_bandwidth_policy_template = open(f"{dir_path}/vyos_bandwidth_policy.textfsm", "r")
  parser = textfsm.TextFSM(config_bandwidth_policy_template)
  return parser.ParseText(output)[0][0]

class BandwidthPolicy:
  def __init__(self, current_policy):
    self.current_policy = current_policy
    self.bandwidth_list = [
      "in_1k",
      "in_50k",
      "in_100k",
      "in_500k",
      "in_1m",
      "in_10m"
    ]

  def current_policy_index(self):
    return self.bandwidth_list.index(self.current_policy)

  def next_policy_index(self):
    return self.current_policy_index() + 1

  def next_policy(self):
    return self.bandwidth_list[self.next_policy_index()]

  def not_max(self):
    return self.current_policy_index() != len(self.bandwidth_list) - 1

def set_flag(net_connect, current_policy = ""):
  if current_policy == "":
    current_policy = get_initial_policy(net_connect)
  bwp = BandwidthPolicy(current_policy)
  dropped = measure_drop(net_connect)
  is_dropped = dropped[0] < dropped[1]

  flag = is_dropped and bwp.not_max()
  dt = datetime.datetime.now()

  msg = \
  "######\n" \
  f"datetime: {dt}\n" \
  "######\n" \
  f"prev_dropped: {dropped[0]},\n" \
  f"current_dropped: {dropped[1]},\n" \
  f"prev_dropped < current_dropped: {is_dropped},\n" \
  f"current policy: {current_policy},\n" \
  f"current_policy is not max: {bwp.not_max()},\n" \
  f"need to increase bandwidth: {flag}\n"

  log_path = "/home/ec2-user/yokogushi_contents_team/zto_bandwidth/log/zto_bandwidth.log"
  with open(log_path, "a") as f:
    f.write(msg)

  return flag

if __name__ == '__main__':
  lock = fasteners.InterProcessLock('/var/tmp/lockfile')

  if not lock.acquire(blocking=False):
    sys.exit()

  vyos_router = {
    "device_type": "vyos",
    "host": "10.0.0.2",
    "username": "vyos",
    "password": "vyos",
    "port": 22,
    # "session_log": 'netmiko_session.log'
  }

  log_path = "/home/ec2-user/yokogushi_contents_team/zto_bandwidth/log/zto_bandwidth.log"

  net_connect = ConnectHandler(**vyos_router)
  time.sleep(3)

  current_policy = get_initial_policy(net_connect)

  flag = set_flag(net_connect, current_policy)

  while flag:
    bwp = BandwidthPolicy(current_policy)
    next_policy = bwp.next_policy()
    config = [
      f"delete traffic-policy limiter {current_policy} description", 
      f"set traffic-policy limiter {next_policy} description current_policy",
      f"set interfaces ethernet eth1 traffic-policy in {next_policy}",
      f"set interfaces ethernet eth2 traffic-policy in {next_policy}"
    ]

    output = net_connect.send_config_set(config, exit_config_mode=False)
    msg = output + "\n"
    time.sleep(3)

    output = net_connect.commit()
    dt = datetime.datetime.now()
    msg = output + f"{output}\n{dt}\n"
    current_policy = bwp.next_policy()

    with open(log_path, "a") as f:
      f.write(msg)

    time.sleep(10)
    net_connect = ConnectHandler(**vyos_router)
    time.sleep(3)
    flag = set_flag(net_connect, current_policy)

  lock.release()
