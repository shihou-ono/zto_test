from netmiko import ConnectHandler
import textfsm
import time
import subprocess

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
      "qos_in_1k",
      "qos_in_50k",
      "qos_in_100k",
      "qos_in_500k",
      "qos_in_1m",
      "qos_in_10m"
    ]

  def current_policy_index(self):
    return self.bandwidth_list.index(self.current_policy)

  def next_policy_index(self):
    return self.current_policy_index() + 1

  def next_policy(self):
    return self.bandwidth_list[self.next_policy_index()]

  def not_max(self):
    return self.current_policy_index() != len(self.bandwidth_list) - 1

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

bwp = BandwidthPolicy(current_policy)
print(bwp.current_policy_index())
print(type(bwp.current_policy_index()))

print(bwp.next_policy_index())
print(type(bwp.next_policy_index()))

print(bwp.next_policy())
print(type(bwp.next_policy()))

print(bwp.not_max())
