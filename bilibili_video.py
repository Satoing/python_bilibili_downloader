import re
import requests
import json
from contextlib import closing
from multiprocessing.pool import Pool
from tqdm import tqdm

url = "https://www.bilibili.com/video/BV1b5411c7Sa"


class BilibiliVideo(object):
    """
    封装的bilibili视频类,一个对象对应一个视频或合集，实例化时需要传入url。
    提供的接口：
    1. download(): 下载单个视频
    2. download_collection(): 下载视频合集，兼容download()
    """
    header = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 11_0 like Mac OS X) AppleWebKit/604.1.38 (KHTML, like Gecko) Version/11.0 Mobile/15A372 Safari/604.1',
        'Referer': 'https://www.bilibili.com'  # bilibili新的反爬机制，需要设置Referer为bilibili主站
    }
    cookie = {
        'Cookie': '''i-wanna-go-back=-1; buvid_fp_plain=undefined; SESSDATA=fb6e516d,1671985500,565a0*61; bili_jct=fd2887b95afc46a2a4e7fc58fd7fd756; DedeUserID=52750318; DedeUserID__ckMd5=8c7b267b76a912e4; blackside_state=0; CURRENT_BLACKGAP=0; rpdid=|(J|YumYumml0J'uYlYRJJlkY; LIVE_BUVID=AUTO3016564784976752; b_ut=5; hit-dyn-v2=1; nostalgia_conf=-1; _uuid=1CD98563-3B1D-DC4A-6A8C-1185110EAE36885262infoc; b_nut=1658219185; buvid3=A0423850-F2DE-EDAA-54DF-96DBBC26EBF685732infoc; buvid4=75469809-4201-9788-917E-138AC79A384385732-022071916-cqBLdk3Jccw2jjiQow9BOQ==; fingerprint=fca57e62cfeed3d3073a47d66a6e0d47; sid=7z3j1e0i; buvid_fp=2de6d08901548664c0e846f257cd3a23; is-2022-channel=1; CURRENT_QUALITY=112; PVID=3; theme_style=light; bp_video_offset_52750318=692028766166188000; innersign=1; b_timer={"ffp":{"333.1007.fp.risk_A0423850":"1827D916B38","333.1193.fp.risk_A0423850":"1827D916B9A","333.788.fp.risk_A0423850":"1827D9E52B5"}}; b_lsid=EE95A63F_1827DA5A287; CURRENT_FNVAL=4048'''}
    s = requests.session()

    # 第一次实例化时需要传入COOKIE，不然为空
    def __init__(self, url):
        """
        :param url: bilibili视频的链接
        video_id: 视频的bvid
        vid: 视频或合集的详细信息
        page: 多P视频选择的集数
        cid: 视频的cid
        video_name: 视频的标题
        video_url: 视频的动态链接
        """
        # 打印用户欢迎信息
        my_info = json.loads(BilibiliVideo.s.get('http://api.bilibili.com/x/space/myinfo',
                                                 cookies=BilibiliVideo.cookie).text)
        print("\n欢迎你！" + my_info['data']['name'])

        # 初始化
        self.video_id = re.findall("[\w.]*[\w:\-\+\%]", url)[3]  # 从视频链接中获取bvid
        self.vid = json.loads(
            BilibiliVideo.s.get(f'https://api.bilibili.com/x/web-interface/view?bvid={self.video_id}',
                                headers=BilibiliVideo.header, cookies=BilibiliVideo.cookie).text
        )
        # 默认为单p视频，多P视频先初始化为第一个
        self.page = 0
        self.cid = self.vid['data']['pages'][self.page]['cid']

        # 获取单个视频的信息
        video_info = json.loads(
            BilibiliVideo.s.get('https://api.bilibili.com/x/player/playurl?bvid=' +
                                self.video_id + '&cid=' + str(self.cid) + '&qn=80&otype=json',
                                headers=BilibiliVideo.header, cookies=BilibiliVideo.cookie).text
        )
        # 从视频信息中获取关键信息
        self.video_name = self.vid['data']['title']
        self.video_url = video_info['data']['durl'][0]['url']

    # 下载单个视频
    def download(self):
        # 如果是多P视频，首先需要用户选择下载集数，然后更新视频标题和链接
        if self.vid['data']['videos'] > 1:
            print(f"这是一个多P视频,共{self.vid['data']['videos']}集，列表为：")
            pid = 0
            for page in self.vid['data']['pages']:
                pid += 1
                print(f"{pid}. {page['part']}")

            page = int(input("\n请输入要下载第几集(从1开始)："))
            self.page = page - 1
            self.video_name = self.vid['data']['pages'][self.page]['part']

        info = {
            'pid': self.page + 1,
            'cid': self.vid['data']['pages'][self.page]['cid'],
            'title': self.vid['data']['pages'][self.page]['part'],
            'bvid': self.video_id,
            'url': self.video_url
        }

        self.download_1p(info)

    # 多线程下载合集视频
    def download_collection(self):
        if self.vid['data']['videos'] == 1:
            self.download()

        infos = []  # 合集的数据字典
        for pid in range(int(self.vid['data']['videos'])):
            info = {
                'pid': pid + 1,
                'cid': self.vid['data']['pages'][pid]['cid'],
                'title': self.vid['data']['pages'][pid]['part'],
                'bvid': self.video_id
            }
            infos.append(info)

        pool = Pool(3)
        pool.map(self.download_1p, infos)
        pool.close()  # 关闭进程池，不再接受新的进程
        pool.join()  # 主进程阻塞等待子进程的退出

    # 下载视频的公共代码，实现了一个简易进度条
    # 存在的问题是下载合集视频时进度条会相互覆盖，还要想办法实现一个视频的下载对应一个进度条
    @staticmethod
    def download_1p(info: dict):
        print("\n----------------------------------------------------------\n"
              "开始下载视频{}".format(str(info['pid']) + '. ' + info['title']))

        # 未传入url，说明这是一个多P视频，需要获取
        try: info['url']
        except KeyError:
            detail_url = 'https://api.bilibili.com/x/player/playurl?bvid=' + \
                         info['bvid'] + '&cid=' + str(info['cid']) + '&qn=80&otype=json'
            video_info = json.loads(
                BilibiliVideo.s.get(detail_url, headers=BilibiliVideo.header, cookies=BilibiliVideo.cookie).text
            )
            info['url'] = video_info['data']['durl'][0]['url']

        with closing(BilibiliVideo.s.get(info['url'], headers=BilibiliVideo.header, stream=True)) as response:
            chunk_size = 1024  # 单次请求最大值
            content_size = int(response.headers['content-length'])  # 内容体总大小，单位是字节
            data_count = 0  # 当前下载的大小，初始化为0

            bar = tqdm(total=content_size/(1024**2), unit='MB', desc=f"下载文件 {info['title']}")
            with open(f"./video/{str(info['pid']) + '. ' + info['title']}" + '.flv', mode='wb') as f:
                # 写入分块文件
                for chunk in response.iter_content(chunk_size=chunk_size):
                    f.write(chunk)
                    bar.update(chunk_size/(1024**2))
            # 关闭进度条
            bar.close()

if __name__ == "__main__":
    # print(bvideo.__init__.__doc__)
    bvideo = BilibiliVideo(url)
    bvideo.download_collection()
