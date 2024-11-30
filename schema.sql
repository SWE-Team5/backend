drop table if exists user;
drop table if exists description_texts;
create table user (
  id integer primary key autoincrement,
  user_id varchar(45) not null,
  student_id integer not null,
  department integer not null,
  user_name varchar(255) not null,
  semester integer not null,
  email varchar(30) not null, 
  phone varchar(20),
  multi_major integer not null,
  password_hash varchar(255) not null,
  alarm integer not null
);
INSERT INTO user (user_id, student_id, department, user_name, semester, email, phone, multi_major, password_hash, alarm) VALUES
('john_doe', 2023123456, 101, 'John Doe', 3, 'john.doe@example.com', '010-1234-5678', 0, 'hashed_password_1', 1),
('jane_smith', 2023765432, 102, 'Jane Smith', 2, 'jane.smith@example.com', '010-9876-5432', 1, 'hashed_password_2', 0),
('alice_wong', 2023987654, 103, 'Alice Wong', 4, 'alice.wong@example.com', '010-1111-2222', 0, 'hashed_password_3', 1),
('bob_jones', 2023456789, 104, 'Bob Jones', 1, 'bob.jones@example.com', '010-3333-4444', 1, 'hashed_password_4', 0),
('charlie_lee', 2023123987, 105, 'Charlie Lee', 3, 'charlie.lee@example.com', '010-5555-6666', 0, 'hashed_password_5', 1),
('david_kim', 2023789654, 106, 'David Kim', 2, 'david.kim@example.com', '010-7777-8888', 0, 'hashed_password_6', 0),
('eva_green', 2023897654, 107, 'Eva Green', 4, 'eva.green@example.com', '010-9999-0000', 1, 'hashed_password_7', 1),
('frank_zhou', 2023245687, 108, 'Frank Zhou', 1, 'frank.zhou@example.com', '010-2222-3333', 0, 'hashed_password_8', 0),
('grace_park', 2023765891, 109, 'Grace Park', 2, 'grace.park@example.com', '010-4444-5555', 1, 'hashed_password_9', 1),
('hannah_kim', 2023124567, 110, 'Hannah Kim', 3, 'hannah.kim@example.com', '010-6666-7777', 0, 'hashed_password_10', 1);

-- 사용자 관심 키워드 테이블
DROP TABLE IF EXISTS user_keywords;
CREATE TABLE user_keywords (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  keyword VARCHAR(255) NOT NULL,
  isCalendar INTEGER NOT NULL,  -- BOOLEAN 대체 (0과 1)
  FOREIGN KEY (user_id) REFERENCES user (id)
);

-- 사용자 공지 읽음 테이블
DROP TABLE IF EXISTS user_notifications;
CREATE TABLE user_notifications (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  noti_id INTEGER NOT NULL,
  keyword_id INTEGER NULL,
  is_read INTEGER NOT NULL,  -- BOOLEAN 대체 (0과 1)
  scrap INTEGER NOT NULL,  -- BOOLEAN 대체 (0과 1),
  UNIQUE(noti_id, keyword_id)
  FOREIGN KEY (user_id) REFERENCES user (id),
  FOREIGN KEY (noti_id) REFERENCES notifications (id),
  FOREIGN KEY (keyword_id) REFERENCES user_keywords (id)
);

-- 전체 공지 목록 테이블
DROP TABLE IF EXISTS notifications;
CREATE TABLE notifications (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title VARCHAR(255) NOT NULL,
  noti_url VARCHAR(255) NOT NULL,
  noti_id INTEGER NOT NULL UNIQUE
);


-- 사용자 관심 키워드 테이블에 한글 키워드 더미 데이터 삽입
INSERT INTO user_keywords (user_id, keyword, isCalendar) VALUES
(1, '컴퓨터공학', 1),
(1, '인공지능 연구', 0),
(2, '수학', 1),
(2, '통계학', 0),
(3, '생물학', 1),
(3, '유전학', 0),
(4, '물리학', 1),
(4, '양자역학', 0),
(5, '문학', 1),
(5, '창작 글쓰기', 0),
(6, '화학', 1),
(6, '유기화학', 0),
(7, '경제학', 1),
(7, '재무', 0),
(8, '역사학', 1),
(8, '고고학', 0),
(9, '공학', 1),
(9, '기계공학', 0),
(10, '미술', 1),
(10, '사진술', 0);
