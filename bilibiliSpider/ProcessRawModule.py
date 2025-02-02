'''
a module for processing json raw info to serialize info
'''
import bilibiliSpider
import ToolBox
from Config import spider_config
import csv
from multiprocessing import Pool
import os
import time

default_spider = bilibiliSpider.bilibili_spider()
default_output_path = spider_config.output_path
default_spider.mas_proxy_flag = spider_config.mas_proxy_flag
default_tasks = spider_config.tasks
default_multi_processor_flag = spider_config.multi_processor_flag
default_multi_processor_num = spider_config.multi_processor_num
default_rank_type = spider_config.rank_type
error_raw = {'code': 0, 'message': '0', 'ttl': 1, 'data': {
                'aid': -1, 'view': -1, 'danmaku': -1, 'reply': -1, 'favorite': -1, 'coin': -1, 'share': -1, 'like': -1,
                'now_rank': -1, 'his_rank': -1, 'no_reprint': -1, 'copyright': -1, 'argue_msg': '-1'
                }
            }

default_head = ['0rank_type', '1video_type', '2video_id', '3ranking',
                 '4video_title', '5video_upload_time', '6video_length_time',
                 '7author_id', '8author_followers', '9author_following',
                 '10view', '11danmaku', '12reply', '13favorite', '14coin', '15share', '16like',
                 '17points', '18spider_time'
            ]
def process_extract(videos):
    info = []
    spider = default_spider
    head = default_head
    count = 0
    for temp in videos:
        video_info = [i for i in head]
        video_info[0] = temp[0]
        video_info[1] = temp[1]
        video_info[2] = temp[3]
        video_info[3] = temp[2]
        video_info[4] = temp[4]
        video_info[7] = temp[5]
        video_info[17] = temp[6]

        video_aid = video_info[2]

        author_mid = video_info[7]

        video_info[5] = spider.get_video_upload_time_info(video_aid)
        video_info[6] = spider.get_video_length_info(video_aid)

        author_info = process_raw_user_info(author_mid)
        video_info[8] = author_info[1]
        video_info[9] = author_info[0]
        ToolBox.tool_stop_random_time(max_time=0.05)
        video_info[10:17] = process_raw_video_info(video_aid)

        video_info[18] = ToolBox.tool_get_current_time()
        info.append(video_info)
        count += 1
        log = '{} now, got aid {}, failed {} videos'.format(count, video_aid, spider.get_error_count())
        print(log)
        ToolBox.tool_log_info(level='info', message=log)
    return info

def process_raw_video_info(aid, spider=default_spider):
    '''
    :param spider: an object of bilibili_spider
    :param aid:
    :return: list ['view', 'danmaku', 'reply', 'favorite', 'coin', 'share', 'like']
    '''
    try:
        raw = spider.get_raw_video_info(aid)
        if raw.get('data') is None:
            raw = error_raw
            error_raw['data']['aid'] = aid
    except Exception as e:
        log = 'ERROR IN process raw video info aid {} {}'.format(aid, e)
        ToolBox.tool_log_info(level='error', message=log)
        print(log)
        raw = error_raw
        raw['data']['aid'] = aid
    info = []
    temp = ['0view', '1danmaku', '2reply', '3favorite', '4coin', '5share', '6like']
    for i in temp:
        info.append(raw.get('data').get(i[1:]))

    return info


def process_raw_user_info(mid, spider=default_spider):
    '''
    :param spider: an object of bilibili_spider
    :param mid: user's id
    :return: list ['following', 'follower']
    '''
    try:
        raw = spider.get_raw_user_info(mid)
    except Exception as e:
        log = 'ERROR IN GET RAW USER INFO mid{} {}'.format(mid, e)
        ToolBox.tool_log_info(level='error', message=log)
        print(log)
        raw = {
            'data' : {
                'following' : -1,
                'follower' : -1,
            }
        }
    info = []
    temp = ['0following', '1follower']
    for i in temp:
        info.append(raw.get('data').get(i[1:]))
    return info



