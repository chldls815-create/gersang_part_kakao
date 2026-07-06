import os
import sqlite3
from flask import Flask, request, jsonify

app = Flask(__name__)

# --------------------------------------------------
# 1. 데이터베이스 초기화 함수
# --------------------------------------------------
def init_db():
    conn = sqlite3.connect('party.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS parties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT, host TEXT, host_id INTEGER,
            max_1 INTEGER, max_2 INTEGER, max_3 INTEGER, max_4 INTEGER,
            max_normal INTEGER,
            mem_1 TEXT, mem_2 TEXT, mem_3 TEXT, mem_4 TEXT, 
            normal_members TEXT
        )
    ''')
    
    # [추가] 데이터가 아예 없을 때만 테스트용 데이터를 넣어줍니다.
    cursor.execute("SELECT COUNT(*) FROM parties")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO parties (title, host, max_normal, normal_members) VALUES (?, ?, ?, ?)", 
                       ('나타의 시련', '테스트방장', 4, '상단원1,상단원2'))
        conn.commit()
        
    conn.commit()
    conn.close()

# --------------------------------------------------
# 2. 파티 목록 조회 스킬 API (카카오톡 캐로셀 카드 형태로 응답)
# --------------------------------------------------
@app.route('/get_parties', methods=['POST'])
def get_parties():
    # 카카오톡 서버로부터 요청 데이터 수신
    req = request.get_json()
    
    conn = sqlite3.connect('party.db')
    cursor = conn.cursor()
    # 일반 파티(max_normal > 0) 목록을 가져옵니다.
    cursor.execute("SELECT id, title, host, max_normal, normal_members FROM parties WHERE max_normal > 0")
    parties = cursor.fetchall()
    conn.close()
    
    # 모집 중인 파티가 없을 때의 예외 응답
    if not parties:
        return jsonify({
            "version": "2.0",
            "template": {
                "outputs": [{
                    "simpleText": {
                        "text": "⚔️ 현재 모집 중인 일반 파티가 없습니다. 먼저 파티를 생성해 주세요!"
                    }
                }]
            }
        })

    # 카카오톡 캐로셀 카드에 들어갈 아이템 리스트 생성
    items = []
    for p in parties:
        p_id, title, host, max_normal, normal_members = p
        members = normal_members.split(',') if normal_members else []
        current_count = len(members)
        
        # 카카오톡 basicCard 포맷 구성
        items.append({
            "title": f"⚔️ {title}",
            "description": f"👑 파티장: {host}\n👥 인원: ({current_count}/{max_normal})\n📝 명단: {', '.join(members) or '없음'}",
            "buttons": [
                {
                    "label": "파티 참여하기",
                    "action": "block",
                    "blockId": "6a4b4801ac0ed0806edc10cd",  # 카카오 오픈빌더에서 생성할 '파티참여 블록'의 ID를 여기에 넣습니다.
                    "extra": {"party_id": p_id  # 버튼 클릭 시 서버로 다시 넘겨줄 파티 고유 ID
                    }
                }
            ]
        })
        
    return jsonify({
        "version": "2.0",
        "template": {
            "outputs": [{
                "carousel": {
                    "type": "basicCard",
                    "items": items
                }
            }]
        }
    })

# --------------------------------------------------
# 3. 파티 참여 처리 스킬 API (사용자 별명을 파싱하여 DB 업데이트)
# --------------------------------------------------
@app.route('/join_party', methods=['POST'])
def join_party():
    req = request.get_json()
    
    # 사용자가 누른 버튼의 extra 데이터(party_id) 추출
    party_id = req.get('action', {}).get('clientExtra', {}).get('party_id')
    
    # 카카오톡 사용자의 프로필 닉네임 추출 (등록되지 않은 경우 무명상단원)
    user_name = req.get('userRequest', {}).get('user', {}).get('properties', {}).get('nickname', '무명상단원')
    
    if not party_id:
        return jsonify({
            "version": "2.0",
            "template": {
                "outputs": [{
                    "simpleText": {
                        "text": "❌ 잘못된 요청입니다. 다시 시도해 주세요."
                    }
                }]
            }
        })
        
    conn = sqlite3.connect('party.db')
    cursor = conn.cursor()
    cursor.execute("SELECT title, max_normal, normal_members FROM parties WHERE id = ?", (party_id,))
    p = cursor.fetchone()
    
    if not p:
        conn.close()
        return jsonify({
            "version": "2.0",
            "template": {
                "outputs": [{
                    "simpleText": {
                        "text": "❌ 존재하지 않거나 이미 삭제된 파티입니다."
                    }
                }]
            }
        })
        
    title, max_normal, normal_members = p
    members = normal_members.split(',') if normal_members else []
    
    # 중복 참여 검사
    if user_name in members:
        conn.close()
        return jsonify({
            "version": "2.0",
            "template": {
                "outputs": [{
                    "simpleText": {
                        "text": f"⚠️ {user_name}님은 이미 [{title}] 파티에 참여 중입니다!"
                    }
                }]
            }
        })
        
    # 인원 초과 검사
    if len(members) >= max_normal:
        conn.close()
        return jsonify({
            "version": "2.0",
            "template": {
                "outputs": [{
                    "simpleText": {
                        "text": f"❌ 정원이 가득 차서 [{title}] 파티에 참여할 수 없습니다."
                    }
                }]
            }
        })
        
    # 명단 업데이트 및 저장
    members.append(user_name)
    new_members_str = ",".join(members)
    cursor.execute("UPDATE parties SET normal_members = ? WHERE id = ?", (new_members_str, party_id))
    conn.commit()
    
    # 마감 조건 확인
    is_full = len(members) == max_normal
    msg = f"🎉 {user_name}님이 [{title}] 파티에 참여하셨습니다!\n👥 현재 인원: ({len(members)}/{max_normal})"
    
    if is_full:
        msg += f"\n\n📢 **[{title}] 파티 모집이 마감되었습니다! 파티원들은 출발 준비를 해주세요!**"
        
    conn.close()
    
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

# --------------------------------------------------
# 4. 서버 구동
# --------------------------------------------------
if __name__ == '__main__':
    init_db()  # 서버 켜질 때 DB가 없으면 자동 생성
    # 외부 호스팅 환경(Render 등)에 맞춰 0.0.0.0 주소 및 포트 바인딩
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
