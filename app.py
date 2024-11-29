from contextlib import closing
from flask import Flask, request, render_template, jsonify, session, redirect, url_for
from flask_jwt_extended import *
from flask import g
import sqlite3
import datetime
import os, sys
import config
import vectorDB
from flask_cors import CORS

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from dotenv import load_dotenv

from document_loader import load_documents, create_vectorstore
from chatbot_logic import create_chatbot
from pinecone_to_txt import fetch_data_from_pinecone
from VDB.notice.test_query import pinecone_main

app = Flask(__name__)
CORS(app)

app.config.update(
    Debug=True,
    JWT_SECRET_KEY="ofians247g8awr"
    )

jwt = JWTManager(app)
jwt_blacklist = set()

################### initialize chatbot ###########################

# 환경 변수 로드 (OPENAI_API_KEY, PINECONE_API_KEY 등)
load_dotenv()

# 파인콘에서 데이터 가져오기
#fetch_data_from_pinecone()

# 문서 로드 및 벡터 스토어 생성 또는 업데이트
documents = load_documents('documents')  # 문서가 저장된 디렉토리
persist_directory = 'vectorstore'

# 벡터 스토어 생성 또는 업데이트
vectorstore = create_vectorstore(documents, persist_directory)
# 챗봇 생성
qa_chain = create_chatbot(vectorstore)

################### DB ############################
def init_db():
    if os.path.exists(app.config['DATABASE']):
        updateexist = os.path.exists(app.config['DB_SQL_UPDATE'])
        print('db updating...', updateexist)
        if updateexist:
            with closing(connect_db()) as db:
                with app.open_resource(app.config['DB_SQL_UPDATE']) as f:
                    sqlcmd = f.read().decode('utf-8')
                    print(sqlcmd)
                    db.cursor().executescript(sqlcmd)
                db.commit()
            print('updated db')
        return

    os.makedirs('db', exist_ok=True)

    with closing(connect_db()) as db:
        with app.open_resource(app.config['DB_SQL']) as f:
            db.cursor().executescript(f.read().decode('utf-8'))
        db.commit()

def load_db():
    cur = g.db.execute('select * from user order by id desc')
    entries = [dict(id=row[1], user_id=row[2], student_id=row[3], 
                department=row[4], user_name=row[5], semester=row[6]) for row in cur.fetchall()]
    print(entries)
    if len(entries) > 0:
        for entry in entries:
            print(entry)


@app.before_request
def before_request():
    g.db = connect_db()

@app.teardown_request
def teardown_request(exception):
    g.db.close()

def connect_db():
    return sqlite3.connect(app.config['DATABASE'])

##############################################################
@app.route('/')
def home():
    load_db()
    return 'Hello, World!'

@app.route('/test')
@jwt_required()
def test():

    current_user = get_jwt_identity()
    print(current_user)
    return render_template('test.html')

def update_notice_keyword_user(user_id, keyword_id, keyword_text):
    # 외부 함수에서 공지 목록을 가져옴
    notice_list = pinecone_main(keyword_text)
    # DB에서 해당 유저와 키워드에 대한 최신 공지 ID를 가져옴
    user_notice = g.db.execute(
        'SELECT MAX(noti_id) AS max_noti_id FROM user_notifications WHERE user_id = ? AND keyword_id = ?',
        (user_id, keyword_id)
    ).fetchone()
    max_noti_id = notice_list['matches'][0]['id'] if notice_list['matches'][0] is not None else 0
    
    # 업데이트할 새로운 공지를 필터링 (max_noti_id보다 큰 것들만)
    new_notices = [notice for notice in notice_list['matches'] if notice['id'] > max_noti_id]
    
    # 새로운 공지가 없다면 False 반환
    if not new_notices:
        return False
    
    # 새로운 공지를 user_notifications 테이블에 추가
    for notice in new_notices:
        # add to notification table also.
        g.db.execute(
            'INSERT INTO notifications (title, url) VALUES ( ?, ?)',
            (notice['title'], notice['url'])
        )
        g.db.execute(
            'INSERT INTO user_notifications (user_id, noti_id, keyword_id, read, scrap) VALUES (?, ?, ?, ?, ?)',
            (user_id, notice['id'], keyword_id, 0, 0)  # 초기값으로 읽음과 스크랩을 0으로 설정
        )
    
    # 변경 사항을 DB에 커밋
    g.db.commit()
    
    # 새로운 공지가 추가되었으므로 True 반환
    return True

