from json import JSONDecodeError
from urllib.parse import urljoin

import requests


def ensure_trailing_slash(url: str):
    return urljoin(url + "/", ".")


def fetch_json(*, url: str, session: requests.Session = None, verify: bool = True):
    # Any IOError raised here will just be raised to the calling function, which is desired behavior.
    if session:
        resp = session.get(url, verify=verify)
    else:
        resp = requests.get(url, verify=verify)

    try:
        return resp.json()
    except JSONDecodeError as e:
        raise IOError("Cannot decode JSON response. "
                      f"First 100 chars of server's response are: {resp.text:.100}\n"
                      f"Exception is: {e}")
