from fastapi import FastAPI
import numpy as np
from numpy.random import randint
import redis
from redis import ConnectionPool
import uvicorn
import traceback
import pickle
from collections import defaultdict

pool1 = ConnectionPool(host='localhost', port=6379, db=1)
r1 = redis.Redis(connection_pool=pool1)
pool2 = ConnectionPool(host='localhost', port=6379, db=2)
r2 = redis.Redis(connection_pool=pool2)
pool3 = ConnectionPool(host='localhost', port=6379, db=3)
r3 = redis.Redis(connection_pool=pool3)
pool4 = ConnectionPool(host='localhost', port=6379, db=4)
r4 = redis.Redis(connection_pool=pool4)

app = FastAPI()
pool = ConnectionPool(host='localhost', port=6379, db=0)
pool1 = ConnectionPool(host='localhost', port=6379, db=1)
pool2 = ConnectionPool(host='localhost', port=6379, db=2)
pool3 = ConnectionPool(host='localhost', port=6379, db=3)
pool4 = ConnectionPool(host='localhost', port=6379, db=4)
r = redis.Redis(connection_pool=pool)
r1 = redis.Redis(connection_pool=pool1)
r2 = redis.Redis(connection_pool=pool2)
r3 = redis.Redis(connection_pool=pool3)
r4 = redis.Redis(connection_pool=pool4)


@app.get("/gainhwa/{ga}")
async def gainhwa(ga:str, login_user:bool=False):
    # print(ga)
    print(login_user)
    if login_user:
        print('로그인 햇당께')
    ## 개인 열람 기록
    seed_4 = r4.get(ga)
    if seed_4 ==None: # 기사를 본적이 없는 ga
        return "no_data"

    #

    dics4 = pickle.loads(seed_4)  # 기사 열람기록 + vector
    # print(dics4['vecs'])
    vec_len = len(dics4['vecs'])
    print(vec_len)

    history = r3.get(ga)   # 추천기록
    history = pickle.loads(history) if history!=None else defaultdict(int)
    out_list = np.array([k for k, v in history.items() if v >= 3])
    # reversep = history['read']

    ## 전체 mat
    mat = r2.get('mat')
    mat = np.frombuffer(mat, dtype='float32').reshape(-1, 50).copy()
    gid_list = np.frombuffer(r2.get('gid'), dtype='U9')
    title_list = np.frombuffer(r2.get('title'), dtype='U59')
    url_list = np.frombuffer(r2.get('url'), dtype='U68')
    thumburl_list = np.frombuffer(r2.get('thumburl'), dtype='U65')

    ### de_index 설정
    del_index = np.where(np.isin(gid_list, out_list))
    mat[del_index] =0

    ##
    if vec_len == 1:
        vec = dics4['vecs'][0]
        sorted_g = np.argsort(np.matmul(mat, vec))[::-1]
        first0 = sorted_g[:9]
        last0 = sorted_g[-5:]
        pallet = [[first0, 9], [last0,3]]

    elif vec_len ==2:
        first_vec = dics4['vecs'][-1]  # 멘 뒤에있는게 최신
        last_vec = dics4['vecs'][0]
        first0 = np.argsort(np.matmul(mat, first_vec))[::-1][:6]
        mat[first0] = 0
        sorted_last = np.argsort(np.matmul(mat, last_vec))[::-1]
        last0 = sorted_last[:12]
        pallet = [[first0, 6], [last0,6]]
    else:
        indiv_mat = np.array(dics4['vecs'])
        first_vec = indiv_mat[-1].copy()
        ordered0 = np.argsort(np.matmul(indiv_mat, first_vec))[::-1]
        middle_vec = indiv_mat[ordered0[len(ordered0)//2]]
        last_vec = indiv_mat[ordered0[-1]]

        first0 = np.argsort(np.matmul(mat, first_vec))[::-1][:6]
        mat[first0] = 0
        middle0 = np.argsort(np.matmul(mat, middle_vec))[::-1][:6]
        mat[middle0] = 0
        sorted_last = np.argsort(np.matmul(mat, last_vec))[::-1]
        last0 = sorted_last[:6]
        pallet = [[first0,4], [middle0,4], [last0,4]]

    top12 = []
    for list0, limit0 in pallet:
        temp_n = 0
        for ind0 in list0:
            if ind0 not in top12:
                top12.append(ind0)
                temp_n +=1
                if temp_n >=limit0:
                    break
    dics1 = {}
    for i, x in enumerate(top12):
        dics1[i] = {'title': title_list[x], 'url': url_list[x], 'thumburl': thumburl_list[x]}

        ### history update
        gid0 = gid_list[x]
        history[gid0] += 0.5
        r3.set(ga, pickle.dumps(history))
        r3.expire(ga, 600)
    return dics1



if __name__ == '__main__':
    uvicorn.run(app, port=8002, host='0.0.0.0')