from flask import Flask, request, jsonify
import sqlite3

app = Flask(__name__)

# ==========================================
# 1. 데이터베이스 초기화 (새로운 구조 적용)
# ==========================================
def init_db():
    conn = sqlite3.connect('party.db')
    c = conn.cursor()
    
    # 파티 기본 정보 테이블 (상태값 추가)
    c.execute('''
        CREATE TABLE IF NOT EXISTS parties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            host_name TEXT NOT NULL,
            party_type TEXT NOT NULL,
            status TEXT DEFAULT '모집중'
        )
    ''')
    
    # 파티원 및 역할 정보 테이블 (관계형 구조)
    c.execute('''
        CREATE TABLE IF NOT EXISTS party_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            party_id INTEGER,
            member_name TEXT NOT NULL,
            role TEXT,
            FOREIGN KEY(party_id) REFERENCES parties(id)
        )
    ''')
    conn.commit()
    conn.close()

# 서버 구동 시 DB 테이블 생성 확인
init_db()


# ==========================================
# 2. 메인 메뉴 (시작 화면 퀵리플라이 연결용)
# ==========================================
@app.route('/main_menu', methods=['POST'])
def main_menu():
    return jsonify({
        "version": "2.0",
        "template": {
            "outputs": [{
                "carousel": {
                    "type": "basicCard",
                    "items": [{
                        "title": "⚔️ 상단 파티 관리 메뉴",
                        "description": "원하시는 기능을 선택해주세요.",
                        "buttons": [
                            {"label": "📋 파티 목록", "action": "block", "blockId": "6a4b96222c03941dfb8faea2"},
                            {"label": "➕ 파티 생성", "action": "block", "blockId": "6a4b3ec99319fd65f569e167"},
                            {"label": "🏃 참여하기", "action": "block", "blockId": "6a4b4801ac0ed0806edc10cd"}
                        ]
                    }]
                }
            }]
        }
    })


# ==========================================
# 3. 파티 생성 메뉴 (종류 3가지 선택 화면)
# ==========================================
@app.route('/create_party_menu', methods=['POST'])
def create_party_menu():
    return jsonify({
        "version": "2.0",
        "template": {
            "outputs": [{
                "carousel": {
                    "type": "basicCard",
                    "items": [
                        {
                            "title": "🐒 제천대성",
                            "description": "파티장 포함 5명 참여 가능\n(역할 구분 없음)",
                            "buttons": [{
                                "label": "이 파티 생성하기",
                                "action": "block",
                                "blockId": "여기에_파티생성처리_블록ID입력",
                                "extra": {"party_type": "제천대성"}
                            }]
                        },
                        {
                            "title": "🔥 나타의 시련 (쉬움)",
                            "description": "총 5명 참여 가능\n(4가지 역할 선택 필수)",
                            "buttons": [{
                                "label": "이 파티 생성하기",
                                "action": "block",
                                "blockId": "여기에_파티생성처리_블록ID입력",
                                "extra": {"party_type": "나타(쉬움)"}
                            }]
                        },
                        {
                            "title": "🌋 나타의 시련 (어려움)",
                            "description": "총 5명 참여 가능\n(4가지 역할 선택 필수)",
                            "buttons": [{
                                "label": "이 파티 생성하기",
                                "action": "block",
                                "blockId": "여기에_파티생성처리_블록ID입력",
                                "extra": {"party_type": "나타(어려움)"}
                            }]
                        }
                    ]
                }
            }]
        }
    })


# ==========================================
# 4. [예정] 실제 파티 생성 처리 로직
# ==========================================
@app.route('/create_party_action', methods=['POST'])
def create_party_action():
    req = request.get_json()
    
    # 1. 카카오톡 유저 정보에서 닉네임 가져오기 (설정이 안 되어 있으면 기본값 지정)
    user_properties = req.get('userRequest', {}).get('user', {}).get('properties', {})
    host_name = user_properties.get('nickname', '상단원')
    
    if host_name == '상단원':
        # 동명이인 방지를 위해 닉네임이 없을 경우 고유 ID의 앞 4글자를 붙여줌
        user_id = req.get('userRequest', {}).get('user', {}).get('id', 'Unknown')
        host_name = f"상단원({user_id[:4]})"

    # 2. 버튼의 extra 데이터에서 어떤 파티 종류를 골랐는지 가져오기
    client_extra = req.get('action', {}).get('clientExtra', {})
    party_type = client_extra.get('party_type', '제천대성')

    # 3. DB에 파티 방을 만들고, 방장을 멤버로 자동 등록하기
    conn = sqlite3.connect('party.db')
    c = conn.cursor()
    
    # parties 테이블에 방 생성
    c.execute('INSERT INTO parties (host_name, party_type, status) VALUES (?, ?, ?)', 
              (host_name, party_type, '모집중'))
    party_id = c.lastrowid # 방금 생성된 파티의 고유 번호(ID)
    
    # party_members 테이블에 파티장을 '파티장' 역할로 등록
    c.execute('INSERT INTO party_members (party_id, member_name, role) VALUES (?, ?, ?)', 
              (party_id, host_name, '파티장'))
    
    conn.commit()
    conn.close()

    # 4. 채널(또는 채팅방)에 출력될 공지 메시지 구성
    msg = f"✨ 새로운 파티가 생성되었습니다! ✨\n\n" \
          f"👑 파티장: {host_name}\n" \
          f"⚔️ 종류: {party_type}\n\n" \
          f"📢 상단원분들은 하단의 [파티 목록보기] 버튼을 눌러 비어있는 역할에 참여해 주세요!"

    return jsonify({
        "version": "2.0",
        "template": {
            "outputs": [{
                "simpleText": {
                    "text": msg
                }
            }]
        }
    })


# ==========================================
# 5. [예정] 파티 목록 조회 로직
# ==========================================
@app.route('/get_parties', methods=['POST'])
def get_parties():
    # 새로운 DB 구조(parties + party_members)를 읽어와서 카드로 보여주는 기능을 짤 예정입니다.
    pass


# ==========================================
# 6. [예정] 파티 참여 및 역할 선택 로직
# ==========================================
@app.route('/join_party', methods=['POST'])
def join_party():
    # 빈자리를 확인하고, 역할을 선택하여 DB에 등록하는 기능을 짤 예정입니다.
    pass


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
