__author__ = 'Maksim Andrianov <r.m.andrianov@yandex.ru>'

import subprocess
import requests
import argparse
import sys


def parse_arguments():
    parser = argparse.ArgumentParser(description='...')
    parser.add_argument('--key', action='store', nargs='?', type=str, default=None)
    parser.add_argument('--token', action='store', nargs='?', type=str, default=None)
    parser.add_argument('--discovery', action='count', default=0)
    parser.add_argument('--check', action='count', default=0)
    parser.add_argument('--product_id', action='store', nargs='?', type=str, default=None)
    parser.add_argument('--region', action='store', nargs='?', type=str, default=None)
    parser.add_argument('--name', action='store', nargs='?', type=str, default=None)
    parser.add_argument('-d', '--debug', action='count', default=0)
    args = parser.parse_args()
    return args


def get_token(key_path):
    auth_cmd = f"gcloud auth activate-service-account --key-file={key_path}"
    get_token_cmd = "gcloud auth print-access-token"

    auth_pr = subprocess.Popen(auth_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output_auth, error_auth = auth_pr.communicate()

    if "Activated service account credentials for" in error_auth.decode("utf-8"):
        token_pr = subprocess.Popen(get_token_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        token, error_token = token_pr.communicate()
        return token.decode("utf-8").strip()
    else:
        print(error_auth.decode("utf-8"))
        sys.exit(1)


def get_backend_services(token, product_id):
    url = f"https://compute.googleapis.com/compute/v1/projects/{product_id}" \
          "/aggregated/backendServices?alt=json&includeAllScopes=True&maxResults=500&returnPartialSuccess=True"
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate",
        "Authorization": f"Bearer {token}",
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        # TODO
        # Write a correct error description
        print("Error 1")
        sys.exit(1)


def get_health(token, product_id, region, lb, debug):
    if region != "global":
        get_group_url = f"https://compute.googleapis.com/compute/v1/projects/{product_id}/regions/{region}/backendServices/{lb}?alt=json"
        get_health_url = f"https://compute.googleapis.com/compute/v1/projects/{product_id}/regions/{region}/backendServices/{lb}/getHealth?alt=json"
    else:
        get_group_url = f"https://compute.googleapis.com/compute/v1/projects/{product_id}/{region}/backendServices/{lb}?alt=json"
        get_health_url = f"https://compute.googleapis.com/compute/v1/projects/{product_id}/{region}/backendServices/{lb}/getHealth?alt=json"

    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate",
        "Authorization": f"Bearer {token}",
    }
    get_group_response = requests.get(get_group_url, headers=headers)
    if get_group_response.status_code == 200:
        get_group_response = get_group_response.json()
        data = {
            "group": get_group_response['backends'][0]['group']
        }
        response = requests.post(get_health_url, headers=headers, json=data)
        if response.status_code == 200:
            print(response.json())
        else:
            # TODO
            # Write a correct error description
            print("Error 2")
    else:
        # TODO
        # Write a correct error description
        print("Error 3")


def discovery(token, product_id):
    bs = get_backend_services(token, product_id)
    body = ""
    if bs is not None:
        macros_region = "{#REGION}"
        macros_name = "{#NAME}"
        macros_product_id = "{#PRODUCT_ID}"
        for region, value in bs.get('items', {}).items():
            if 'backendServices' in value:
                for backend_service in value['backendServices']:
                    if backend_service.get('kind') == 'compute#backendService':
                        lb = backend_service.get('name')
                        if lb:
                            region = region.split("/")[-1]
                            body = (body + "{" + f'"{macros_product_id}": "{product_id}",' +
                                    f'"{macros_region}": "{region.split("/")[-1]}",' +
                                    f'"{macros_name}": "{lb}"' + "},")

    data = "{ \"data\": [" + body[:-1] + "] }"
    print(data)


def main():
    args = parse_arguments()

    debug = args.debug
    if args.token:
        token = args.token
    else:
        if args.key:
            token = get_token(args.key)
        else:
            print("Use either --token <YOUR_TOKEN> or --key <PATH_TO_YOUR_FILE>.")
            sys.exit(1)

    # You can pass the product_id as an argument --product_id or store it in a variable.
    if args.product_id:
        product_id = args.product_id
    else:
        # For example
        # product_id = "europe-location-1234"
        # or
        # product_id = ["europe-location-1234", "europe-location-5678", ... ]
        product_id = None

    if args.discovery:
        if args.product_id is None:
            print(f"You must specify the product id as argument --product_id <PRODUCT_ID_NAME> "
                  "or write it to a variable product_id")
        else:
            if isinstance(product_id, list):
                for product in product_id:
                    discovery(token, product)
            else:
                discovery(token, product_id)

    if args.check:
        if args.product_id is None:
            print("You must specify the product id as argument --product_id <PRODUCT_ID_NAME> "
                  "or write it to a variable product_id")
            sys.exit(1)
        if args.region is None:
            print("You must specify the region as an argument --region <REGION_NAME>")
            sys.exit(1)
        if args.name is None:
            print("You must specify the service name as argument --name <LOAD_BALANCER_NAME>")
            sys.exit(1)
        if isinstance(product_id, list):
            for product in product_id:
                get_health(token, product, args.region, args.name, debug)
        else:
            get_health(token, product_id, args.region, args.name, debug)


if __name__ == "__main__":
    main()
