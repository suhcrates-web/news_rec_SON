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
pool2 = ConnectionPool(host='localhost', port=6379, db=2)
pool3 = ConnectionPool(host='localhost', port=6379, db=3)
r = redis.Redis(connection_pool=pool)
r2 = redis.Redis(connection_pool=pool2)
r3 = redis.Redis(connection_pool=pool3)
r.flushdb()
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
    select gid, mat, title, url, thumburl, tot_gid, tot_mat from news_recommend.carrier where id0=1
    """
)

gid, mat, title, url, thumburl, tot_gid, tot_mat = cursor.fetchall()[0]

tot_mat = np.frombuffer(tot_mat,dtype='float32').reshape(-1,30)
tot_gid = json.loads(tot_gid)
pipe3 = r3.pipeline()
pipe2 = r2.pipeline()
start = timeit.default_timer()
for i, vec0 in enumerate(tot_mat):
    pipe3.set(tot_gid[i], vec0.tobytes())
pipe3.execute()
mid = timeit.default_timer()

r2.set('mat',mat)
r2.set('title', title)
r2.set('gid', gid)
r2.set('url', url)
r2.set('thumburl', thumburl)
pipe2.execute()
end = timeit.default_timer()
print(mid-start)
print(end -mid)


### r0, r3 모두  없는것들은 지워줘야됨.