import streamlit as st
import pandas as pd
import random
import json
import os
import re
from datetime import datetime, timedelta
from collections import defaultdict

st.set_page_config(page_title="笨鸟四级", page_icon="🐢", layout="wide")

# ---------- 初始化 session_state ----------
def init_session_state():
    defaults = {
        'review_list': [], 'review_idx': 0, 'show_answer': False,
        'dict_items': [], 'dict_idx': 0, 'dict_correct': 0, 'dict_done': False,
        'dict_show_res': False, 'dict_res_correct': False, 'user_ans': '',
        'show_guide': True, 'night_mode': False,
        'trans_bank': [], 'current_trans_q': None,
        'trans_submitted': False, 'trans_score_detail': None,
        'trans_user_input': '',
        'review_shuffle_seed': random.randint(1, 10000),
        'meaning_test_active': False, 'meaning_test_word': None,
        'meaning_user_input': '', 'meaning_test_result': None,
        'mastered_records': {},
        'perfect_words': [],
        'current_day_review': None,
        'day_review_idx': 0,
        'day_review_items': [],
        'day_review_correct': 0,
        'learning_start_date': None
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session_state()

# ---------- 样式 ----------
night_css = """
<style>
    body { background-color: #1e1e1e; color: #e0e0e0; }
    .stButton>button { background-color: #333; color: white; border: 1px solid #555; }
    .stTextInput>div>div>input { background-color: #2d2d2d; color: white; }
    .stTextArea>div>textarea { background-color: #2d2d2d; color: white; }
</style>
""" if st.session_state.night_mode else ""

st.markdown(f"""
<style>
    body {{ background-color: {'#1e1e1e' if st.session_state.night_mode else '#fafafa'}; }}
    .main {{ color: {'#e0e0e0' if st.session_state.night_mode else '#1e1e1e'}; }}
    .big-word {{ font-size: 3.5rem; font-weight: bold; text-align: center; margin: 10px 0; }}
    .phonetic {{ font-size: 1.4rem; color: #2c7da0; text-align: center; }}
    .pos-tag {{ background-color: #d32f2f; color: white; padding: 4px 12px; border-radius: 20px; display: inline-block; }}
    .meaning {{ font-size: 1.8rem; margin: 10px 0; }}
    .mindmap-box {{ background-color: {'#1a2a3a' if st.session_state.night_mode else '#f9f9f9'}; padding: 20px; border-radius: 20px; margin: 15px 0; border: 1px solid {'#444' if st.session_state.night_mode else '#e0e0e0'}; }}
    .mindmap-title {{ font-size: 1.2rem; font-weight: bold; margin-bottom: 10px; color: #2c7da0; }}
    .mindmap-item {{ display: inline-block; padding: 6px 14px; margin: 4px; border-radius: 20px; background-color: {'#333' if st.session_state.night_mode else '#fff'}; border: 1px solid {'#555' if st.session_state.night_mode else '#ddd'}; }}
    .mindmap-phrase {{ background: linear-gradient(135deg, {'#3a2a1a' if st.session_state.night_mode else '#fff3e0'}, {'#4a3a2a' if st.session_state.night_mode else '#ffe0b2'}); border-left: 4px solid #ff9800; }}
    .mindmap-family {{ background: linear-gradient(135deg, {'#1e3a1e' if st.session_state.night_mode else '#e8f5e9'}, {'#2e4a2e' if st.session_state.night_mode else '#c8e6c9'}); border-left: 4px solid #4caf50; }}
    .mindmap-example {{ background: linear-gradient(135deg, {'#3a1a2a' if st.session_state.night_mode else '#fce4ec'}, {'#4a2a3a' if st.session_state.night_mode else '#f8bbd0'}); border-left: 4px solid #e91e63; }}
    .phrase-important {{ background-color: #d32f2f; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.7rem; margin-left: 6px; }}
    .day-grid {{ display: flex; flex-wrap: wrap; gap: 12px; margin: 20px 0; }}
    .day-card {{ background-color: {'#2d2d2d' if st.session_state.night_mode else '#fff'}; border: 1px solid {'#555' if st.session_state.night_mode else '#ddd'}; border-radius: 16px; padding: 16px 12px; text-align: center; cursor: pointer; transition: 0.2s; min-width: 80px; }}
    .day-card:hover {{ background-color: {'#3a3a3a' if st.session_state.night_mode else '#e3f2fd'}; }}
    .reward-box {{ background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 30px; border-radius: 24px; text-align: center; margin: 20px 0; }}
    .stButton>button {{ width: 100%; height: 3rem; font-size: 1rem; border-radius: 10px; }}
    .error-word {{ color: #d32f2f; font-weight: bold; }}
    .correct-word {{ color: #2e7d32; font-weight: bold; }}
    .score-detail {{ background-color: {'#2a2a2a' if st.session_state.night_mode else '#f5f5f5'}; padding: 15px; border-radius: 12px; margin: 10px 0; }}
</style>
{night_css}
""", unsafe_allow_html=True)

# ---------- 数据文件 ----------
DATA_FILE = "cet4_data.json"
TRANS_BANK_FILE = "trans_bank.json"

DEFAULT_DATA = {
    "words": [],
    "progress": {},
    "user_stats": {"streak": 0, "last_study": None, "total_days": 0},
    "mistake_book": {},
    "user_notes": {},
    "daily_plan": {"target": 20, "completed_today": 0},
    "mastered_records": {},
    "perfect_words": [],
    "learning_start_date": None
}

def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            for key in DEFAULT_DATA:
                if key not in data:
                    data[key] = DEFAULT_DATA[key]
            for w, info in data.get("mistake_book", {}).items():
                if "correct_streak" not in info:
                    info["correct_streak"] = 0
            if data.get("mastered_records"):
                st.session_state.mastered_records = data["mastered_records"]
            if data.get("perfect_words"):
                st.session_state.perfect_words = data["perfect_words"]
            if data.get("learning_start_date"):
                st.session_state.learning_start_date = data["learning_start_date"]
            return data
    except:
        return DEFAULT_DATA.copy()

def save_data(data):
    data["mastered_records"] = st.session_state.mastered_records
    data["perfect_words"] = st.session_state.perfect_words
    data["learning_start_date"] = st.session_state.learning_start_date
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_trans_bank():
    try:
        with open(TRANS_BANK_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_trans_bank(bank):
    with open(TRANS_BANK_FILE, "w", encoding="utf-8") as f:
        json.dump(bank, f, ensure_ascii=False, indent=2)

# ---------- 辅助函数 ----------
def update_streak(data):
    today = datetime.now().date().isoformat()
    last = data["user_stats"].get("last_study")
    if last != today:
        if last and (datetime.fromisoformat(last).date() == datetime.now().date() - timedelta(days=1)):
            data["user_stats"]["streak"] += 1
        else:
            data["user_stats"]["streak"] = 1
        data["user_stats"]["last_study"] = today
        data["user_stats"]["total_days"] = data["user_stats"].get("total_days", 0) + 1
        save_data(data)

def init_progress(word, difficulty):
    return {"ease_factor": 2.5, "interval": 0, "next_review": datetime.now().date().isoformat(), "repetitions": 0, "difficulty": difficulty}

def calculate_next_review(ease_factor, interval, quality, error_count=0):
    penalty = 1.0 / (1 + error_count * 0.35)
    if quality == 0:
        interval = 0
        next_date = datetime.now().date()
    elif quality == 1:
        interval = max(1, int(1 * penalty))
        next_date = datetime.now().date() + timedelta(days=interval)
    else:
        if interval == 0: interval = 1
        elif interval == 1: interval = max(2, int(6 * penalty))
        else: interval = int(interval * ease_factor * penalty)
        next_date = datetime.now().date() + timedelta(days=interval)
    ease_factor = max(1.3, ease_factor + (0.1 - (3 - quality) * (0.08 + (3 - quality) * 0.02)))
    return ease_factor, interval, next_date

def add_to_mistake_book(data, word):
    if "mistake_book" not in data: data["mistake_book"] = {}
    today = datetime.now().date().isoformat()
    if word in data["mistake_book"]:
        data["mistake_book"][word]["error_count"] = data["mistake_book"][word].get("error_count", 0) + 1
        data["mistake_book"][word]["last_error"] = today
        data["mistake_book"][word]["correct_streak"] = 0
    else:
        data["mistake_book"][word] = {"error_count": 1, "correct_streak": 0, "last_error": today, "added": today}

def record_correct_in_mistake(data, word):
    if word in data.get("mistake_book", {}):
        data["mistake_book"][word]["correct_streak"] = data["mistake_book"][word].get("correct_streak", 0) + 1
        if data["mistake_book"][word]["correct_streak"] >= 5:
            del data["mistake_book"][word]
            return True
    return False

def add_to_perfect(word):
    today = datetime.now().date().isoformat()
    if not st.session_state.learning_start_date:
        st.session_state.learning_start_date = today
    if word not in st.session_state.perfect_words:
        st.session_state.perfect_words.append(word)
    if today not in st.session_state.mastered_records:
        st.session_state.mastered_records[today] = []
    if word not in st.session_state.mastered_records[today]:
        st.session_state.mastered_records[today].append(word)
    data = load_data()
    data["perfect_words"] = st.session_state.perfect_words
    data["mastered_records"] = st.session_state.mastered_records
    data["learning_start_date"] = st.session_state.learning_start_date
    save_data(data)

def extract_english_words(text):
    return list(set(re.findall(r'\b[a-zA-Z]{2,}\b', text.lower()))) if text else []

def extract_phrases_from_text(text):
    # 简单短语提取：2-4个单词的组合
    words = text.lower().split()
    phrases = []
    for i in range(len(words)-1):
        for j in range(i+1, min(i+4, len(words)+1)):
            phrase = ' '.join(words[i:j])
            if 2 <= len(phrase.split()) <= 4:
                phrases.append(phrase)
    return list(set(phrases))

def parse_phrases(phrase_str):
    if not phrase_str: return []
    phrases = []
    for part in phrase_str.split(';'):
        part = part.strip()
        if ':' in part:
            en, zh = part.split(':', 1)
            phrases.append({"en": en.strip(), "zh": zh.strip()})
    return phrases

def parse_meanings(meaning_str):
    if not meaning_str: return []
    results = []
    for part in meaning_str.split(';'):
        part = part.strip()
        if not part: continue
        if '.' in part:
            pos, defs = part.split('.', 1)
            def_list = [d.strip() for d in defs.split(';') if d.strip()]
            results.append({"pos": pos.strip() + '.', "defs": def_list})
        else:
            if results:
                results[-1]["defs"].extend([d.strip() for d in part.split(';')])
    return results

def get_word_meanings_list(word_data):
    meanings_str = word_data.get("meaning", "")
    parsed = parse_meanings(meanings_str)
    all_defs = []
    for p in parsed:
        all_defs.extend(p["defs"])
    return all_defs

# ---------- 思维导图组件 ----------
def render_mindmap(word_data):
    word = word_data["word"]
    meaning = word_data.get("meaning", "")
    pos = word_data.get("pos", "")
    phonetic = word_data.get("phonetic", "")
    example = word_data.get("example", "")
    example_zh = word_data.get("example_zh", "")
    memory_tip = word_data.get("memory_tip", "")
    synonyms = word_data.get("synonyms", "").split(",") if word_data.get("synonyms") else []
    antonyms = word_data.get("antonyms", "").split(",") if word_data.get("antonyms") else []
    word_family = word_data.get("word_family", "").split(",") if word_data.get("word_family") else []
    phrases = parse_phrases(word_data.get("phrases", ""))
    important_phrases_str = word_data.get("important_phrases", "")
    important_phrases = [p.strip() for p in important_phrases_str.split(",") if p.strip()] if important_phrases_str else []
    
    st.markdown(f'<div class="big-word">{word}</div>', unsafe_allow_html=True)
    if phonetic:
        st.markdown(f'<div class="phonetic">🔊 /{phonetic}/</div>', unsafe_allow_html=True)
        # 修复发音：用JavaScript并加入错误处理
        st.components.v1.html(f"""
        <script>
        function speak_{word.replace(" ", "_")}() {{
            if (window.speechSynthesis) {{
                window.speechSynthesis.cancel();
                var msg = new SpeechSynthesisUtterance('{word}');
                msg.lang = 'en-US';
                msg.rate = 0.8;
                window.speechSynthesis.speak(msg);
            }}
        }}
        </script>
        <button onclick="speak_{word.replace(' ', '_')}()" style="padding:8px 16px; background:#2c7da0; color:white; border:none; border-radius:20px;">🔊 听发音</button>
        """, height=60)
    if pos:
        st.markdown(f'<span class="pos-tag">{pos}</span>', unsafe_allow_html=True)
    st.markdown(f'<div class="meaning">📖 {meaning}</div>', unsafe_allow_html=True)
    
    with st.container():
        st.markdown('<div class="mindmap-box">', unsafe_allow_html=True)
        
        if word_family:
            st.markdown('<div class="mindmap-title">🌳 词族变形</div>', unsafe_allow_html=True)
            fam_html = ''.join([f'<span class="mindmap-item mindmap-family">{f.strip()}</span>' for f in word_family if f.strip()])
            st.markdown(fam_html, unsafe_allow_html=True)
        
        if phrases:
            st.markdown('<div class="mindmap-title" style="margin-top:15px;">🔗 短语搭配</div>', unsafe_allow_html=True)
            for p in phrases:
                is_imp = p["en"] in important_phrases
                imp_class = "mindmap-phrase" if is_imp else "mindmap-item"
                star = '<span class="phrase-important">必背</span>' if is_imp else ''
                st.markdown(f'<span class="mindmap-item {imp_class}"><b>{p["en"]}</b> {p["zh"]}{star}</span>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if synonyms:
                st.markdown('<div class="mindmap-title">🔄 近义词</div>', unsafe_allow_html=True)
                syn_html = ''.join([f'<span class="mindmap-item">{s.strip()}</span>' for s in synonyms if s.strip()])
                st.markdown(syn_html, unsafe_allow_html=True)
        with col2:
            if antonyms:
                st.markdown('<div class="mindmap-title">⚡ 反义词</div>', unsafe_allow_html=True)
                ant_html = ''.join([f'<span class="mindmap-item">{a.strip()}</span>' for a in antonyms if a.strip()])
                st.markdown(ant_html, unsafe_allow_html=True)
        
        if example:
            st.markdown('<div class="mindmap-title" style="margin-top:15px;">📝 例句</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="mindmap-item mindmap-example"><b>EN:</b> {example}</div>', unsafe_allow_html=True)
            if example_zh:
                st.markdown(f'<div class="mindmap-item mindmap-example"><b>中文:</b> {example_zh}</div>', unsafe_allow_html=True)
        
        if memory_tip:
            st.markdown('<div class="mindmap-title" style="margin-top:15px;">💡 记忆法</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="mindmap-item" style="background:{ "#2a4a2a" if st.session_state.night_mode else "#e8f5e9" };">{memory_tip}</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

# ---------- 数据加载 ----------
data = load_data()
update_streak(data)
words = data["words"]
progress = data["progress"]
mistake_dict = data["mistake_book"]

if not st.session_state.trans_bank:
    st.session_state.trans_bank = load_trans_bank()

today_str = datetime.now().date().isoformat()
due_normal = [w for w in words if progress.get(w["word"], init_progress(w["word"], w.get("difficulty",3)))["next_review"] <= today_str]
due_mistake = [next((w for w in words if w["word"] == m), None) for m in mistake_dict if next((w for w in words if w["word"] == m), None)]

# ---------- 侧边栏 ----------
st.sidebar.markdown("## 🐢 学习数据")
st.sidebar.markdown(f"""
- 📚 词库: {len(words)}
- ⏳ 待复习: {len(due_normal)+len(due_mistake)}
- 📕 错题本: {len(mistake_dict)}
- 🔥 连续: {data['user_stats']['streak']} 天
- 🏆 完美掌握: {len(st.session_state.perfect_words)}
""")
if st.sidebar.button("🌙 夜间模式" if not st.session_state.night_mode else "☀️ 日间模式"):
    st.session_state.night_mode = not st.session_state.night_mode
    st.rerun()

# ---------- 主界面 ----------
st.title("🐢 笨鸟四级 · 思维导图记忆")
tabs = st.tabs(["📚 复习", "✍️ 默写", "📕 错题本", "📋 翻译题库", "🌐 翻译练习", "🏆 完美掌握", "➕ 导入", "📖 词库", "📊 数据"])

# ==================== 标签页0：今日复习 ====================
with tabs[0]:
    st.header("📅 智能复习")
    
    all_due = due_mistake + due_normal
    seen = set()
    all_due = [w for w in all_due if w and w["word"] not in seen and not seen.add(w["word"])]
    
    if st.button("🔄 刷新") or "review_list" not in st.session_state:
        random.seed(st.session_state.review_shuffle_seed)
        random.shuffle(all_due)
        all_due.sort(key=lambda w: mistake_dict.get(w["word"], {}).get("error_count", 0), reverse=True)
        st.session_state.review_list = all_due
        st.session_state.review_idx = 0
        st.session_state.show_answer = False
        st.session_state.meaning_test_active = False
        st.session_state.review_shuffle_seed = random.randint(1, 10000)

    if not all_due:
        st.success("🎉 今日暂无复习任务")
    else:
        idx = st.session_state.review_idx
        if idx < len(st.session_state.review_list):
            cur = st.session_state.review_list[idx]
            word_str = cur["word"]
            
            if not st.session_state.show_answer and not st.session_state.meaning_test_active:
                st.markdown(f'<div class="big-word">{word_str}</div>', unsafe_allow_html=True)
                if cur.get("phonetic"):
                    st.markdown(f'<div class="phonetic">🔊 /{cur["phonetic"]}/</div>', unsafe_allow_html=True)
                    st.components.v1.html(f"""
                    <script>
                    function speak_{word_str.replace(" ", "_")}() {{
                        if (window.speechSynthesis) {{
                            window.speechSynthesis.cancel();
                            var msg = new SpeechSynthesisUtterance('{word_str}');
                            msg.lang = 'en-US';
                            msg.rate = 0.8;
                            window.speechSynthesis.speak(msg);
                        }}
                    }}
                    </script>
                    <button onclick="speak_{word_str.replace(' ', '_')}()" style="padding:8px 16px; background:#2c7da0; color:white; border:none; border-radius:20px;">🔊 听发音</button>
                    """, height=60)
                
                user_meaning = st.text_area("✍️ 输入中文释义 (多个释义用分号分隔)", key=f"meaning_input_{idx}", height=80)
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("提交", key=f"submit_meaning_{idx}"):
                        correct_defs = get_word_meanings_list(cur)
                        user_defs = [d.strip() for d in user_meaning.replace("；", ";").split(";") if d.strip()]
                        matched = sum(1 for u in user_defs if any(u in c or c in u for c in correct_defs))
                        data2 = load_data()
                        if matched >= max(1, len(correct_defs) * 0.6):
                            st.session_state.meaning_test_result = "correct"
                            record_correct_in_mistake(data2, word_str)
                            prog = data2["progress"].get(word_str, init_progress(word_str, cur.get("difficulty",3)))
                            prog["repetitions"] += 1
                            data2["progress"][word_str] = prog
                            if prog["repetitions"] >= 3:
                                if word_str not in st.session_state.perfect_words:
                                    add_to_perfect(word_str)
                            save_data(data2)
                        else:
                            st.session_state.meaning_test_result = "wrong"
                            add_to_mistake_book(data2, word_str)
                            save_data(data2)
                        st.session_state.meaning_test_active = True
                        st.rerun()
                with col2:
                    if st.button("显示答案", key=f"show_ans_{idx}"):
                        st.session_state.show_answer = True
                        st.rerun()
            
            if st.session_state.show_answer or (st.session_state.meaning_test_active and st.session_state.meaning_test_result == "correct"):
                if st.session_state.meaning_test_result == "correct":
                    st.success("✅ 释义正确！")
                render_mindmap(cur)
                
                st.markdown("---")
                st.subheader("🤔 掌握程度")
                q1, q2, q3, q4 = st.columns(4)
                p = progress.get(word_str, init_progress(word_str, cur.get("difficulty",3)))
                
                def make_cb(quality, w, cur_obj):
                    def cb():
                        data2 = load_data()
                        prog = data2["progress"].get(w, init_progress(w, cur_obj.get("difficulty",3)))
                        err_cnt = data2["mistake_book"].get(w, {}).get("error_count",0)
                        ease, interval, next_date = calculate_next_review(prog["ease_factor"], prog["interval"], quality, err_cnt)
                        prog.update({"ease_factor": ease, "interval": interval, "next_review": next_date.isoformat(), "repetitions": prog["repetitions"]+1})
                        data2["progress"][w] = prog
                        if quality == 0:
                            add_to_mistake_book(data2, w)
                        elif quality >= 2:
                            record_correct_in_mistake(data2, w)
                            if prog["repetitions"] >= 3:
                                if w not in st.session_state.perfect_words:
                                    add_to_perfect(w)
                        save_data(data2)
                        st.session_state.show_answer = False
                        st.session_state.meaning_test_active = False
                        st.session_state.meaning_test_result = None
                        st.session_state.review_idx += 1
                    return cb
                
                q1.button("😭 忘记", on_click=make_cb(0, word_str, cur))
                q2.button("😕 困难", on_click=make_cb(1, word_str, cur))
                q3.button("🙂 记得", on_click=make_cb(2, word_str, cur))
                q4.button("😎 简单", on_click=make_cb(3, word_str, cur))
            
            elif st.session_state.meaning_test_active and st.session_state.meaning_test_result == "wrong":
                st.error("❌ 释义不完整或有误")
                correct_defs = get_word_meanings_list(cur)
                st.markdown(f"**正确释义**：{'; '.join(correct_defs)}")
                render_mindmap(cur)
                if st.button("加入错题本并继续", key=f"cont_{idx}"):
                    st.session_state.show_answer = False
                    st.session_state.meaning_test_active = False
                    st.session_state.meaning_test_result = None
                    st.session_state.review_idx += 1
                    st.rerun()
        else:
            st.success("✅ 今日复习完成")
            if st.button("重新开始"):
                st.session_state.review_list = []
                st.rerun()

# ==================== 标签页1：综合默写 ====================
with tabs[1]:
    st.header("✍️ 综合默写")
    
    if not words:
        st.warning("请先导入单词")
    else:
        if st.button("🔄 换一组") or "dict_items" not in st.session_state:
            items = []
            sample_words = random.sample(words, min(10, len(words)))
            for w in sample_words:
                items.append({"type": "word_spell", "word": w["word"], "meaning": w["meaning"], "data": w})
                items.append({"type": "word_meaning", "word": w["word"], "meaning": w["meaning"], "data": w})
                phrases = parse_phrases(w.get("phrases", ""))
                for p in phrases[:2]:
                    items.append({"type": "phrase_en", "phrase_en": p["en"], "phrase_zh": p["zh"], "data": w})
                    items.append({"type": "phrase_zh", "phrase_en": p["en"], "phrase_zh": p["zh"], "data": w})
            random.shuffle(items)
            st.session_state.dict_items = items
            st.session_state.dict_idx = 0
            st.session_state.dict_correct = 0
            st.session_state.dict_done = False
            st.session_state.dict_show_res = False

        if not st.session_state.dict_done:
            idx = st.session_state.dict_idx
            items = st.session_state.dict_items
            if idx < len(items):
                item = items[idx]
                st.markdown(f"### 📌 {idx+1}/{len(items)}")
                
                if item["type"] == "word_spell":
                    st.markdown(f"**释义**: {item['meaning']}")
                    user_in = st.text_input("输入英文单词", key=f"ws_{idx}")
                    answer = item["word"]
                elif item["type"] == "word_meaning":
                    st.markdown(f"**单词**: {item['word']}")
                    user_in = st.text_area("输入中文释义", key=f"wm_{idx}")
                    answer = item["meaning"]
                elif item["type"] == "phrase_en":
                    st.markdown(f"**短语中文**: {item['phrase_zh']}")
                    user_in = st.text_input("输入英文短语", key=f"pe_{idx}")
                    answer = item["phrase_en"]
                else:
                    st.markdown(f"**英文短语**: {item['phrase_en']}")
                    user_in = st.text_input("输入中文释义", key=f"pz_{idx}")
                    answer = item["phrase_zh"]
                
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("提交", key=f"sub_{idx}"):
                        correct = False
                        if item["type"] in ["word_spell", "phrase_en"]:
                            correct = user_in.strip().lower() == answer.lower()
                        else:
                            correct = any(u in answer or answer in u for u in user_in.split(';'))
                        
                        data2 = load_data()
                        if correct:
                            st.session_state.dict_correct += 1
                            st.session_state.dict_show_res = True
                            st.session_state.dict_res_correct = True
                            record_correct_in_mistake(data2, item["data"]["word"])
                            prog = data2["progress"].get(item["data"]["word"], init_progress(item["data"]["word"], item["data"].get("difficulty",3)))
                            prog["repetitions"] += 1
                            data2["progress"][item["data"]["word"]] = prog
                            if prog["repetitions"] >= 3:
                                if item["data"]["word"] not in st.session_state.perfect_words:
                                    add_to_perfect(item["data"]["word"])
                        else:
                            st.session_state.dict_show_res = True
                            st.session_state.dict_res_correct = False
                            add_to_mistake_book(data2, item["data"]["word"])
                        save_data(data2)
                        st.session_state.user_ans = user_in
                        st.rerun()
                with c2:
                    if st.button("跳过", key=f"skip_{idx}"):
                        st.session_state.dict_show_res = True
                        st.session_state.dict_res_correct = False
                        st.rerun()
                
                if st.session_state.dict_show_res:
                    if st.session_state.dict_res_correct:
                        st.success("✅ 正确")
                    else:
                        st.error(f"❌ 错误，正确答案: {answer}")
                    if st.button("➡️ 下一题", key=f"next_{idx}"):
                        st.session_state.dict_idx += 1
                        st.session_state.dict_show_res = False
                        if st.session_state.dict_idx >= len(items):
                            st.session_state.dict_done = True
                        st.rerun()
            else:
                st.session_state.dict_done = True
                st.rerun()
        else:
            total = len(st.session_state.dict_items)
            correct = st.session_state.dict_correct
            st.markdown(f"## 🏆 完成！正确 {correct}/{total}")
            if st.button("再来一组"):
                for k in ["dict_items","dict_idx","dict_correct","dict_done","dict_show_res"]:
                    if k in st.session_state: del st.session_state[k]
                st.rerun()

# ==================== 标签页2：错题本 ====================
with tabs[2]:
    st.header("📕 错题本")
    mb = data.get("mistake_book", {})
    if not mb:
        st.info("暂无错题")
    else:
        sorted_mb = sorted(mb.items(), key=lambda x: x[1].get("error_count", 0), reverse=True)
        for w, info in sorted_mb:
            w_obj = next((x for x in words if x["word"] == w), None)
            if w_obj:
                with st.container():
                    st.markdown(f"### {w}  ❌ {info.get('error_count',0)}次")
                    st.markdown(f"释义: {w_obj['meaning']}")
                    if w_obj.get('memory_tip'):
                        st.markdown(f"💡 {w_obj['memory_tip']}")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(f"复习", key=f"mb_rev_{w}"):
                            st.session_state.review_list = [w_obj]
                            st.session_state.review_idx = 0
                            st.session_state.show_answer = False
                            st.rerun()
                    with col2:
                        if st.button(f"移出", key=f"mb_rm_{w}"):
                            del data["mistake_book"][w]
                            save_data(data)
                            st.rerun()
                    st.progress(info.get('correct_streak',0)/5, text=f"连续正确 {info.get('correct_streak',0)}/5")
                    st.markdown("---")

# ==================== 标签页3：翻译题库 ====================
with tabs[3]:
    st.header("📋 翻译题库")
    st.markdown("Excel格式：`中文原文`, `参考译文`")
    up = st.file_uploader("上传Excel", type=["xlsx"])
    if up:
        try:
            df = pd.read_excel(up)
            if "中文原文" in df.columns and "参考译文" in df.columns:
                df = df.fillna("")
                if st.button("导入"):
                    new_items = []
                    for _, row in df.iterrows():
                        new_items.append({
                            "id": datetime.now().timestamp() + len(new_items),
                            "chinese": str(row["中文原文"]),
                            "reference": str(row["参考译文"])
                        })
                    st.session_state.trans_bank.extend(new_items)
                    save_trans_bank(st.session_state.trans_bank)
                    st.success(f"导入 {len(new_items)} 题")
                    st.rerun()
        except Exception as e:
            st.error(str(e))
    
    if st.session_state.trans_bank:
        for i, q in enumerate(st.session_state.trans_bank[:10]):
            if st.button(f"{i+1}. {q['chinese'][:30]}...", key=f"sel_{i}"):
                st.session_state.current_trans_q = q
                st.session_state.trans_submitted = False
                st.session_state.trans_score_detail = None
                st.rerun()

# ==================== 标签页4：翻译练习（第一部分：题目展示和输入） ====================
with tabs[4]:
    st.header("🌐 翻译练习")
    if not st.session_state.current_trans_q:
        st.info("请先在「翻译题库」选题")
    else:
        q = st.session_state.current_trans_q
        st.markdown(f"**中文原文**: {q['chinese']}")
        
        # 参考译文折叠
        with st.expander("🔍 参考译文 (建议先自行翻译后再查看哦)"):
            st.markdown(q['reference'])
        
        user_trans = st.text_area("✍️ 你的翻译", height=150, key="trans_input", value=st.session_state.get('trans_user_input', ''))
        st.session_state.trans_user_input = user_trans
        
        if st.button("📊 提交评分"):
            if not user_trans.strip():
                st.warning("请输入翻译内容")
            else:
                # 评分逻辑放在第二部分，此处先存储
                st.session_state.trans_submitted = True
                st.session_state.trans_user_input = user_trans
                st.rerun()
        
        # 评分结果显示（第二部分继续）
        if st.session_state.trans_submitted and st.session_state.trans_score_detail:
            detail = st.session_state.trans_score_detail
            st.markdown("---")
            st.markdown("### 📊 评分结果")
            st.markdown(f"**总分**: {detail['total']}/15  ({detail['grade']})")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("内容覆盖", f"{detail['coverage']}/7")
                st.caption(f"命中关键词: {detail['hit_keywords']}/{detail['total_keywords']}")
            with col2:
                st.metric("语言质量", f"{detail['language']}/8")
                st.caption(f"拼写正确词数: {detail['correct_spell']}/{detail['total_user_words']}")
            
            # 错误词汇
            if detail.get('wrong_words'):
                st.markdown("#### ❌ 拼写/用词错误 (已加入错题本)")
                for w in detail['wrong_words']:
                    st.markdown(f"- `{w}`")
            
            # 错误短语
            if detail.get('wrong_phrases'):
                st.markdown("#### ❌ 短语错误")
                for p in detail['wrong_phrases']:
                    st.markdown(f"- `{p['user']}` → `{p['correct']}`")
            
            # 遗漏关键词
            if detail.get('missing_keywords'):
                st.markdown("#### ⚠️ 可能遗漏的关键信息")
                st.markdown(f"{', '.join(detail['missing_keywords'])}")
            
            # 重新翻译按钮
            if st.button("🔄 重新翻译"):
                st.session_state.trans_submitted = False
                st.session_state.trans_score_detail = None
                st.session_state.trans_user_input = ''
                st.rerun()


        # 评分逻辑（当提交后且没有评分详情时执行）
        if st.session_state.trans_submitted and not st.session_state.trans_score_detail:
            user_trans = st.session_state.trans_user_input
            q = st.session_state.current_trans_q
            ref_text = q['reference']
            chinese_text = q['chinese']

            # 提取参考译文的关键信息
            ref_words = set(extract_english_words(ref_text))
            user_words = set(extract_english_words(user_trans))
            
            # 提取短语（简化版）
            ref_phrases = extract_phrases_from_text(ref_text)
            user_phrases = extract_phrases_from_text(user_trans)
            
            # 提取中文关键词（简单规则）
            key_terms = re.findall(r'[\u4e00-\u9fff]{2,4}', chinese_text)
            key_terms = [t for t in key_terms if t not in ['这是','那是','这个','那个','一个','一种','一些','很多']][:5]
            
            # 计算内容覆盖（基于关键词命中，简化为检查用户译文中是否包含常见对应词）
            # 这里用一个简单映射表
            term_map = {
                "火锅": ["hot pot", "hotpot"],
                "春节": ["spring festival", "chinese new year"],
                "饺子": ["dumpling", "jiaozi"],
                "剪纸": ["paper cut", "paper cutting"],
                "茶": ["tea"],
                "文化": ["culture"],
                "传统": ["traditional", "tradition"],
                "重要": ["important", "significant"],
                "流行": ["popular"],
                "喜欢": ["like", "enjoy", "love"],
                "吃": ["eat", "have"],
                "喝": ["drink"],
                "庆祝": ["celebrate"],
                "历史": ["history"],
                "家庭": ["family"],
                "朋友": ["friend"],
                "人们": ["people"],
                "中国": ["china", "chinese"],
                "发展": ["develop", "development"],
                "经济": ["economy", "economic"],
                "社会": ["society", "social"],
            }
            
            hit_keywords = 0
            total_keywords = len(key_terms)
            for term in key_terms:
                possible = term_map.get(term, [term.lower()])
                if any(p in user_trans.lower() for p in possible):
                    hit_keywords += 1
            coverage_score = int((hit_keywords / max(1, total_keywords)) * 7)
            
            # 语言质量：检查拼写错误
            known_words = {w["word"].lower() for w in words}
            common_words = {'the','a','an','is','are','was','were','be','been','have','has','had',
                           'do','does','did','and','but','or','of','in','on','at','to','for','with',
                           'by','from','as','it','this','that','these','those','i','you','he','she',
                           'we','they','my','your','his','her','our','their','me','him','us','them',
                           'very','so','too','also','not','no','yes','can','will','would','could','should'}
            
            correct_spell = 0
            wrong_words = []
            for w in user_words:
                if w in common_words or w in known_words:
                    correct_spell += 1
                else:
                    # 检查是否接近某已知词（拼写错误）
                    close_match = None
                    for kw in known_words:
                        if abs(len(w)-len(kw)) <= 2:
                            # 简单编辑距离
                            if sum(1 for a,b in zip(w,kw) if a!=b) <= 2:
                                close_match = kw
                                break
                    if close_match:
                        wrong_words.append(f"{w} → {close_match}")
                        # 将正确形式加入错题本
                        data2 = load_data()
                        add_to_mistake_book(data2, close_match)
                        save_data(data2)
                    else:
                        wrong_words.append(w)
                        # 如果词库中没有，但可能是正确拼写，不扣分太多
            language_score = max(0, 8 - len(wrong_words) * 0.5)
            language_score = min(8, int(language_score))
            
            # 短语检查
            wrong_phrases = []
            for up in user_phrases:
                if up not in ref_phrases:
                    # 检查是否部分匹配
                    matched = False
                    for rp in ref_phrases:
                        if up in rp or rp in up:
                            matched = True
                            break
                    if not matched:
                        wrong_phrases.append({"user": up, "correct": "参考译文中未找到对应短语"})
            
            # 将用户译文中不在词库的生词加入错题本（可选）
            data2 = load_data()
            for w in user_words:
                if w not in common_words and w not in known_words and len(w) > 2:
                    add_to_mistake_book(data2, w)
            save_data(data2)
            
            total_score = coverage_score + language_score
            if total_score >= 13:
                grade = "优秀 (13-15分)"
            elif total_score >= 10:
                grade = "良好 (10-12分)"
            elif total_score >= 7:
                grade = "中等 (7-9分)"
            elif total_score >= 4:
                grade = "及格 (4-6分)"
            else:
                grade = "不及格 (1-3分)"
            
            missing_keywords = [term for term in key_terms if not any(p in user_trans.lower() for p in term_map.get(term, [term.lower()]))]
            
            detail = {
                "total": total_score,
                "grade": grade,
                "coverage": coverage_score,
                "language": language_score,
                "hit_keywords": hit_keywords,
                "total_keywords": total_keywords,
                "correct_spell": correct_spell,
                "total_user_words": len(user_words),
                "wrong_words": wrong_words,
                "wrong_phrases": wrong_phrases,
                "missing_keywords": missing_keywords,
                "ref_words": list(ref_words),
                "user_words": list(user_words)
            }
            st.session_state.trans_score_detail = detail
            st.rerun()

# ==================== 标签页5：完美掌握 ====================
with tabs[5]:
    st.header("🏆 完美掌握 · 每日巩固")
    
    if not st.session_state.learning_start_date:
        st.info("还没有完美掌握的单词，继续学习吧！")
    else:
        dates = sorted(st.session_state.mastered_records.keys())
        if not dates:
            st.info("暂无完美掌握记录")
        else:
            st.markdown("### 📅 选择复习日期")
            start_date = datetime.fromisoformat(st.session_state.learning_start_date).date()
            
            cols = st.columns(min(len(dates), 5))
            for i, date_str in enumerate(dates):
                date_obj = datetime.fromisoformat(date_str).date()
                day_num = (date_obj - start_date).days + 1
                with cols[i % 5]:
                    if st.button(f"DAY {day_num}", key=f"day_{date_str}"):
                        st.session_state.current_day_review = date_str
                        st.session_state.day_review_idx = 0
                        st.session_state.day_review_correct = 0
                        words_today = st.session_state.mastered_records.get(date_str, [])
                        items = []
                        for w_str in words_today:
                            w_obj = next((x for x in words if x["word"] == w_str), None)
                            if w_obj:
                                items.append({"type": "word_spell", "word": w_str, "data": w_obj})
                                items.append({"type": "word_meaning", "word": w_str, "data": w_obj})
                                phrases = parse_phrases(w_obj.get("phrases", ""))
                                for p in phrases[:1]:
                                    items.append({"type": "phrase_en", "phrase": p, "data": w_obj})
                                    items.append({"type": "phrase_zh", "phrase": p, "data": w_obj})
                        random.shuffle(items)
                        st.session_state.day_review_items = items
                        st.rerun()
    
    if st.session_state.current_day_review:
        st.markdown("---")
        date_obj = datetime.fromisoformat(st.session_state.current_day_review).date()
        start_date = datetime.fromisoformat(st.session_state.learning_start_date).date()
        day_num = (date_obj - start_date).days + 1
        st.subheader(f"📖 DAY {day_num} 复习")
        items = st.session_state.day_review_items
        idx = st.session_state.day_review_idx
        
        if idx < len(items):
            item = items[idx]
            st.markdown(f"**{idx+1}/{len(items)}**")
            if item["type"] == "word_spell":
                st.markdown(f"释义: {item['data']['meaning']}")
                user_in = st.text_input("单词", key=f"dr_ws_{idx}")
                answer = item["word"]
            elif item["type"] == "word_meaning":
                st.markdown(f"单词: {item['word']}")
                user_in = st.text_area("中文", key=f"dr_wm_{idx}")
                answer = item["data"]["meaning"]
            elif item["type"] == "phrase_en":
                st.markdown(f"短语中文: {item['phrase']['zh']}")
                user_in = st.text_input("英文", key=f"dr_pe_{idx}")
                answer = item["phrase"]["en"]
            else:
                st.markdown(f"短语英文: {item['phrase']['en']}")
                user_in = st.text_input("中文", key=f"dr_pz_{idx}")
                answer = item["phrase"]["zh"]
            
            if st.button("提交", key=f"dr_sub_{idx}"):
                correct = False
                if item["type"] in ["word_spell", "phrase_en"]:
                    correct = user_in.strip().lower() == answer.lower()
                else:
                    correct = any(u in answer for u in user_in.split(';'))
                if correct:
                    st.session_state.day_review_correct += 1
                    st.success("正确")
                else:
                    st.error(f"错误，答案: {answer}")
                st.session_state.day_review_idx += 1
                if st.session_state.day_review_idx >= len(items):
                    st.balloons()
                    st.markdown('<div class="reward-box"><h2>🎉 恭喜！</h2><p>你已完成今日完美单词复习！</p></div>', unsafe_allow_html=True)
                st.rerun()
        else:
            st.success("复习完成")
            if st.button("返回"):
                st.session_state.current_day_review = None
                st.rerun()

# ==================== 标签页6：导入单词 ====================
with tabs[6]:
    st.header("📥 导入单词")
    st.markdown("""
    Excel列名：`word`, `meaning`, `pos`, `phonetic`, `memory_tip`, `example`, `example_zh`, 
    `synonyms`, `antonyms`, `word_family`, `phrases`, `important_phrases`, `difficulty`
    """)
    up = st.file_uploader("选择Excel", type=["xlsx"], key="word_upload")
    if up:
        try:
            df = pd.read_excel(up)
            required = ["word", "meaning"]
            if not all(c in df.columns for c in required):
                st.error("缺少word/meaning列")
            else:
                df = df.fillna("")
                if st.button("确认导入"):
                    data2 = load_data()
                    exist = {w["word"] for w in data2["words"]}
                    new = 0
                    for _, row in df.iterrows():
                        w = str(row["word"]).strip()
                        if not w or w in exist: continue
                        entry = {
                            "word": w,
                            "meaning": str(row["meaning"]),
                            "pos": str(row.get("pos", "")),
                            "phonetic": str(row.get("phonetic", "")),
                            "memory_tip": str(row.get("memory_tip", "")),
                            "example": str(row.get("example", "")),
                            "example_zh": str(row.get("example_zh", "")),
                            "synonyms": str(row.get("synonyms", "")),
                            "antonyms": str(row.get("antonyms", "")),
                            "word_family": str(row.get("word_family", "")),
                            "phrases": str(row.get("phrases", "")),
                            "important_phrases": str(row.get("important_phrases", "")),
                            "difficulty": int(row.get("difficulty", 3))
                        }
                        data2["words"].append(entry)
                        data2["progress"][w] = init_progress(w, entry["difficulty"])
                        new += 1
                    save_data(data2)
                    st.success(f"导入 {new} 词")
                    st.rerun()
        except Exception as e:
            st.error(str(e))

# ==================== 标签页7：词库 ====================
with tabs[7]:
    st.header("📖 单词库")
    if words:
        df = pd.DataFrame(words)
        st.dataframe(df[["word","meaning","pos"]])
        to_del = st.multiselect("删除单词", df["word"].tolist())
        if st.button("删除选中"):
            data2 = load_data()
            data2["words"] = [w for w in data2["words"] if w["word"] not in to_del]
            for w in to_del:
                if w in data2["progress"]: del data2["progress"][w]
                if w in data2["mistake_book"]: del data2["mistake_book"][w]
            save_data(data2)
            st.success("删除成功")
            st.rerun()
    else:
        st.info("暂无单词")

# ==================== 标签页8：学习数据 ====================
with tabs[8]:
    st.header("📊 详细学习数据")
    data2 = load_data()
    st.markdown(f"- 总单词量：{len(words)}")
    st.markdown(f"- 错题本单词数：{len(data2.get('mistake_book', {}))}")
    st.markdown(f"- 连续打卡：{data2['user_stats']['streak']} 天")
    st.markdown(f"- 总学习天数：{data2['user_stats']['total_days']} 天")
    st.markdown(f"- 翻译题库：{len(st.session_state.trans_bank)} 题")
    st.markdown(f"- 完美掌握单词：{len(st.session_state.perfect_words)}")
    if words:
        total_reviews = sum(p.get("repetitions", 0) for p in data2["progress"].values())
        st.markdown(f"- 累计复习次数：{total_reviews}")
    if st.session_state.learning_start_date:
        st.markdown(f"- 开始学习日期：{st.session_state.learning_start_date}")

# ---------- 运行入口 ----------
if __name__ == "__main__":
    # 所有页面已在上面定义，streamlit自动运行
    pass
