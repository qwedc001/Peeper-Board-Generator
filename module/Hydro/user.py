import base64
import logging
import requests
from module.config import Config
from module.utils import headers, get_qq_name
from module.structures import UserData
from lxml import etree


def infer_qq(html, mail) -> str:
    # 一共有三种手段：检测QQ邮箱，爬取QQ号字段是否有QQ号，检测头像字段是否有QQ号
    direct_qq_base64 = "".join(html.xpath('//a[@data-tooltip="复制QQ号"]/@data-copy'))
    direct_qq = base64.b64decode(direct_qq_base64).decode() if direct_qq_base64 else ""
    if direct_qq:
        return direct_qq
    if mail and mail.split("@")[1] == "qq.com":
        return mail.split("@")[0]
    avatar = "".join(html.xpath('//div[@class="media__left"]/img/@src'))
    # 有QQ号的头像链接格式如下 //q1.qlogo.cn/g?b=qq&nk=QQ号&...
    if "q1.qlogo.cn" in avatar and "nk=" in avatar:
        return avatar.split("nk=")[1].split("&")[0]
    return ""


def fetch_user(config: Config, uid: str) -> UserData:
    logging.info("开始获取用户记录")
    url = config.get_config("url") + f'user/{uid}'
    user_headers = headers
    headers['Cookie'] = f'sid={config.get_config("cookie")["sid"]};sid.sig={config.get_config("cookie")["sid_sig"]};'
    response_text = requests.get(url, headers=user_headers)
    html = etree.HTML(response_text.text)
    user_name = "".join(s.strip() for s in html.xpath('//div[@class="media__body profile-header__main"]/h1/text()'))
    user = UserData(user_name, uid)
    mail_base64 = "".join(html.xpath('//a[@data-tooltip="复制电子邮件"]/@data-copy'))
    user.mail = base64.b64decode(mail_base64).decode() if mail_base64 else ""
    user.qq = infer_qq(html, user.mail)
    # user.qq_name = get_qq_name(user.qq) if user.qq else ""
    status_and_progress = "".join(html.xpath('//div[@class="media__body profile-header__main"]/p/text() | //div['
                                             '@class="media__body profile-header__main"]/p/*/text()')).split("\n")
    user.status = "".join(s.strip() for s in status_and_progress[:-1])
    user.progress = status_and_progress[-1].strip()
    user.description = "\n".join(
        html.xpath('//div[@class="section__body typo richmedia"]/p/text() | //div[@class="section__body typo '
                   'richmedia"]/p//*/text()'))
    return user
