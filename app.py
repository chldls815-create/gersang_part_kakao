from flask import Flask, request, jsonify
import sqlite3

app = Flask(__name__)

# ==========================================
# 1. 데이터베이스 초기화 (users 테이블 추가)
# ==========================================
def init_db():
    conn = sqlite3.connect('party.db')
    c = conn.cursor()
    
    # 닉네임 저장 테이블
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            kakao_id TEXT PRIMARY KEY,
            nickname TEXT NOT NULL
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS parties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            host_name TEXT NOT NULL,
            party_type TEXT NOT NULL,
            status TEXT DEFAULT '모집중'
        )
    ''')
    
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

init_db()

# ------------------------------------------
# [헬퍼 함수] 카카오 ID로 닉네임 찾아오기
# ------------------------------------------
def get_user_nickname(kakao_id):
    conn = sqlite3.connect('party.db')
    c = conn.cursor()
    c.execute("SELECT nickname FROM users WHERE kakao_id=?", (kakao_id,))
    row = c.fetchone()
    conn.close()
    
    if row:
        return row[0]
    return None # 등록된 닉네임이 없으면 None 반환


# ==========================================
# 2. 닉네임 등록/변경 처리 로직 (신규)
# ==========================================
@app.route('/set_nickname', methods=['POST'])
def set_nickname():
    try:
        req = request.get_json()
        user_id = req.get('userRequest', {}).get('user', {}).get('id')
        
        # 오픈빌더에서 설정할 파라미터 이름 'user_nickname'
        new_nickname = req.get('action', {}).get('params', {}).get('user_nickname')

        if not new_nickname:
            return jsonify({"version": "2.0", "template": {"outputs": [{"simpleText": {"text": "닉네임을 인식하지 못했습니다. 다시 시도해 주세요."}}]}})

        conn = sqlite3.connect('party.db')
        c = conn.cursor()
        # REPLACE INTO: 이미 같은 kakao_id가 있으면 덮어쓰고, 없으면 새로 삽입
        c.execute('REPLACE INTO users (kakao_id, nickname) VALUES (?, ?)', (user_id, new_nickname))
        conn.commit()
        conn.close()

        return jsonify({
            "version": "2.0",
            "template": {
                "outputs": [{"simpleText": {"text": f"✅ 닉네임이 [{new_nickname}]으로 성공적으로 등록되었습니다!\n이제 파티 시스템을 정상적으로 이용하실 수 있습니다."}}]
            }
        })
    except Exception as e:
        return jsonify({"version": "2.0", "template": {"outputs": [{"simpleText": {"text": f"오류 발생: {str(e)}"}}]}})


# ==========================================
# 3. 메인 메뉴 (닉네임 등록 버튼 추가)
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
                        "description": "닉네임을 먼저 등록하신 후 이용해 주세요.",
                        "buttons": [
                            {"label": "👤 내 닉네임 등록", "action": "block", "blockId": "6a4bbd4b178bd9946a57a0af"},
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
# 4. 파티 생성 메뉴 (기존과 동일하되 참여버튼 뺌)
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
                            "buttons": [{"label": "이 파티 생성하기", "action": "block", "blockId": "6a4ba2cde923a8b8de49b6dc", "extra": {"party_type": "제천대성"}}]
                        },
                        {
                            "title": "🔥 나타의 시련 (쉬움)",
                            "description": "총 5명 참여 가능\n(4가지 역할 선택 필수)",
                            "buttons": [{"label": "이 파티 생성하기", "action": "block", "blockId": "6a4ba2cde923a8b8de49b6dc", "extra": {"party_type": "나타(쉬움)"}}]
                        },
                        {
                            "title": "🌋 나타의 시련 (어려움)",
                            "description": "총 5명 참여 가능\n(4가지 역할 선택 필수)",
                            "buttons": [{"label": "이 파티 생성하기", "action": "block", "blockId": "6a4ba2cde923a8b8de49b6dc", "extra": {"party_type": "나타(어려움)"}}]
                        }
                    ]
                }
            }]
        }
    })


# ==========================================
# 5. 실제 파티 생성 처리 로직
# ==========================================
@app.route('/create_party_action', methods=['POST'])
def create_party_action():
    try:
        req = request.get_json()
        user_id = req.get('userRequest', {}).get('user', {}).get('id')
        
        # DB에서 등록된 닉네임 찾기
        host_name = get_user_nickname(user_id)
        if not host_name:
            return jsonify({"version": "2.0", "template": {"outputs": [{"simpleText": {"text": "⚠️ 닉네임이 등록되어 있지 않습니다.\n메인 메뉴에서 [내 닉네임 등록]을 먼저 진행해 주세요."}}]}})

        client_extra = req.get('action', {}).get('clientExtra', {})
        party_type = client_extra.get('party_type', '제천대성')

        conn = sqlite3.connect('party.db')
        c = conn.cursor()
        c.execute('INSERT INTO parties (host_name, party_type, status) VALUES (?, ?, ?)', (host_name, party_type, '모집중'))
        party_id = c.lastrowid
        c.execute('INSERT INTO party_members (party_id, member_name, role) VALUES (?, ?, ?)', (party_id, host_name, '파티장'))
        conn.commit()
        conn.close()

        msg = f"✨ 새로운 파티가 생성되었습니다! ✨\n\n👑 파티장: {host_name}\n⚔️ 종류: {party_type}\n\n📢 상단원분들은 [파티 목록]을 눌러 참여해 주세요!"
        return jsonify({"version": "2.0", "template": {"outputs": [{"simpleText": {"text": msg}}]}})
    except Exception as e:
        return jsonify({"version": "2.0", "template": {"outputs": [{"simpleText": {"text": f"오류 발생: {str(e)} "}}]}})


# ==========================================
# 6. 파티 목록 조회 로직
# ==========================================
@app.route('/get_parties', methods=['POST'])
def get_parties():
    try:
        conn = sqlite3.connect('party.db')
        c = conn.cursor()
        c.execute("SELECT id, host_name, party_type FROM parties WHERE status='모집중'")
        active_parties = c.fetchall()
        
        if not active_parties:
            return jsonify({"version": "2.0", "template": {"outputs": [{"simpleText": {"text": "현재 모집 중인 파티가 없습니다.\n[파티 생성]으로 파티를 만들어보세요!"}}]}})

        items = []
        for party in active_parties:
            p_id, host_name, p_type = party
            c.execute("SELECT member_name, role FROM party_members WHERE party_id=?", (p_id,))
            members = c.fetchall()
            
            member_text = ""
            for m in members:
                member_text += f" - {m[0]} ({m[1]})\n"
                
            items.append({
                "title": f"[{p_id}번 방] {p_type}",
                "description": f"👑 방장: {host_name}\n👥 인원: {len(members)}/5\n\n[현재 참여자]\n{member_text.strip()}",
                "buttons": [
                    {"label": "참여하기", "action": "block", "blockId": "6a4b4801ac0ed0806edc10cd", "extra": {"party_id": p_id, "party_type": p_type}},
                    {"label": "참여 취소 (탈퇴)", "action": "block", "blockId": "6a4bb2f23fe8be19e9ebaf65", "extra": {"party_id": p_id}}
                ]
            })
        conn.close()
        return jsonify({"version": "2.0", "template": {"outputs": [{"carousel": {"type": "basicCard", "items": items}}]}})
    except Exception as e:
        return jsonify({"version": "2.0", "template": {"outputs": [{"simpleText": {"text": f"오류 발생: {str(e)} "}}]}})


# ==========================================
# 7. 파티 참여 및 역할 선택 로직
# ==========================================
@app.route('/join_party', methods=['POST'])
def join_party():
    try:
        req = request.get_json()
        user_id = req.get('userRequest', {}).get('user', {}).get('id')
        
        # 닉네임 확인
        user_name = get_user_nickname(user_id)
        if not user_name:
            return jsonify({"version": "2.0", "template": {"outputs": [{"simpleText": {"text": "⚠️ 닉네임이 등록되어 있지 않습니다.\n메인 메뉴에서 [내 닉네임 등록]을 먼저 진행해 주세요."}}]}})

        client_extra = req.get('action', {}).get('clientExtra', {})
        party_id = client_extra.get('party_id')
        party_type = client_extra.get('party_type')
        chosen_role = client_extra.get('chosen_role')

        conn = sqlite3.connect('party.db')
        c = conn.cursor()

        c.execute("SELECT id FROM party_members WHERE party_id=? AND member_name=?", (party_id, user_name))
        if c.fetchone() and not chosen_role:
            conn.close()
            return jsonify({"version": "2.0", "template": {"outputs": [{"simpleText": {"text": "⚠️ 이미 이 파티에 참여 중입니다!"}}]}})

        if party_type == '제천대성':
            c.execute("SELECT COUNT(*) FROM party_members WHERE party_id=?", (party_id,))
            if c.fetchone()[0] >= 5:
                conn.close()
                return jsonify({"version": "2.0", "template": {"outputs": [{"simpleText": {"text": "❌ 정원이 가득 차서 참여할 수 없습니다."}}]}})

            c.execute("INSERT INTO party_members (party_id, member_name, role) VALUES (?, ?, ?)", (party_id, user_name, '파티원'))
            conn.commit()
            
            c.execute("SELECT COUNT(*) FROM party_members WHERE party_id=?", (party_id,))
            new_count = c.fetchone()[0]
            
            msg = f"🎉 {user_name}님이 [제천대성] 파티에 참여하셨습니다! ({new_count}/5)"
            if new_count == 5:
                msg += "\n\n🔥 정원이 모두 충족되어 파티가 완성되었습니다! 🔥"
            
            conn.close()
            return jsonify({"version": "2.0", "template": {"outputs": [{"simpleText": {"text": msg}}]}})

        else:
            if not chosen_role:
                c.execute("SELECT role FROM party_members WHERE party_id=?", (party_id,))
                taken_roles = [r[0] for r in c.fetchall()]
                
                all_roles = ['1.속성몹-水속 우선', '2.패턴+불사몹- 속성무관', '3.패턴+불사몹- 속성무관', '4.침식몹 (똘아리) - 속성 무관']
                available_roles = [r for r in all_roles if r not in taken_roles]

                if not available_roles:
                    conn.close()
                    return jsonify({"version": "2.0", "template": {"outputs": [{"simpleText": {"text": "❌ 모든 역할 자리가 가득 찼습니다."}}]}})

                role_cards = []
                for role in available_roles:
                    role_cards.append({
                        "title": f"🛡️ [{role}] 역할 선택",
                        "description": f"현재 {role} 자리가 비어있습니다. 참여하시겠습니까?",
                        "buttons": [{"label": f"{role}(으)로 참여하기", "action": "block", "blockId": "여기에_파티참여처리_블록ID입력", "extra": {"party_id": party_id, "party_type": party_type, "chosen_role": role}}]
                    })
                conn.close()
                return jsonify({"version": "2.0", "template": {"outputs": [{"carousel": {"type": "basicCard", "items": role_cards}}]}})

            else:
                c.execute("SELECT id FROM party_members WHERE party_id=? AND role=?", (party_id, chosen_role))
                if c.fetchone():
                    conn.close()
                    return jsonify({"version": "2.0", "template": {"outputs": [{"simpleText": {"text": f"❌ 다른 상단원이 방금 [{chosen_role}] 자리를 선점했습니다. 다시 시도해 주세요."}}]}})

                c.execute("INSERT INTO party_members (party_id, member_name, role) VALUES (?, ?, ?)", (party_id, user_name, chosen_role))
                conn.commit()

                c.execute("SELECT COUNT(*) FROM party_members WHERE party_id=?", (party_id,))
                new_count = c.fetchone()[0]

                msg = f"🎉 {user_name}님이 [{chosen_role}] 역할로 파티에 합류하셨습니다! ({new_count}/5)"
                if new_count == 5:
                    msg += "\n\n🔥 모든 역할이 충족되어 나타 파티가 완성되었습니다! 출발하세요! 🔥"
                    c.execute("UPDATE parties SET status='완성' WHERE id=?", (party_id,))
                    conn.commit()

                conn.close()
                return jsonify({"version": "2.0", "template": {"outputs": [{"simpleText": {"text": msg}}]}})

    except Exception as e:
        return jsonify({"version": "2.0", "template": {"outputs": [{"simpleText": {"text": f"오류 발생: {str(e)} "}}]}})

# ==========================================
# 8. 파티 탈퇴 및 취소 처리 로직
# ==========================================
@app.route('/leave_party', methods=['POST'])
def leave_party():
    try:
        req = request.get_json()
        user_id = req.get('userRequest', {}).get('user', {}).get('id')
        user_name = get_user_nickname(user_id)
        
        if not user_name:
            return jsonify({"version": "2.0", "template": {"outputs": [{"simpleText": {"text": "⚠️ 닉네임 등록이 필요합니다."}}]}})

        client_extra = req.get('action', {}).get('clientExtra', {})
        party_id = client_extra.get('party_id')

        conn = sqlite3.connect('party.db')
        c = conn.cursor()

        c.execute("SELECT role FROM party_members WHERE party_id=? AND member_name=?", (party_id, user_name))
        row = c.fetchone()
        
        if not row:
            conn.close()
            return jsonify({"version": "2.0", "template": {"outputs": [{"simpleText": {"text": "❌ 현재 이 파티에 참여하고 있지 않습니다."}}]}})

        user_role = row[0]

        if user_role == '파티장':
            c.execute("DELETE FROM party_members WHERE party_id=?", (party_id,))
            c.execute("UPDATE parties SET status='취소됨' WHERE id=?", (party_id,))
            msg = f"🗑️ 파티장 [{user_name}]님이 파티를 취소하여 방이 전면 해체되었습니다."
        else:
            c.execute("DELETE FROM party_members WHERE party_id=? AND member_name=?", (party_id, user_name))
            msg = f"🏃 [{user_name}]님이 파티 참여를 취소(탈퇴)하셨습니다. 빈자리가 다시 활성화됩니다."
            c.execute("UPDATE parties SET status='모집중' WHERE id=?", (party_id,))

        conn.commit()
        conn.close()
        return jsonify({"version": "2.0", "template": {"outputs": [{"simpleText": {"text": msg}}]}})
    except Exception as e:
        return jsonify({"version": "2.0", "template": {"outputs": [{"simpleText": {"text": f"오류 발생: {str(e)} "}}]}})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
