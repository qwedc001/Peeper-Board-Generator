import requests

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
}


def get_qq_name(qq: str):
    url = 'https://api.usuuu.com/qq/' + qq
    res = requests.get(url, headers)
    if res.status_code == 200:
        return res.json()['data']['name']
    else:
        raise Exception("获取QQ昵称失败")
