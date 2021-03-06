#!/usr/bin/env python 

import subprocess
import sys
import getopt
import fileinput
import re
 

def get_part(line, splitter, index):
    return line.split(splitter)[index]


def parse_terraform_show(path):
    host = {}
    cmd = subprocess.Popen('terraform show %s' % (path), shell=True, stdout=subprocess.PIPE)
    for line in cmd.stdout:
        if 'aws_instance.' in line:
            type = get_part(get_part(line, ':', 0), '.', 1).strip()
            if not type in host:
                host[type] = {}
                if not 'private_dns' in host[type]:
                    host[type]['private_dns'] = []
                if not 'public_ip' in host[type]:
                    host[type]['public_ip'] = []

        if 'private_dns' in line:
            host[type]['private_dns'].append(get_part(line, ' = ', 1).strip())

        if 'public_ip' in line:
            host[type]['public_ip'].append(get_part(line, ' = ', 1).strip())

    print host
    return host


def write_host_to_file(host, type, fo):
    fo.write("[%s]\n" % (type))
    if type in host:
        for i in range(len(host[type]['public_ip'])):
            fo.write("%s-%d ansible_ssh_host=%s\n" % (type, i+1, host[type]['public_ip'][i]))


def write_hosts_file(host, directory):
    filename = '%s/hosts' % (directory)
    fo = open(filename, "wb")

    write_host_to_file(host, 'edge', fo)
    write_host_to_file(host, 'master', fo) 
    write_host_to_file(host, 'slave', fo)

    fo.close()
    return filename


def write_hosts_list(host):
    command = "  command: /tmp/cdh-setup.py --cmhost %s" % (host['master']['private_dns'][0])
    command += " --nodes"
    all_nodes = []
    for type in ['master', 'slave', 'edge']:
        if type in host:
            all_nodes += host[type]['private_dns']

    for node in all_nodes:
        command += " %s" % node

    print command
    
    file = open('roles/cm/tasks/main.yml')
    lines = file.readlines()
    lines = lines[:-1]
    lines.append(command)
    file.close()

    fo = open('roles/cm/tasks/main.yml', "wb")
    fo.write(''.join(lines))
    fo.close()


terraform_dir = '.'
opts, args = getopt.getopt(sys.argv[1:],"i:")
for k, v in opts:
    if k == '-i':
        terraform_dir = v

path = '%s/terraform.tfstate' % terraform_dir
host = parse_terraform_show(path)

if len(host) > 0:
    filename = write_hosts_file(host, terraform_dir)
    write_hosts_list(host)
