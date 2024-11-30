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
    new_notices_before_process = notice_list["matches"]
    
    user_notice = g.db.execute(
        'SELECT noti_id FROM user_notifications WHERE user_id = ? AND keyword_id = ?',
        (user_id, keyword_id)
    ).fetchall()
    
    existing_notices = [notice[0] for notice in user_notice]
    
    # 새로운 공지가 이미 존재하는 경우 필터링
    new_notices = []
    for notice in new_notices_before_process:
        if int(notice['id']) not in existing_notices:
            new_notices.append(notice)


    # 새로운 공지가 없다면 False 반환
    if not new_notices:
        return False
    
    # 새로운 공지를 notifications 및 user_notifications 테이블에 추가
    for notice in new_notices:
        g.db.execute(
            'INSERT INTO notifications (title, noti_url, noti_id) VALUES (?, ?, ?)',
            (notice['metadata']['title'], notice['metadata']['url'], notice['id'])
        )
        g.db.execute(
            'INSERT INTO user_notifications (user_id, noti_id, keyword_id, is_read, scrap) VALUES (?, ?, ?, ?, ?)',
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

@app.route('/user/schedule', methods=['POST'])
@jwt_required()
def get_events_notices_list():
    user_id = get_jwt_identity()
    if user_id is None:
        return jsonify({'msg': 'missing user id'}), 400
    
    input_data = request.get_json()
    event = input_data['title']

    notices = pinecone_main(event)

    matched_notices = notices["matches"]
    data = []

    for notice in matched_notices:
        print(notice['metadata']['title'], notice['id'])
        # Check if the notice already exists in the notifications table
        existing_notice = g.db.execute(
            'SELECT * FROM notifications WHERE noti_id = ?',
            (notice['id'],)
        ).fetchone()
        
        # If the notice does not exist, insert it into the notifications table
        if not existing_notice:
            g.db.execute(
                'INSERT INTO notifications (title, noti_url, noti_id) VALUES (?, ?, ?)',
                (notice['metadata']['title'], notice['metadata']['url'], notice['id'])
            )
            g.db.execute(
                'INSERT INTO user_notifications (user_id, noti_id, keyword_id, is_read, scrap) VALUES (?, ?, ?, ?, ?)',
                (user_id, notice['id'], None, 0, 0)
            )
            g.db.commit()
        else:
            existing_user_notice = g.db.execute(
                'SELECT * FROM user_notifications WHERE user_id = ? AND noti_id = ?',
                (user_id, notice['id'])
            ).fetchone()
            if not existing_user_notice:
                g.db.execute(
                    'INSERT INTO user_notifications (user_id, noti_id, keyword_id, is_read, scrap) VALUES (?, ?, ?, ?, ?)',
                    (user_id, notice['id'], None, 0, 0)
                )
                g.db.commit()
        
        data.append({
            'noti_id': notice['id'],
            'title': notice['metadata']['title'],
            'url': notice['metadata']['url']
        })
    
    return jsonify({'count': len(data), 'data': data, 'msg': "get schedule-related notices success"}), 200

@app.route('/user/keyword', methods=['GET'])
@jwt_required()
def get_users_notices():
    is_new = False
    is_read = False
    data = []
    user_id = get_jwt_identity()
    if user_id is None:
        return jsonify({'msg': 'missing user id'}), 400
    
    # 모든 키워드를 가져오기 위해 fetchall() 사용
    keywords = g.db.execute('SELECT id, keyword FROM user_keywords WHERE user_id = ? AND isCalendar = false', (user_id,)).fetchall()
    if not keywords:
        return jsonify({'msg': 'no keyword'}), 200
    # 각 키워드에 대해 반복하면서 데이터 추가
    for keyword in keywords:
        # 여기서 keyword는 튜플(id, keyword, isCalendar)이므로 인덱스로 접근
        keyword_id = keyword[0]
        keyword_text = keyword[1]
        is_new |= update_notice_keyword_user(user_id, keyword_id, keyword_text)
        data.append({'keyword': keyword_text, 'keywordid': keyword_id, 'new': is_new, 'read' : is_new|is_read })
    
    return jsonify({'msg':"get registerd keyword success", 'count': len(keywords), 'data': data}), 200

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
    is_calendar = input_data['is_calendar']
    print(keyword)
    if keyword is None:
        return jsonify({'msg': 'missing keyword'}), 400
    
    # user_keywords 테이블에 해당 유저와 키워드를 추가
    g.db.execute(
        'INSERT INTO user_keywords (user_id, keyword, isCalendar) VALUES (?, ?, ?)',
        (user_id, keyword, is_calendar)
    )
    cursor = g.db.execute(
        'SELECT id FROM user_keywords WHERE user_id = ? AND keyword = ?',
        (user_id, keyword)
    ).fetchone()
    keyword_id = cursor[0]
    print(keyword_id)
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
        noti_id = notice[0]
        title_row = g.db.execute(
            'SELECT title, noti_url FROM notifications WHERE noti_id = ?',
            (noti_id,)
        ).fetchone()
        
        # 제목과 URL이 없는 경우 기본값 설정 (예외 처리)
        title = title_row[0] if title_row else 'No title available'
        url = title_row[1] if title_row else 'No URL available'
        
        # 결과 리스트에 추가
        data.append({
            'noti_id': noti_id,
            'title': title,
            'url': url
        })
    
    return jsonify({'count': len(data), 'data': data, 'msg': "get scrap notice success"}), 200

@app.route('/user/noti/<int:noticeid>', methods=['POST'])
@jwt_required()
def scrap_notice(noticeid):
    user_id = get_jwt_identity()
    notice_id = noticeid
    input_data = request.get_json()
    is_scrap = input_data['scrap']
    if user_id is None:
        return jsonify({'msg': 'missing user id'}), 400
    if notice_id is None:
        return jsonify({'msg': 'missing notice id'}), 400

        
    existing_user_notice = g.db.execute(
        'SELECT 1 FROM user_notifications WHERE user_id = ? AND noti_id = ?',
        (user_id, notice_id)
    ).fetchone()
    
    if not existing_user_notice:
        return jsonify({'msg': 'notice not found'}), 400
        
    g.db.execute(
        'UPDATE user_notifications SET scrap = ? WHERE user_id = ? AND noti_id = ?',
        (is_scrap, user_id, notice_id)
    )
    
    # 변경 사항을 DB에 커밋
    g.db.commit()
    
    # 스크랩 성공 메시지 반환
    return jsonify({'msg': 'scrap success'}), 200 

@app.route('/user/noti/<int:noticeid>', methods=['PATCH'])
@jwt_required()
def read_notice(noticeid):
    user_id = get_jwt_identity()
    notice_id = noticeid
    input_data = request.get_json()
    is_read = input_data['update'] == "read"
    if user_id is None:
        return jsonify({'msg': 'missing user id'}), 400
    if notice_id is None:
        return jsonify({'msg': 'missing notice id'}), 400
    
    # user_notifications 테이블에서 해당 유저와 공지의 읽음 여부를 변경
    existing_user_notice = g.db.execute(
        'SELECT 1 FROM user_notifications WHERE user_id = ? AND noti_id = ?',
        (user_id, notice_id)
    ).fetchone()
    
    if not existing_user_notice:
        return jsonify({'msg': 'notice not found'}), 400
    
    g.db.execute(
        'UPDATE user_notifications SET is_read = ? WHERE user_id = ? AND noti_id = ?',
        (1, user_id, notice_id)
    )
    
    # 변경 사항을 DB에 커밋
    g.db.commit()
    
    # 읽음 여부 변경 성공 메시지 반환
    return jsonify({'msg': 'read success'}), 200

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
        noti_id = notice[0]
        title_row = g.db.execute(
            'SELECT title, noti_url FROM notifications WHERE noti_id = ?',
            (noti_id,)
        ).fetchone()
        
        # 제목과 URL이 없는 경우 기본값 설정 (예외 처리)
        title = title_row[0] if title_row else 'No title available'
        url = title_row[1] if title_row else 'No URL available'
        
        # 결과 리스트에 추가
        data.append({
            'noti_id': noti_id,
            'read': notice[1],
            'scrap': notice[2],
            'title': title,
            'url': url
        })
    
    return jsonify({'count': len(data), 'data': data, 'msg':"get regist keyword notice success"}), 200

@app.route('/user/<int:keywordid>', methods=['DELETE'])
@jwt_required()
def delete_keyword(keywordid):
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


@app.route('/user/noti/<int:noticeid>', methods=['DELETE'])
@jwt_required()
def delete_notice(noticeid):
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
    notices_url = []
    if response.strip().split('\n')[-1] == '관련 공지사항:':
        for match in pinecone_main(word)["matches"] :
            notices_url.append(match['metadata']['url'])
    if len(notices_url) != 0:
        for i,url in enumerate(notices_url):
            if i == 3: break
            response = response + "\n" + url
    return jsonify({'response': response, 'msg': "chat response success"}), 200

############## Flask App #####################
app.config.from_object(config) 
app.secret_key = os.urandom(24)
init_db()

if __name__ == '__main__':
    connect_db()
    app.run(debug=True)
