### updater
import mysql.connector
from database import config
from redis import Redis, ConnectionPool
import redis
import numpy as np
import json
import sys
import time
from datetime import datetime


pool = ConnectionPool(host='localhost', port=6379, db=0)
pool2 = ConnectionPool(host='localhost', port=6379, db=2)
r = redis.Redis(connection_pool=pool)
r2 = redis.Redis(connection_pool=pool2)

pipe0 = r.pipeline()
pipe2 = r2.pipeline()

def son_updater():
    db = mysql.connector.connect(**config)
    cursor = db.cursor()

    r_gids = r.keys('*')
    r_gids = np.array(r_gids).astype(np.int32)
    cursor.execute(
        f"""
        select gid from news_recommend.news_ago
        """
    )
    m_gids = np.array(cursor.fetchall()).reshape(1,-1)[0]

    #추가
    add_array = np.setdiff1d(m_gids, r_gids) #mysql에만 있는 것 추가
    if len(add_array) > 0:
        cursor.execute(
            f"""
            select gid, vec from news_recommend.news_ago where gid in ({','.join(map(str,add_array))})
            """
        )
        for gid, vec in cursor.fetchall():
            pipe0.set(gid, vec)
        pipe0.execute()
    #삭제
    del_array = np.setdiff1d(r_gids, m_gids) # redis에만 있는거 (삭제)
    for gid0 in del_array:
        pipe0.delete(gid0)
    pipe0.execute()

    # r2 업데이트
    cursor.execute(
        """
        select gid, mat, title, url, thumburl, default0 from news_recommend.carrier where id0=1
        """
    )

    gid, mat, title, url, thumburl, default0 = cursor.fetchall()[0]

    pipe2.set('gid',gid)
    pipe2.set('mat',mat)
    pipe2.set('title', title)
    pipe2.set('url', url)
    pipe2.set('thumburl', thumburl)
    pipe2.set('default0', default0)
    pipe2.execute()


if __name__ == '__main__':
    n=0
    while True:
        n+=1
        now0 = datetime.now()
        son_updater()
        print('did')
        sys.stdout.flush()
        time.sleep(60*4)