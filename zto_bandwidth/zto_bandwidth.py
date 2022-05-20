from netmiko import ConnectHandler
import textfsm
import pprint
import time

def is_dropped(net_connect):
  dropped = []
  for i in range(2):
    output = net_connect.send_command("show interfaces ethernet eth1 queue")
    interface_queue_template = open("./vyos_interface_queue.textfsm", "r")
    parser = textfsm.TextFSM(interface_queue_template)
    dropped.append(parser.ParseText(output)[1][1])
    time.sleep(3)
  return dropped[0] < dropped[1]

def is_max_bandwidth(net_connect):
  output = net_connect.send_command("show configuration commands | match 'eth1 traffic-policy in'")
  config_bandwidth_template = open("./vyos_bandwidth_policy.textfsm", "r")
  parser = textfsm.TextFSM(config_bandwidth_template)
  current_bandwidth = parser.ParseText(output)[0][0]
  print(current_bandwidth)
  return current_bandwidth == "qos_in_10m"


vyos_router = {
  "device_type": "vyos",
  "host": "10.0.0.2",
  "username": "vyos",
  "password": "vyos",
  "port": 22,
  "session_log": 'netmiko_session.log'
}

net_connect = ConnectHandler(**vyos_router)
time.sleep(3)

print(is_max_bandwidth(net_connect))

# while is_dropped(net_connect)) or is_max_bandwidth:
