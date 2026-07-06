from flask import Flask, request, jsonify
import sqlite3

app = Flask(__name__)

# ==========================================
# 1. 데이터베이스 초기화
# ==========================================
def init_db():
    conn = sqlite3.connect('party.db')
    c = conn.cursor()
    
    # 파티 기본 정보 테이블
    c.execute('''
        CREATE TABLE IF NOT EXISTS parties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            host_name TEXT NOT NULL,
            party_type TEXT NOT NULL,
            status TEXT DEFAULT '모집중'
        )
    ''')
    
    # 파티원 및 역할 정보 테이블
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


# ==========================================
# 2. 메인 메뉴
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
                                "blockId": "6a4ba2cde923a8b8de49b6dc", 
                                "extra": {"party_type": "제천대성"}
                            }]
                        },
                        {
                            "title": "🔥 나타의 시련 (쉬움)",
                            "description": "총 5명 참여 가능\n(4가지 역할 선택 필수)",
                            "buttons": [{
                                "label": "이 파티 생성하기",
                                "action": "block",
                                "blockId": "6a4ba2cde923a8b8de49b6dc", 
                                "extra": {"party_type": "나타(쉬움)"}
                            }]
                        },
                        {
                            "title": "🌋 나타의 시련 (어려움)",
                            "description": "총 5명 참여 가능\n(4가지 역할 선택 필수)",
                            "buttons": [{
                                "label": "이 파티 생성하기",
                                "action": "block",
                                "blockId": "6a4ba2cde923a8b8de49b6dc", 
                                "extra": {"party_type": "나타(어려움)"}
                            }]
                        }
                    ]
                }
            }]
        }
    })


# ==========================================
# 4. 실제 파티 생성 처리 로직
# ==========================================
@app.route('/create_party_action', methods=['POST'])
def create_party_action():
    try:
        req = request.get_json()
        user_properties = req.get('userRequest', {}).get('user', {}).get('properties', {})
        host_name = user_properties.get('nickname')
        if not host_name:
            user_id = req.get('userRequest', {}).get('user', {}).get('id', 'Unknown')
            host_name = f"상단원({user_id[:4]})"

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
# 5. 파티 목록 조회 로직 (탈퇴 버튼 추가)
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
                    {
                        "label": "참여하기",
                        "action": "block",
                        "blockId": "6a4b4801ac0ed0806edc10cd", # 중요
                        "extra": {"party_id": p_id, "party_type": p_type}
                    },
                    {
                        "label": "참여 취소 (탈퇴)",
                        "action": "block",
                        "blockId": "6a4bb2f23fe8be19e9ebaf65", # 중요 (새로 생성해야 함)
                        "extra": {"party_id": p_id}
                    }
                ]
            })
        conn.close()
        return jsonify({"version": "2.0", "template": {"outputs": [{"carousel": {"type": "basicCard", "items": items}}]}})
    except Exception as e:
        return jsonify({"version": "2.0", "template": {"outputs": [{"simpleText": {"text": f"오류 발생: {str(e)} "}}]}})


# ==========================================
# 6. 파티 참여 및 역할 선택 로직 (핵심)
# ==========================================
@app.route('/join_party', methods=['POST'])
def join_party():
    try:
        req = request.get_json()
        user_properties = req.get('userRequest', {}).get('user', {}).get('properties', {})
        user_name = user_properties.get('nickname')
        if not user_name:
            user_id = req.get('userRequest', {}).get('user', {}).get('id', 'Unknown')
            user_name = f"상단원({user_id[:4]})"
            
        client_extra = req.get('action', {}).get('clientExtra', {})
        party_id = client_extra.get('party_id')
        party_type = client_extra.get('party_type')
        chosen_role = client_extra.get('chosen_role') # 사용자가 고른 역할 (있을 수도, 없을 수도 있음)

        conn = sqlite3.connect('party.db')
        c = conn.cursor()

        # [공통 체크] 이미 방에 참여 중인지 확인
        c.execute("SELECT id FROM party_members WHERE party_id=? AND member_name=?", (party_id, user_name))
        if c.fetchone() and not chosen_role:
            conn.close()
            return jsonify({"version": "2.0", "template": {"outputs": [{"simpleText": {"text": "⚠️ 이미 이 파티에 참여 중입니다!"}}]}})

        # ------------------------------------------
        # CASE A: 역할 구분이 없는 [제천대성] 파티 처리
        # ------------------------------------------
        if party_type == '제천대성':
            c.execute("SELECT COUNT(*) FROM party_members WHERE party_id=?", (party_id,))
            current_count = c.fetchone()[0]
            if current_count >= 5:
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

        # ------------------------------------------
        # CASE B: 역할 선택이 필요한 [나타의 시련] 파티 처리
        # ------------------------------------------
        else:
            # 1단계: 사용자가 아직 역할을 고르지 않고 그냥 '참여하기'만 누른 상태인 경우
            if not chosen_role:
                c.execute("SELECT role FROM party_members WHERE party_id=?", (party_id,))
                taken_roles = [r[0] for r in c.fetchall()]
                
                # 가용 역할 정의 (원하는 명칭으로 수정 가능)
                all_roles = ['1.속성몹+水속우선', '2.패턴+불사몹(속성무관)', '3.패턴+불사몹(속성무관)', '침식몹(속성무관)']
                available_roles = [r for r in all_roles if r not in taken_roles]

                if not available_roles:
                    conn.close()
                    return jsonify({"version": "2.0", "template": {"outputs": [{"simpleText": {"text": "❌ 모든 역할 자리가 가득 찼습니다."}}]}})

                # 비어 있는 역할들을 Carousel 카드로 구성하여 사용자에게 보여줌
                role_cards = []
                for role in available_roles:
                    role_cards.append({
                        "title": f"🛡️ [{role}] 역할 선택",
                        "description": f"현재 {role} 자리가 비어있습니다. 참여하시겠습니까?",
                        "buttons": [{
                            "label": f"{role}(으)로 참여하기",
                            "action": "block",
                            "blockId": "여기에_파티참여처리_블록ID입력", # 자기 자신 블록 ID를 다시 호출
                            "extra": {"party_id": party_id, "party_type": party_type, "chosen_role": role}
                        }]
                    })
                conn.close()
                return jsonify({"version": "2.0", "template": {"outputs": [{"carousel": {"type": "basicCard", "items": role_cards}}]}})

            # 2단계: 사용자가 비어있는 역할 카드를 보고 특정 역할을 최종 선택한 경우
            else:
                # 동시 선택 방지용 검증 (그새 자리가 찼는지 확인)
                c.execute("SELECT id FROM party_members WHERE party_id=? AND role=?", (party_id, chosen_role))
                if c.fetchone():
                    conn.close()
                    return jsonify({"version": "2.0", "template": {"outputs": [{"simpleText": {"text": f"❌ 다른 상단원이 방금 [{chosen_role}] 자리를 선점했습니다. 다시 시도해 주세요."}}]}})

                # 역할 추가 실행
                c.execute("INSERT INTO party_members (party_id, member_name, role) VALUES (?, ?, ?)", (party_id, user_name, chosen_role))
                conn.commit()

                c.execute("SELECT COUNT(*) FROM party_members WHERE party_id=?", (party_id,))
                new_count = c.fetchone()[0]

                msg = f"🎉 {user_name}님이 [{chosen_role}] 역할로 파티에 합류하셨습니다! ({new_count}/5)"
                if new_count == 5:
                    # 5명이 다 차면 자동으로 파티 완성 공지 출력
                    msg += "\n\n🔥 모든 역할이 충족되어 나타 파티가 완성되었습니다! 출발하세요! 🔥"
                    c.execute("UPDATE parties SET status='완성' WHERE id=?", (party_id,))
                    conn.commit()

                conn.close()
                return jsonify({"version": "2.0", "template": {"outputs": [{"simpleText": {"text": msg}}]}})

    except Exception as e:
        return jsonify({"version": "2.0", "template": {"outputs": [{"simpleText": {"text": f"오류 발생: {str(e)} "}}]}})


# ==========================================
# 7. 파티 탈퇴 및 취소 처리 로직 (새로 추가)
# ==========================================
@app.route('/leave_party', methods=['POST'])
def leave_party():
    try:
        req = request.get_json()
        user_properties = req.get('userRequest', {}).get('user', {}).get('properties', {})
        user_name = user_properties.get('nickname')
        if not user_name:
            user_id = req.get('userRequest', {}).get('user', {}).get('id', 'Unknown')
            user_name = f"상단원({user_id[:4]})"

        client_extra = req.get('action', {}).get('clientExtra', {})
        party_id = client_extra.get('party_id')

        conn = sqlite3.connect('party.db')
        c = conn.cursor()

        # 해당 파티에서 내 역할 찾기
        c.execute("SELECT role FROM party_members WHERE party_id=? AND member_name=?", (party_id, user_name))
        row = c.fetchone()
        
        if not row:
            conn.close()
            return jsonify({"version": "2.0", "template": {"outputs": [{"simpleText": {"text": "❌ 현재 이 파티에 참여하고 있지 않습니다."}}]}})

        user_role = row[0]

        if user_role == '파티장':
            # 방장이 취소한 경우 방 자체를 해체함
            c.execute("DELETE FROM party_members WHERE party_id=?", (party_id,))
            c.execute("UPDATE parties SET status='취소됨' WHERE id=?", (party_id,))
            msg = f"🗑️ 파티장 [{user_name}]님이 파티를 취소하여 방이 전면 해체되었습니다."
        else:
            # 일반 파티원이 취소한 경우 명단에서만 삭제
            c.execute("DELETE FROM party_members WHERE party_id=? AND member_name=?", (party_id, user_name))
            msg = f"🏃 [{user_name}]님이 파티 참여를 취소(탈퇴)하셨습니다. 빈자리가 다시 활성화됩니다."
            # 만약 '완성' 상태였다면 다시 '모집중'으로 되돌림
            c.execute("UPDATE parties SET status='모집중' WHERE id=?", (party_id,))

        conn.commit()
        conn.close()
        return jsonify({"version": "2.0", "template": {"outputs": [{"simpleText": {"text": msg}}]}})
    except Exception as e:
        return jsonify({"version": "2.0", "template": {"outputs": [{"simpleText": {"text": f"오류 발생: {str(e)} "}}]}})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
