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
pool4 = ConnectionPool(host='localhost', port=6379, db=4)
r = redis.Redis(connection_pool=pool)
r1 = redis.Redis(connection_pool=pool1)
r2 = redis.Redis(connection_pool=pool2)
r3 = redis.Redis(connection_pool=pool3)
r4 = redis.Redis(connection_pool=pool4)


### ai 추천포유
@app.get("/foryou/{ga}/{gid}")
async def hello(ga:str, gid:str=None, login_user:bool=False):
    gid = None if gid=='_' else gid
    g_vec_flag = True  # g_vec이 있는 경우
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
                        g_vec_flag = False
                        g_vec = u_vec  # 유저 벡터를 기사 벡터로 씀 (이전에 봤던게 더 강화됨)
                else:  # ga에 해당하는 벡터가 없음. 처음오는 손님
                    if g_vec is not None:  # gid에 해당하는 벡터는 있음
                        u_vec = g_vec
                    else:  # gid에 해당하는 벡터도 없음
                        # 완전히 새로운 추천
                        g_vec_flag = False
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
            r1.expire(ga, 864000)  # 60*60*24*10 : 10일 뒤로 낮춤.
            a = r2.get('title')
            title_list = np.frombuffer(a, dtype='U59')
            url_list = np.frombuffer(r2.get('url'), dtype='U68')
            thumburl_list = np.frombuffer(r2.get('thumburl'),dtype='U65')

            dics1 = {}
            for i, x in enumerate(top10):
                if gid != gid_list[x]:
                    dics1[i] = {'title': title_list[x], 'url': url_list[x], 'thumburl': thumburl_list[x]}

            #### 동아닷컴 유저 정보 수집 ####
            if login_user:
            # if len(ga) > 40 and gid != None and g_vec_flag:  # 동닷유저일 경우 + gid 가 왔을경우 + g_vec이 있는 경우
                dics4= r4.get(ga)
                if dics4 == None:
                    dics4 = {'gids':[], 'vecs':[], 'cent':[]}
                else:
                    dics4 = pickle.loads(dics4)  
                dics4['gids'].append(gid)
                dics4['gids'] = dics4['gids'][-20:]
                dics4['vecs'].append(g_vec)
                dics4['vecs'] = dics4['vecs'][-20:]
                r4.set(ga, pickle.dumps(dics4))
                r4.expire(ga, 5184000) # 60*60*24*60 두달
                    
            #######
            break
        
        except Exception as e:
            traceback.print_exc()
            print(e)
    return dics1



@app.get("/gainhwa/{ga}")
async def gainhwa(ga:str, login_user:bool=False):

    ## 개인 열람 기록
    seed_4 = r4.get(ga)
    if seed_4 ==None: # 기사를 본적이 없는 ga
        return "no_data"

    #

    dics4 = pickle.loads(seed_4)  # 기사 열람기록 + vector
    # print(dics4['vecs'])
    vec_len = len(dics4['vecs'])
    # print(vec_len)

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




# if __name__ == '__main__':
#     uvicorn.run(app, port=8001, host='0.0.0.0')
