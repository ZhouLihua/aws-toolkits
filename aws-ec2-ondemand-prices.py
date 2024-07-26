import csv
import json
import re

import boto3


def extract_number_from_string(input_string):
    match = re.search(r'\d+(\.\d+)?', input_string)
    return match.group() if match else None


def get_ec2_prices(region_name,
                   preinstalled_software='NA',
                   tenancy='Shared',
                   is_byol=False,
                   term_type='OnDemand'):
    session = boto3.Session()
    # only three api price endpoints
    # https://api.pricing.us-east-1.amazonaws.com
    # https://api.pricing.eu-central-1.amazonaws.com
    # https://api.pricing.ap-south-1.amazonaws.com
    pricing = session.client('pricing', region_name='ap-south-1')

    if is_byol:
        license_model = 'Bring your own license'
    else:
        license_model = 'No License required'

    if tenancy == 'Host':
        capacity_status = 'AllocatedHost'
    else:
        capacity_status = 'Used'

    prices = {}
    next_token = "NA"
    while True:
        if next_token != "NA":
            response = pricing.get_products(
                ServiceCode='AmazonEC2',
                Filters=[
                    {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': region_name},
                    {'Type': 'TERM_MATCH', 'Field': 'termType', 'Value': term_type},
                    {'Type': 'TERM_MATCH', 'Field': 'capacitystatus', 'Value': capacity_status},
                    {'Type': 'TERM_MATCH', 'Field': 'preInstalledSw', 'Value': preinstalled_software},
                    {'Type': 'TERM_MATCH', 'Field': 'tenancy', 'Value': tenancy},
                    {'Type': 'TERM_MATCH', 'Field': 'licenseModel', 'Value': license_model},
                ],
                MaxResults=100,
                NextToken=next_token
            )
        else:
            response = pricing.get_products(
                ServiceCode='AmazonEC2',
                Filters=[
                    {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': region_name},
                    {'Type': 'TERM_MATCH', 'Field': 'termType', 'Value': term_type},
                    {'Type': 'TERM_MATCH', 'Field': 'capacitystatus', 'Value': capacity_status},
                    {'Type': 'TERM_MATCH', 'Field': 'preInstalledSw', 'Value': preinstalled_software},
                    {'Type': 'TERM_MATCH', 'Field': 'tenancy', 'Value': tenancy},
                    {'Type': 'TERM_MATCH', 'Field': 'licenseModel', 'Value': license_model},
                ],
                MaxResults=100
            )

        for product in response['PriceList']:
            product_obj = json.loads(product)
            price = next(iter(product_obj['terms'][term_type].values()))[
                'priceDimensions']
            price = list(price.values())[0]['pricePerUnit']['CNY']
            if float(price) == 0:
                continue

            instance_type = product_obj['product']['attributes']['instanceType']

            if 'clockSpeed' in product_obj['product']['attributes']:
                clock_speed = product_obj['product']['attributes']['clockSpeed']
                clock_speed = extract_number_from_string(clock_speed)
            else:
                clock_speed = None

            network_performance_str = product_obj['product']['attributes']['networkPerformance']
            network_performance = extract_number_from_string(
                network_performance_str)
            if network_performance is not None:
                if 'Megabit' in network_performance_str:
                    network_performance = str(
                        float(network_performance) / 1000)
            else:
                network_performance = ''

            memory = product_obj['product']['attributes']['memory'].replace(
                ' GiB', '')
            vcpu = product_obj['product']['attributes']['vcpu']
            operating_system = product_obj['product']['attributes']['operatingSystem']
            prices.setdefault(instance_type, []).append({
                f"{term_type}_Price": price, 'Memory': memory, 'vCPU': vcpu,
                'Clock_Speed': clock_speed,
                'Network_Performance': network_performance,
                'OS': operating_system})

        if 'NextToken' in response:
            next_token = response['NextToken']
        else:
            break

    with open(f'{region_name}_ec2_prices.csv', 'w', newline='') as csvfile:
        fieldnames = ['Instance_Type', f"{term_type}_Price", 'Memory', 'vCPU',
                      'Clock_Speed', 'Network_Performance', 'OS']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for instance_type, instance_info_list in prices.items():
            for instance_info in instance_info_list:
                print(f'instance info: {instance_info}')
                writer.writerow({
                    'Instance_Type': instance_type,
                    f"{term_type}_Price": float(instance_info[f"{term_type}_Price"]),
                    'Memory': instance_info['Memory'], 'vCPU': instance_info['vCPU'],
                    'Clock_Speed': instance_info['Clock_Speed'],
                    'Network_Performance': instance_info['Network_Performance'],
                    'OS': instance_info['OS']})


if __name__ == '__main__':
    get_ec2_prices('China (Ningxia)')
    get_ec2_prices('China (Beijing)')