def process_one_task(video_category, rank_type='origin', spider=default_spider):
    # info.append(head)
    count = 0
    ToolBox.tool_stop_random_time(max_time=0.5)
    videos = spider.get_rank_video_info(rank_type=rank_type, video_type=video_category)[1:]
    log = 'getting {} {}'.format(rank_type, video_category)
    print(log)
    ToolBox.tool_log_info(level='info', message=log)
    info = process_extract(videos)
    csv_path = 'bilibili_rank_data' + f'_{video_category}.csv'
    with open(csv_path, 'a+', encoding='utf-8', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(info)
        log = f'{video_category}done ! spider {count} videos failed in {spider.get_error_count()} videos'
        print(log)
        ToolBox.tool_log_info(level='info', message=log)

def process_merge_csv(tasks=default_tasks, output_path=default_output_path):
    '''
    merge csv files to one csv file
    :param tasks:
    :return:
    '''
    info = []
    head = default_head
    info.append(head)
    prefix = 'bilibili_rank_data'
    for task in tasks:
        try:
            csv_path = prefix + f'_{task}.csv'
            with open(csv_path, 'r', encoding='utf-8', newline='') as file:
                reader = csv.reader(file)
                for row in reader:
                    info.append(row)
            os.remove(csv_path)
        except Exception as e:
            print('ERROR IN process_merge_csv {}'.format(e))

    with open(output_path, 'a+', encoding='utf-8', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(info)


#make your own rule to collect info

def process_multi_tasks(tasks=default_tasks, rank_tyoe='origin'):
    '''
    Multi processors spider
    :param tasks: video categories like ['guochuang', 'movie']
    :return:
    '''
    # max_cpu_count = multiprocessing.cpu_count()
    max_cpu_count = default_multi_processor_num
    if max_cpu_count is None:
        max_cpu_count = 1
    p = Pool(max_cpu_count)
    for task in tasks:
        p.apply_async(process_one_task, args=(task, rank_tyoe))

    p.close()
    p.join()

    log = f'done ! spider videos failed in {default_spider.get_error_count()} videos'
    ToolBox.tool_log_info(level='info', message=log)


def process_single_tasks(spider=default_spider, rank_type='origin'):
    '''
    make your own rule to collect info with single processor
    :param spider:
    :param csv_path:
    :param rank_type:
    :return:
    '''
    video_category = default_tasks
    # info.append(head)
    count = 0
    for video_type in video_category:
        ToolBox.tool_stop_random_time(max_time=0.3)
        videos = spider.get_rank_video_info(rank_type=rank_type, video_type=video_type)[1:]
        log = 'getting {} {}'.format(rank_type, video_type)
        print(log)
        ToolBox.tool_log_info(level='info', message=log)
        info = process_extract(videos)
        csv_path = 'bilibili_rank_data' + f'_{video_type}.csv'
        with open(csv_path, 'a+', encoding='utf-8', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(info)
            log = f'{video_type} done ! spider {count} videos failed in {spider.get_error_count()} videos'
            print(log)
            ToolBox.tool_log_info(level='info', message=log)


@ToolBox.tool_count_time
def process_run_main(multi_processor_flag=default_multi_processor_flag):
    print('spider will start in {} seconds ...'.format(10))
    time.sleep(5)
    if multi_processor_flag:
        process_multi_tasks(rank_tyoe=default_rank_type)
    else:
        process_single_tasks(rank_type=default_rank_type)

    process_merge_csv(default_tasks, default_output_path)







if __name__ == '__main__':

    process_merge_csv()
    # tasks = list(default_spider.video_category.keys())
    # tasks = ['game', 'movie', 'dance']
    # process_multi_tasks(tasks, output_path='output.csv')
    # 249.63007489999998 seconds
    #
    # cost 13 min