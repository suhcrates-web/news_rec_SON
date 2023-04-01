#### readme #####

## general
본 API 서비스는 분석용 서버인 news_rec_SHIP (1대)와 news_rec_SON (2대),  RDS (1대)로 이뤄짐.
news_rec_SHIP은 동아닷컴 기사목록 조회 api인 https://openapi.donga.com/newsList 로부터 기사목록을 다운받아 RDS의 news_recommend DB의 news_ago 테이블, carrier 테이블을 업데이트하는 역할을 함.
  news_rec_SHIP 은 RDS 일방적으로 업로드하기만 하며, news_rec_SON 은 일방적으로 다운로드 하기만 함. SHIP과 SON 은 RDS를 통해 소통하며 직접적인 소통은 없음.

## SHIP
systemctl 에 news_rec_SHIP.service 가 enable 돼있음.
이 services는 total_update_timeline.py 를 가동시키는 역할을 하며, 이 파일은 2분에 한번씩 msyql_realtime_update.py 와 carrier_maker.py 를 가동시킴.
 mysql_realtime_update.py 는 RDS 의 news_ago 테이블을, carrier_maker.py 는 carrier 테이블을 업데이트함.
 SHIP 은 사용자 신호를 직접 받지 않음.

## SON
 ALB에 연결돼 상용자 신호를 직접 받는 서버임. request 의 파라미터 'server' 값이 1이면 1번 서버에, 2번이면 2번 서버에 request가 전달됨.  파라미터 server 값은 사용자의 ga 끝번호의 홀/짝 여부에 따라 결정됨. 이는 한 사용자는 한 개의 서버와만 상호작용하도록 하기 위한 장치임.
 SON의 systemctl 에는 두가지 서비스( son_updater.service,  news_recommend.service) 가 enabled 돼있음. son_updater은 'son_updater.py'를 구동하며, 2분에 한번씩 RDS로부터 최신 데이터를 가져와 내부의 redis DB를 업데이트하는 장치임. news_recommend는 'main.py' 를 구동하며,  gunicorn 을 통해 fastapi 서버를 동작시키는 역할을 함. gunicorn 설정은 2 workers(멀티프로세싱)임.

 main.py는 SON 내부의 메모리 기반 DB인 redis와 주로 소통하며, redis는 총 4개(0~3) DB로 구성됨.
-DB0 : 기사 일련번호(gid)와 그에 상응하는 벡터가 키-벨류 페어로 담겨있음.
-DB1 : 사용자 식별번호(ga)와 그에 상응하는 벡터가 키-벨류 페어로 담겨있음. 저장된 키값은 30일 후 자동 expire됨.
-db2 : 추천목록 값들이 저장됨.	
	'mat' : 2000*50 매트릭스가 byte 형태로 저장됨. np.frombuffer() 을 통해 디코드. 2000개 기사의 50차원 행렬을 합친 것.
	'gid' : mat 의 2000개 기사에 상응하는 gid 번호 리스트가 byte 형태로 저장.
	'title' :  mat 기사의 제목
	'url', 'thumurl' : mat 기사의 url과 썸네일 url.
	'temp : 사용자가 송신한 ga, gid에 해당하는 벡터가 없을 때, 아무 정보가 없는 상태에서 추천을 하기 위해 임의로 부여한 벡터. 현재 무작위 벡터를 부여하고 있으나 향후 QE 모델 등을 도입할 예정
-db3 : 사용자 로그기록이 저장됨. 가장 마지막 접속 후 10분 뒤 자동 expire됨. 파이썬 패키지인 'collections.defaultdict' 형식의 자료가 'pickle'을 통해 인코딩돼 저장됨.

## RDB
 # news_ago 
 SON의 DB0에 넣기 위한 자료. 테이블 에는 2달여간의 기사목록과 이들의 메타데이터, 형태소 변환 데이터, 벡터 변환 데이터가 저장돼있음. 
 - 칼럼 gid ~ cate_code 는 동아닷컴 송신 정보와 동일. length 는 content의 글자 수. konlpy는 기사 본문인 content를 형태소 변환한 리스트를 blob 형태로 변환시켜 저장. vec은 형태소 변환 리스트를 Doc2vec 모델에 넣어 벡터 변환한 numpy.array 를 blob 형태로 저장함.
- news_ago 의 기사 중 시간 순 900개 (동아일보 400, 이외 500)를 가져와 carrier 내용을 만듦.
  
 #carrier
-SON 의 DB2 내용을 만듦. mat, gid, title, url, temp 등. numpy array 가 blob 형태로 저장됨.


#### 설치방법
### SHIP
$sudo  apt install python3.11 redis-server mysql-server python3.11-venv
$sudo systemctl disable mysql  # mysqld 가 메모리 부하를 차지하므로 diable 시켜줌
$sudo apt install openjdk-8-jdk
   => $ export JAVA_HOME=<which java 경로>
$mkdir /home/donga/projects/news_rec_SHIP
$ cd /home/donga/projects/news_rec_SHIP

해당 폴더에 git clone 실시.
remote : https://github.com/suhcrates-web/news_rec_SHIP.git

이후 해당 폴더에 virtual environment 구성.
$ python3.11 -m venv venv   
$ source venv/bin/activate   # venv 활성화 후 python3.11 패키지를 설치해야 함.
$ pip3.11 install requests numpy konlpy gensim mysql-connector-python
$ sudo vi database.py   # mysql config 파일을 직접 만들어야
==============
import mysql.connector
config = {
'user' : 'root',
'password': 'dlftks44#',
'host' : 'dongailboars-rds.cluster-cr2zqjzbyiqo.ap-northeast-2.rds.amazonaws.com',
'port' : '3306'
}
===================

# 데이터베이스 세팅
create_db_and_table.py -> crawl_30.py -> proto_mysql_maker_1.py 
-> install_systemctl.py : systemctl 구성 후 가동.

### SON
$sudo  apt install python3.11 redis-server mysql-server python3.11-venv
$sudo systemctl disable mysql  # mysqld 가 메모리 부하를 차지하므로 diable 시켜줌
$mkdir /home/donga/projects/news_rec_SON
$ cd /home/donga/projects/news_rec_SON

$ python3.11 -m venv venv   
$ source venv/bin/activate 
$ pip3.11 install requests numpy fastapi redis uvicorn gunicorn mysql-connector-python
$ sudo vi database.py

# 세팅
proto_redis_maker.py -> install_systemctl_son_updater.py -> install_systemctl_main.py