################## User API ############################

@app.route('/user/login', methods=['POST'])
def login():
    input_data = request.get_json()
    user_id = input_data['id']
    user_pw = input_data['pw']
    #get_user_data_from_db = ["admin", "admin"]
    get_user_data_from_db = g.db.execute('select * from user where student_id = ?', (user_id,)).fetchone()

    if get_user_data_from_db is None:
        return jsonify({'msg': 'login fail'}), 401
    else:
        if user_pw == get_user_data_from_db[9]:
            print(get_user_data_from_db[0])
            access_token = create_access_token(identity=get_user_data_from_db[0], expires_delta=datetime.timedelta(minutes=10))
            return jsonify({'msg': 'login success', 'access_token': access_token}), 200
        else:
            return jsonify({'msg': 'login fail'}), 401

@app.route('/user/logout', methods=['POST'])
@jwt_required()
def logout():
    jti = get_jwt()['jti']

    jwt_blacklist.add(jti)
    return jsonify({'msg': 'logout success'}), 200

@app.route('/user/register', methods=['POST'])
def register():
    input_data = request.get_json()
    if 'user_id' not in input_data or 'student_id' not in input_data or 'department' not in input_data or 'user_name' not in input_data or 'semester' not in input_data or 'email' not in input_data or 'phone' not in input_data or 'user_pw_hash' not in input_data or 'alarm' not in input_data:
        return jsonify({'msg': 'missing parameter'}), 400
    user_id = input_data['user_id']
    student_id = input_data['student_id']
    department = input_data['department']
    user_name = input_data['user_name']
    semester = input_data['semester']
    email = input_data['email']
    phone = input_data['phone']
    multi_major = input_data['multi_major'] if 'multi_major' in input_data else None
    user_pw_hash = input_data['user_pw_hash']
    alarm = input_data['alarm']
    g.db.execute('insert into user (user_id, student_id, department, user_name, semester, email, phone, multi_major, user_pw_hash, alarm) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                 [user_id, student_id, department, user_name, semester, email, phone, multi_major, user_pw_hash, alarm])
    g.db.commit()

    return jsonify({'msg': 'register success'}), 200

@app.route('/user/register', methods=['PATCH'])
@jwt_required()
def update_user_info():
    input_data = request.get_json()
    if 'user_id' not in input_data:
        return jsonify({'msg': 'missing users id'}), 400
    user_id = input_data['user_id']
    student_id = input_data['student_id'] if 'student_id' in input_data else None
    department = input_data['department'] if 'department' in input_data else None
    user_name = input_data['user_name'] if 'user_name' in input_data else None
    semester = input_data['semester'] if 'semester' in input_data else None
    email = input_data['email'] if 'email' in input_data else None
    phone = input_data['phone'] if 'phone' in input_data else None
    multi_major = input_data['multi_major'] if 'multi_major' in input_data else None
    user_pw_hash = input_data['user_pw_hash'] if 'user_pw_hash' in input_data else None
    alarm = input_data['alarm'] if 'alarm' in input_data else None
    g.db.execute('update user set student_id = ?, department = ?, user_name = ?, semester = ?, email = ?, phone = ?, multi_major = ?, user_pw_hash = ?, alarm = ? where user_id = ?',
                 [student_id, department, user_name, semester, email, phone, multi_major, user_pw_hash, alarm, user_id])
    g.db.commit()

    return jsonify({'msg': 'update success'}), 200

@app.route('/user/keyword', methods=['GET'])
@jwt_required()
def get_users_notices():
    is_new = False
    data = []
    user_id = get_jwt_identity()
    print("#"*50)
    print(user_id)
    print("#"*50)
    if user_id is None:
        return jsonify({'msg': 'missing user id'}), 400
    
    # 모든 키워드를 가져오기 위해 fetchall() 사용
    keywords = g.db.execute('SELECT id, keyword FROM user_keywords WHERE user_id = ? AND isCalendar = false', (user_id,)).fetchall()
    if not keywords:
        return jsonify({'msg': 'no keyword'}), 200
    # 각 키워드에 대해 반복하면서 데이터 추가
    for keyword in keywords:
        print(keyword, keywords)
        # 여기서 keyword는 튜플(id, keyword, isCalendar)이므로 인덱스로 접근
        keyword_id = keyword[0]
        keyword_text = keyword[1]
        is_new |= update_notice_keyword_user(user_id, keyword_id, keyword_text)
        data.append({'keyword': keyword_text, 'keywordid': keyword_id, 'new': is_new})
    
    return jsonify({'count': len(keywords), 'data': data}), 200

@app.route('/user/keyword', methods=['POST'])
@jwt_required()
def register_keyword():
    user_id = get_jwt_identity()
    input_data = request.get_json()
    if user_id is None:
        return jsonify({'msg': 'missing user id'}), 400
    if 'keyword' not in input_data:
        return jsonify({'msg': 'missing keyword'}), 400
    keyword = input_data['keyword']
    if keyword is None:
        return jsonify({'msg': 'missing keyword'}), 400
    
    # user_keywords 테이블에 해당 유저와 키워드를 추가
    g.db.execute(
        'INSERT INTO user_keywords (user_id, keyword, isCalendar) VALUES (?, ?, ?)',
        (user_id, keyword, 0)
    )
    cursor = g.db.execute(
        'SELECT id FROM user_keywords WHERE user_id = ? AND keyword = ?',
        (user_id, keyword)
    )
    keyword_id = cursor.fetchone()[0]
    # 변경 사항을 DB에 커밋
    g.db.commit()
    
    # 추가 성공 메시지 반환
    return jsonify({'msg': 'regist keyword success', 'keyword_id':cursor}), 200

@app.route('/user/scrap', methods=['GET'])
@jwt_required()
def get_users_scrap_notices():
    user_id = get_jwt_identity()
    if user_id is None:
        return jsonify({'msg': 'missing user id'}), 400
    
    # 스크랩한 공지의 noti_id 목록을 가져옴
    notices = g.db.execute(
        'SELECT noti_id FROM user_notifications WHERE user_id = ? AND scrap = 1',
        (user_id,)
    ).fetchall()
    
    if not notices:
        return jsonify({'msg': 'no scrap notice'}), 200

    # 각 스크랩한 공지의 제목과 URL을 가져와 리스트에 추가
    data = []
    for notice in notices:
        noti_id = notice['noti_id']
        title_row = g.db.execute(
            'SELECT title, url FROM notice WHERE id = ?',
            (noti_id,)
        ).fetchone()
        
        # 제목과 URL이 없는 경우 기본값 설정 (예외 처리)
        title = title_row['title'] if title_row else 'No title available'
        url = title_row['url'] if title_row else 'No URL available'
        
        # 결과 리스트에 추가
        data.append({
            'noti_id': noti_id,
            'title': title,
            'url': url
        })
    
    return jsonify({'count': len(data), 'data': data}), 200

@app.route('/user/noti/<int:noticeid>', methods=['POST'])
@jwt_required()
def scrap_notice():
    user_id = get_jwt_identity()
    notice_id = request.view_args['noticeid']
    input_data = request.get_json()
    is_scrap = input_data['scrap']
    if user_id is None:
        return jsonify({'msg': 'missing user id'}), 400
    if notice_id is None:
        return jsonify({'msg': 'missing notice id'}), 400
    
    # user_notifications 테이블에서 해당 유저와 공지의 스크랩 여부를 변경
    g.db.execute(
        'UPDATE user_notifications SET scrap = ? WHERE user_id = ? AND noti_id = ?',
        (is_scrap, user_id, notice_id)
    )
    
    # 변경 사항을 DB에 커밋
    g.db.commit()
    
    # 스크랩 성공 메시지 반환
    return jsonify({'msg': 'scrap success'}), 200 

@app.route('/user/<int:keyword_id>', methods=['GET'])
@jwt_required()
def get_notice_list(keyword_id):
    user_id = get_jwt_identity()
    if user_id is None:
        return jsonify({'msg': 'missing user id'}), 400
    
    # user_notifications 테이블에서 해당 유저와 키워드에 대한 공지 목록을 가져옴
    notices = g.db.execute(
        'SELECT noti_id, is_read, scrap FROM user_notifications WHERE user_id = ? AND keyword_id = ?',
        (user_id, keyword_id)
    ).fetchall()
    
    if not notices:
        return jsonify({'msg': 'no notices found'}), 200

    # 각 공지에 대해 제목과 URL을 가져와 리스트에 추가
    data = []
    for notice in notices:
        noti_id = notice['noti_id']
        title_row = g.db.execute(
            'SELECT title, url FROM notice WHERE id = ?',
            (noti_id,)
        ).fetchone()
        
        # 제목과 URL이 없는 경우 기본값 설정 (예외 처리)
        title = title_row['title'] if title_row else 'No title available'
        url = title_row['url'] if title_row else 'No URL available'
        
        # 결과 리스트에 추가
        data.append({
            'noti_id': noti_id,
            'read': notice['read'],
            'scrap': notice['scrap'],
            'title': title,
            'url': url
        })
    
    return jsonify({'count': len(data), 'data': data}), 200

@app.route('/user/<int:keywordid>', methods=['DELETE'])
@jwt_required()
def delete_keyword():
    user_id = get_jwt_identity()
    keyword_id = request.view_args['keywordid']
    if user_id is None:
        return jsonify({'msg': 'missing user id'}), 400
    if keyword_id is None:
        return jsonify({'msg': 'missing keyword id'}), 400
    
    # user_keywords 테이블에서 해당 유저와 키워드를 삭제
    g.db.execute(
        'DELETE FROM user_notifications WHERE user_id = ? AND keyword_id = ?',
        (user_id, keyword_id)
    )
    g.db.execute(
        'DELETE FROM user_keywords WHERE user_id = ? AND id = ?',
        (user_id, keyword_id)
    )
    
    # 변경 사항을 DB에 커밋
    g.db.commit()
    
    # 삭제 성공 메시지 반환
    return jsonify({'msg': 'delete success'}), 200


@app.route('/user/<int:noticeid>', methods=['DELETE'])
@jwt_required()
def delete_notice():
    user_id = get_jwt_identity()
    notice_id = request.view_args['noticeid']
    if user_id is None:
        return jsonify({'msg': 'missing user id'}), 400
    if notice_id is None:
        return jsonify({'msg': 'missing notice id'}), 400
    
    # user_notifications 테이블에서 해당 유저와 공지를 삭제
    g.db.execute(
        'DELETE FROM user_notifications WHERE user_id = ? AND noti_id = ?',
        (user_id, notice_id)
    )
    
    # 변경 사항을 DB에 커밋
    g.db.commit()
    
    # 삭제 성공 메시지 반환
    return jsonify({'msg': 'delete success'}), 200


@app.route('/chat', methods=['POST'])
@jwt_required()
def get_chat():
    input_data = request.get_json()
    word = input_data['word']
    if word is None:
        return jsonify({'msg': 'missing word'}), 400
    from langchain.callbacks import get_openai_callback
    with get_openai_callback() as cb:
        response = qa_chain.run(word)
        # 토큰 사용량 출력 (옵션)
        print(f"토큰 사용량: {cb.total_tokens} (프롬프트: {cb.prompt_tokens}, 응답: {cb.completion_tokens})")

    return jsonify({'response': response}), 200

############## Flask App #####################
app.config.from_object(config)
app.secret_key = os.urandom(24)
init_db()

if __name__ == '__main__':
    connect_db()
    app.run(debug=True)
