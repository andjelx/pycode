#!/usr/bin/env python3
import argparse
import sys

import boto3
import docker
import urllib.request

# Image to use for containers
IMAGE_NAME = 'dynamodb'
SECURITY_GROUP = 'sg-a27e2fde'
DB_HOSTNAME = 'ec2-54-175-103-254.compute-1.amazonaws.com'
DB_LOCAL_PORT = '8000/tcp'


def get_containers(client, container_name):
    """
    :return: Running containers list by name
    :param container_name: Container name to search
    :param client: Docker client
    """
    return [
        container for container in client.containers.list(all=True)
        if container.name == container_name
    ]


def main():
    # Get command-line arguments.
    parser = argparse.ArgumentParser(description="Create DynamoDB instance")

    parser.add_argument("--external_ip", required=False)
    arguments = parser.parse_args()

    # Getting current user information
    iam = boto3.resource("iam")
    user = iam.CurrentUser()
    user_name = user.user_name
    container_name = 'dynamodb-{}'.format(user_name)

    client = docker.from_env()
    containers = get_containers(client, container_name)
    if containers:
        container = containers[0]
        # Container exists - starting
        if container.status != 'running':
            print('Starting container: {}'.format(container.name))
            container.start()
    else:
        # Container not exists - running new one
        print('Creating container: {}'.format(container_name))
        client.containers.run(IMAGE_NAME,
                              detach=True,
                              name=container_name,
                              ports={DB_LOCAL_PORT: None})

    container = get_containers(client, container_name)[0]
    external_port = int(container.attrs['NetworkSettings']['Ports'][
        DB_LOCAL_PORT][0]['HostPort'])

    print("Instance started on port {}".format(external_port))
    print("Your endpoint url is: http://{}:{}/".format(DB_HOSTNAME,
                                                       external_port))

    # Hack to get clients external IP if not supplied
    external_ip = arguments.external_ip if arguments.external_ip else \
        urllib.request.urlopen('https://ident.me').read().decode('utf8')
    if not external_ip:
        print("Can't detect external IP. Please supply it via commandline")
        return 1

    print("Your external IP is {}".format(external_ip))

    ec2 = boto3.resource('ec2')
    security_group = ec2.SecurityGroup(SECURITY_GROUP)
    # Adding port
    permission = [
        port_item for port_item in security_group.ip_permissions
        if port_item['FromPort'] == external_port
    ]
    if permission:
        for ip in permission[0]['IpRanges']:
            if ip['CidrIp'].split('/')[0] != str(external_ip):
                # Dropping all others access
                print('Removing old records and adding new one for ip {}'.
                      format(external_ip))
                security_group.revoke_ingress(
                    IpProtocol="tcp",
                    CidrIp=ip['CidrIp'],
                    FromPort=external_port,
                    ToPort=external_port)
                security_group.authorize_ingress(
                    IpProtocol="tcp",
                    CidrIp="{}/32".format(external_ip),
                    FromPort=external_port,
                    ToPort=external_port)
    else:
        # Port access never being granted
        security_group.authorize_ingress(
            IpProtocol="tcp",
            CidrIp="{}/32".format(external_ip),
            FromPort=external_port,
            ToPort=external_port)

    return 0


if __name__ == "__main__":
    sys.exit(main())
