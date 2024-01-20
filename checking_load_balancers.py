import subprocess
import requests
import argparse


def get_token(key_path):
    auth_cmd = f"gcloud auth activate-service-account --key-file={key_path}"
    get_token_cmd = "gcloud auth print-access-token"

    auth_pr = subprocess.Popen(auth_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    token_pr = subprocess.Popen(get_token_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    output_auth, error_auth = auth_pr.communicate()
    token, error_token = token_pr.communicate()

    print(error_auth.decode("utf-8"))
    return token.decode("utf-8").strip()


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
        return None


def get_health(token, product_id, region, lb):
    if region != "global":
        region = f"regions/{region}"
    url = f"https://compute.googleapis.com/compute/v1/projects/{product_id}/{region}/backendServices/{lb}?alt=json"
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate",
        "Authorization": f"Bearer {token}",
    }
    response = requests.get(url, headers=headers)
    print(response.json())


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
    else:
        body = ""
    data = "{ \"data\": [" + body[:-1] + "] }"
    print(data)


def main():
    parser = argparse.ArgumentParser(description='...')
    parser.add_argument('--key', action='store', nargs='?', type=str, required=True, default=None)
    parser.add_argument('--discovery', action='count', default=0)
    parser.add_argument('--debug', action='count', default=0)
    args = parser.parse_args()

    token = get_token(args.key)

    #key = "test-key.json"

    if args.discovery:
        discovery(token, product_id)

    #get_backend_services(token, product_id)
    #get_health(token, product_id, region, name)


if __name__ == "__main__":
    main()