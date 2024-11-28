-- 전체 공지 목록 테이블에 성균관대 공지사항 더미 데이터 삽입
INSERT INTO notifications (title, noti_url) VALUES
('신입생 환영회 안내', 'https://skku.edu/notifications/welcome'),
('중간고사 일정 공지', 'https://skku.edu/notifications/midterm-schedule'),
('캠퍼스 시설 점검 안내', 'https://skku.edu/notifications/maintenance'),
('신규 강의 신청 안내', 'https://skku.edu/notifications/course-registration'),
('학사일정 휴일 공지', 'https://skku.edu/notifications/holiday'),
('도서관 운영 시간 변경', 'https://skku.edu/notifications/library-hours'),
('체육대회 일정 발표', 'https://skku.edu/notifications/sports-events'),
('취업 박람회 2024', 'https://skku.edu/notifications/career-fair'),
('보건소 서비스 업데이트', 'https://skku.edu/notifications/health-services'),
('동문회 모임 2024', 'https://skku.edu/notifications/alumni-meet');

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

-- 사용자 공지 읽음 테이블에 더미 데이터 삽입
INSERT INTO user_notifications (user_id, noti_id, keyword_id, is_read, scrap) VALUES
(1, 1, 1, 1, 0),
(1, 2, 2, 0, 1),
(2, 3, 3, 1, 0),
(2, 4, 4, 0, 1),
(3, 5, 5, 1, 0),
(3, 6, 6, 0, 1),
(4, 7, 7, 1, 0),
(4, 8, 8, 0, 1),
(5, 9, 9, 1, 0),
(5, 10, 10, 0, 1),
(6, 1, 11, 1, 0),
(6, 2, 12, 0, 1),
(7, 3, 13, 1, 0),
(7, 4, 14, 0, 1),
(8, 5, 15, 1, 0),
(8, 6, 16, 0, 1),
(9, 7, 17, 1, 0),
(9, 8, 18, 0, 1),
(10, 9, 19, 1, 0),
(10, 10, 20, 0, 1);