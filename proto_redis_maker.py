### updater
import mysql.connector
from database import config
from redis import Redis, ConnectionPool
import redis
import numpy as np
import json
import timeit


db = mysql.connector.connect(**config)
cursor = db.cursor()
pool = ConnectionPool(host='localhost', port=6379, db=0)
pool1 = ConnectionPool(host='localhost', port=6379, db=1)
pool2 = ConnectionPool(host='localhost', port=6379, db=2)
pool3 = ConnectionPool(host='localhost', port=6379, db=3)
r = redis.Redis(connection_pool=pool)
r1 = redis.Redis(connection_pool=pool1)
r2 = redis.Redis(connection_pool=pool2)
r3 = redis.Redis(connection_pool=pool3)
r.flushdb()
r1.flushdb()
r2.flushdb()
r3.flushdb()
pipe0 = r.pipeline()
cursor.execute(
    f"""
    select gid, vec from news_recommend.news_ago
    """
)
for gid, vec in cursor.fetchall():
    if gid=='url':
        print('url')
    pipe0.set(gid,vec)
pipe0.execute()


cursor.execute(
    """
    select gid, mat, title, url, thumburl from news_recommend.carrier where id0=1
    """
)

gid, mat, title, url, thumburl = cursor.fetchall()[0]

pipe2 = r2.pipeline()
r2.set('mat',mat)
r2.set('title', title)
r2.set('gid', gid)
r2.set('url', url)
r2.set('thumburl', thumburl)
pipe2.execute()


### r0, r3 모두  없는것들은 지워줘야됨.