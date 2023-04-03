# v3_main
# 리스트가 가끔 11개 오는 문제 해결.  gid 에 해당하는 기사 벡터를 0으로. 'sorted_u_reverse'를 선택할 경우 점수가 '0'인 곳에서 기사를 추천하는 경우가 생김. 여기서 gid 가 중복으로 골라져 마지막에 걸러져 11개가 나오는것.
from fastapi import FastAPI
import numpy as np
from numpy.random import randint
import redis
from redis import ConnectionPool
import uvicorn
import traceback
import pickle
from collections import defaultdict

def find_10_alt(tot_mat, user_vector, gisa_vector,gid_list, out_list):
    del_index = np.where(np.isin(gid_list, out_list))
    tot_mat[del_index] =0
    sorted_g = np.argsort(np.matmul(tot_mat, gisa_vector))[::-1][:5]
    tot_mat[sorted_g] = 0
    sorted_u_origin = np.argsort(np.matmul(tot_mat, user_vector))[::-1]
    sorted_u = sorted_u_origin[:5]
    sorted_u_reverse = sorted_u_origin[-3:]
    top10 = np.concatenate((sorted_g, sorted_u, sorted_u_reverse)).astype('int32')
    return top10

app = FastAPI()
pool = ConnectionPool(host='localhost', port=6379, db=0)
pool1 = ConnectionPool(host='localhost', port=6379, db=1)
pool2 = ConnectionPool(host='localhost', port=6379, db=2)
pool3 = ConnectionPool(host='localhost', port=6379, db=3)
r = redis.Redis(connection_pool=pool)
r1 = redis.Redis(connection_pool=pool1)
r2 = redis.Redis(connection_pool=pool2)
r3 = redis.Redis(connection_pool=pool3)
@app.get("/{ga}/{gid}")
async def hello(ga:str, gid:str=None):
    gid = None if gid=='_' else gid
    dics1= {}
    for _ in range(3):
        try:  # # redis에서 이유 없이 None 이 나오는 경우가 매우 드물게 있어서 3번 시도.
            if gid is None:  # 사용자에게서 gid 가 안옴
                u_vec = r1.get(ga)
                if u_vec == None:  # 사용자 ga에 해당하는 벡터가 없음
                    # 완전히 새로운 추천
                    u_vec = r2.get('default0')
                    g_vec = u_vec
                else:  # 사용자 ga에 해당하는 벡터가 있음
                    g_vec = u_vec
            else:  # 사용자에게서 gid 가 옴
                g_vec = r.get(gid)
                u_vec = r1.get(ga)
                if u_vec is not None:  # ga에 해당하는 벡터가 있음
                    if g_vec is not None:  # gid에 해당하는 벡터가 있음
                        pass  # 걍 하면 됨
                    else:  # gid에 해당하는 벡터가 없음
                        g_vec = u_vec  # 유저 벡터를 기사 벡터로 씀 (이전에 봤던게 더 강화됨)
                else:  # ga에 해당하는 벡터가 없음. 처음오는 손님
                    if g_vec is not None:  # gid에 해당하는 벡터는 있음
                        u_vec = g_vec
                    else:  # gid에 해당하는 벡터도 없음
                        # 완전히 새로운 추천
                        u_vec = r2.get('default0')
                        g_vec = u_vec
            u_vec = np.frombuffer(u_vec, dtype='float32')
            g_vec = np.frombuffer(g_vec, dtype='float32')
            gid_list = np.frombuffer(r2.get('gid'), dtype='U9')
            mat = r2.get('mat')
            mat = np.frombuffer(mat, dtype='float32').reshape(-1, 50).copy()
            history = r3.get(ga)
            history = pickle.loads(history) if history!=None else defaultdict(int)
            history['read'] +=1
            reversep = history['read']
            p = 1/reversep if reversep <12 else 1/12
            history[gid] += 10
            out_list = np.array([k for k, v in history.items() if v >= 3])
            top10 = find_10_alt(mat, u_vec, g_vec, gid_list,out_list)
            row_del = None
            if len(out_list) >100:
                r3.delete(ga)
            else:
                for i, gid0 in enumerate(gid_list[top10]):
                    if i <= 6:
                        history[gid0] += 1
                    if gid == gid0:
                        row_del = i
                r3.set(ga, pickle.dumps(history))
                r3.expire(ga,600)
            top10 = np.delete(top10, row_del, axis=0)[:12] if row_del != None else top10[:12]
            u_vec = p * g_vec + (1-p) * u_vec
            r1.set(ga, u_vec.tobytes())
            r1.expire(ga, 2592000)  # 60*60*24*30 : 30일 뒤
            a = r2.get('title')
            title_list = np.frombuffer(a, dtype='U59')
            url_list = np.frombuffer(r2.get('url'), dtype='U68')
            thumburl_list = np.frombuffer(r2.get('thumburl'),dtype='U65')

            dics1 = {}
            for i, x in enumerate(top10):
                if gid != gid_list[x]:
                    dics1[i] = {'title': title_list[x], 'url': url_list[x], 'thumburl': thumburl_list[x]}
            break
        except Exception as e:
            traceback.print_exc()
            print(e)
    return dics1

if __name__ == '__main__':
    uvicorn.run(app, port=8001, host='0.0.0.0')
