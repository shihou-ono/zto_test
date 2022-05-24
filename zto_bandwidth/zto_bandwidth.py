from netmiko import ConnectHandler
import textfsm
import time
import subprocess

def measure_drop(net_connect):
  dropped = []
  for i in range(2):
    output = net_connect.send_command("show interfaces ethernet eth1 queue")
    interface_queue_template = open("./vyos_interface_queue.textfsm", "r")
    parser = textfsm.TextFSM(interface_queue_template)
    print(parser.ParseText(output))
    dropped.append(parser.ParseText(output)[1][1])
    time.sleep(3)
  return dropped

def get_initial_policy(net_connect):
  command = "show configuration commands | match 'eth1 traffic-policy in'"
  output = net_connect.send_command(command)
  config_bandwidth_policy_template = open("./vyos_bandwidth_policy.textfsm", "r")
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

  msg = f"is_dropped:{is_dropped},\n" \
  f"current policy:{current_policy},\n" \
  f"current_policy is not max:{bwp.not_max()},\n" \
  f"need to increase bandwidth:{flag}\n"
  print(msg)
  return flag

vyos_router = {
  "device_type": "vyos",
  "host": "10.0.0.2",
  "username": "vyos",
  "password": "vyos",
  "port": 22,
  # "session_log": 'netmiko_session.log'
}

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
  print(output)
  time.sleep(3)
  output = net_connect.commit()
  print(output)
  time.sleep(30)

  current_policy = bwp.next_policy()

  net_connect = ConnectHandler(**vyos_router)
  time.sleep(3)
  flag = set_flag(net_connect, current_policy)
