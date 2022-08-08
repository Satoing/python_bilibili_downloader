import re
import requests
import json
from contextlib import closing
from multiprocessing.pool import Pool

url = "https://www.bilibili.com/video/BV1b5411c7Sa"


class BilibiliVideo(object):
    """
    封装的bilibili视频类，
    类属性和合集相关，
    而一个对象对应一个视频。
    实例化时需要传入cookies和url
    """
    header = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 11_0 like Mac OS X) AppleWebKit/604.1.38 (KHTML, like Gecko) Version/11.0 Mobile/15A372 Safari/604.1',
        'Referer': 'https://www.bilibili.com'  # bilibili新的反爬机制，需要设置Referer为bilibili主站
    }
    cookie = {
        'Cookie': '''i-wanna-go-back=-1; buvid_fp_plain=undefined; SESSDATA=fb6e516d,1671985500,565a0*61; bili_jct=fd2887b95afc46a2a4e7fc58fd7fd756; DedeUserID=52750318; DedeUserID__ckMd5=8c7b267b76a912e4; blackside_state=0; CURRENT_BLACKGAP=0; rpdid=|(J|YumYumml0J'uYlYRJJlkY; LIVE_BUVID=AUTO3016564784976752; b_ut=5; hit-dyn-v2=1; nostalgia_conf=-1; _uuid=1CD98563-3B1D-DC4A-6A8C-1185110EAE36885262infoc; b_nut=1658219185; buvid3=A0423850-F2DE-EDAA-54DF-96DBBC26EBF685732infoc; buvid4=75469809-4201-9788-917E-138AC79A384385732-022071916-cqBLdk3Jccw2jjiQow9BOQ==; fingerprint=fca57e62cfeed3d3073a47d66a6e0d47; sid=7z3j1e0i; buvid_fp=2de6d08901548664c0e846f257cd3a23; is-2022-channel=1; CURRENT_QUALITY=112; PVID=3; theme_style=light; bp_video_offset_52750318=692028766166188000; innersign=1; b_timer={"ffp":{"333.1007.fp.risk_A0423850":"1827D916B38","333.1193.fp.risk_A0423850":"1827D916B9A","333.788.fp.risk_A0423850":"1827D9E52B5"}}; b_lsid=EE95A63F_1827DA5A287; CURRENT_FNVAL=4048'''}
    s, flag = requests.session(), False
    video_id, vid = '', dict()

    @classmethod
    def init(cls, url):
        """
        类属性的初始化函数
        cookie: 用户的cookie，把它设置为类属性而不是实例属性
        video_id: 视频的bvid
        vid: 视频的详细信息及字幕、封面等静态资源的链接
        """
        # 初始化
        cls.video_id = re.findall("[\w.]*[\w:\-\+\%]", url)[3]  # 从视频链接中获取bvid
        cls.vid = json.loads(
            cls.s.get(f'https://api.bilibili.com/x/web-interface/view?bvid={cls.video_id}',
                      headers=cls.header, cookies=cls.cookie).text
        )
        # 打印用户信息
        my_info = json.loads(cls.s.get('http://api.bilibili.com/x/space/myinfo',
                                       cookies=cls.cookie).text)
        print("\n欢迎你！" + my_info['data']['name'])

    # 第一次实例化时需要传入COOKIE，不然为空
    def __init__(self, url):
        """
        初始化实例属性并打印用户信息
        :param url: bilibili视频的链接
        -------------------------------------------
        page: 多P视频选择的集数
        video: 视频的cid
        video_name: 视频的标题
        video_url: 视频的动态链接
        """
        # 初始化类属性并打印用户信息
        BilibiliVideo.init(url)

        # 默认为单p视频，如果为多P，就需要选择集数
        self.page = 0
        if BilibiliVideo.vid['data']['videos'] > 1:
            print(f"这是一个多P视频,共{BilibiliVideo.vid['data']['videos']}集，列表为：")
            pid = 0
            for page in BilibiliVideo.vid['data']['pages']:
                pid += 1
                print(f"{pid}. {page['part']}")
            page = int(input("这似乎是一个多P视频。\n请输入要下载第几集(从1开始)："))
            self.page = page - 1
        self.video = BilibiliVideo.vid['data']['pages'][self.page]['cid']

        # 获取单个视频的信息
        video_info = json.loads(
            BilibiliVideo.s.get('https://api.bilibili.com/x/player/playurl?bvid=' +
                                BilibiliVideo.video_id + '&cid=' + str(self.video) + '&qn=80&otype=json',
                                headers=BilibiliVideo.header, cookies=BilibiliVideo.cookie).text
        )
        # 从视频信息中获取关键信息
        self.video_name = BilibiliVideo.vid['data']['title']
        self.video_url = video_info['data']['durl'][0]['url']
        # 如果是多P视频，下载的视频标题应该是列表中的标题
        if BilibiliVideo.vid['data']['videos'] > 1:
            self.video_name = BilibiliVideo.vid['data']['pages'][self.page]['part']

    def download(self):
        print(f"\n开始下载视频\n----------------------------------------"
              f"\n视频标题：{self.video_name}\n下载链接：{self.video_url}")

        with closing(BilibiliVideo.s.get(self.video_url, headers=BilibiliVideo.header, stream=True)) as response:
            chunk_size = 1024  # 单次请求最大值
            content_size = int(response.headers['content-length'])  # 内容体总大小，单位是字节
            data_count = 0  # 当前下载的大小，初始化为0
            with open(self.video_name + '.flv', 'wb') as file:
                for data in response.iter_content(chunk_size=chunk_size):
                    file.write(data)
                    data_count = data_count + len(data)
                    now_jd = (data_count / content_size) * 100
                    print("\r视频下载进度：%d%% (%dMB/%dMB)" % (now_jd, data_count / (1024 ** 2), content_size / (1024 ** 2)),
                          end=" ")
                input('\n\n下载成功！下载的视频位于本程序同级目录中,按回车退出程序...')

    @staticmethod
    def download_1p(info: dict):
        print("\n{}开始下载".format(str(info['pid'])+'. '+info['video_name']))

        with closing(BilibiliVideo.s.get(info['video_url'], headers=BilibiliVideo.header, stream=True)) as response:
            chunk_size = 1024  # 单次请求最大值
            content_size = int(response.headers['content-length'])  # 内容体总大小，单位是字节
            data_count = 0  # 当前下载的大小，初始化为0

            with open(f"./video/{str(info['pid'])+'. '+info['video_name']}" + '.flv', 'wb') as file:
                for data in response.iter_content(chunk_size=chunk_size):
                    file.write(data)
                    data_count = data_count + len(data)
                    now_jd = (data_count / content_size) * 100
                    print("\r视频%d下载进度：%d%% (%dMB/%dMB)" %
                          (info['pid'], now_jd,data_count / (1024 ** 2), content_size / (1024 ** 2)), end="")

    # 多线程下载合集视频
    @classmethod
    def download_collection(cls, url):
        cls.init(url)
        if cls.vid['data']['videos'] == 1:
            print('这个函数对单P视频是无效的')
            return

        infos = []  # 合集的数据字典

        # 这里单线程请求有点耗时
        for pid in range(int(cls.vid['data']['videos'])):
            video = cls.vid['data']['pages'][pid]['cid']
            video_info = json.loads(
                cls.s.get('https://api.bilibili.com/x/player/playurl?bvid=' +
                          cls.video_id + '&cid=' + str(video) + '&qn=80&otype=json',
                          headers=cls.header, cookies=cls.cookie).text
            )
            info = dict()
            info['pid'] = pid
            info['video_name'] = cls.vid['data']['pages'][pid]['part']
            info['video_url'] = video_info['data']['durl'][0]['url']
            infos.append(info)

        pool = Pool(3)
        pool.map(cls.download_1p, infos)
        pool.close()  # 关闭进程池，不再接受新的进程
        pool.join()  # 主进程阻塞等待子进程的退出


if __name__ == "__main__":
    # print(bvideo.__init__.__doc__)
    BilibiliVideo.download_collection(url)
