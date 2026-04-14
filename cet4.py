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
        'review_shuffle_seed': random.randint(1, 10000),
        'meaning_test_active': False, 'meaning_test_word': None,
        'meaning_user_input': '', 'meaning_test_result': None,
        'mastered_words': {},  # {date: [word_list]}
        'current_day_review': None,
        'day_review_mode': 'mixed',  # mixed/meaning/spell/phrase_cn/phrase_en
        'day_review_idx': 0,
        'day_review_items': [],
        'day_review_correct': 0,
        'day_review_show_res': False,
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
    .mindmap-key {{ background-color: #2c7da0; color: white; }}
    .mindmap-phrase {{ background: linear-gradient(135deg, {'#3a2a1a' if st.session_state.night_mode else '#fff3e0'}, {'#4a3a2a' if st.session_state.night_mode else '#ffe0b2'}); border-left: 4px solid #ff9800; }}
    .mindmap-family {{ background: linear-gradient(135deg, {'#1e3a1e' if st.session_state.night_mode else '#e8f5e9'}, {'#2e4a2e' if st.session_state.night_mode else '#c8e6c9'}); border-left: 4px solid #4caf50; }}
    .mindmap-example {{ background: linear-gradient(135deg, {'#3a1a2a' if st.session_state.night_mode else '#fce4ec'}, {'#4a2a3a' if st.session_state.night_mode else '#f8bbd0'}); border-left: 4px solid #e91e63; }}
    .phrase-important {{ background-color: #d32f2f; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.7rem; margin-left: 6px; }}
    .example-box {{ background-color: {'#2a2a2a' if st.session_state.night_mode else '#f0f4f8'}; padding: 16px; border-radius: 12px; border-left: 5px solid #2c7da0; }}
    .calendar-grid {{ display: grid; grid-template-columns: repeat(7, 1fr); gap: 10px; margin: 20px 0; }}
    .calendar-day {{ background-color: {'#2d2d2d' if st.session_state.night_mode else '#fff'}; border: 1px solid {'#555' if st.session_state.night_mode else '#ddd'}; border-radius: 12px; padding: 12px 8px; text-align: center; cursor: pointer; transition: 0.2s; }}
    .calendar-day:hover {{ background-color: {'#3a3a3a' if st.session_state.night_mode else '#e3f2fd'}; }}
    .calendar-day.completed {{ background-color: #4caf50; color: white; }}
    .reward-box {{ background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 30px; border-radius: 24px; text-align: center; margin: 20px 0; }}
    .stButton>button {{ width: 100%; height: 3rem; font-size: 1rem; border-radius: 10px; }}
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
    "mastered_records": {},  # {date: [word_list]}
    "perfect_words": []      # 正确3次以上的单词
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
            return data
    except:
        return DEFAULT_DATA.copy()

def save_data(data):
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

def extract_english_words(text):
    return list(set(re.findall(r'\b[a-zA-Z]{2,}\b', text.lower()))) if text else []

def parse_phrases(phrase_str):
    """解析短语字符串：格式 'oppose sth:反对某事; be opposed to:不赞成' """
    if not phrase_str: return []
    phrases = []
    for part in phrase_str.split(';'):
        part = part.strip()
        if ':' in part:
            en, zh = part.split(':', 1)
            phrases.append({"en": en.strip(), "zh": zh.strip()})
    return phrases

def parse_meanings(meaning_str):
    """解析多个释义：'v.反抗;反对 n.反对派' -> [{'pos':'v.', 'defs':['反抗','反对']}, ...]"""
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
    """返回所有释义的扁平列表（用于默写比对）"""
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
    important_phrases = [p for p in phrases if word_data.get("important_phrases", "") and p["en"] in word_data["important_phrases"]]
    
    st.markdown(f'<div class="big-word">{word}</div>', unsafe_allow_html=True)
    if phonetic:
        st.markdown(f'<div class="phonetic">🔊 /{phonetic}/</div>', unsafe_allow_html=True)
    if pos:
        st.markdown(f'<span class="pos-tag">{pos}</span>', unsafe_allow_html=True)
    st.markdown(f'<div class="meaning">📖 {meaning}</div>', unsafe_allow_html=True)
    
    with st.container():
        st.markdown('<div class="mindmap-box">', unsafe_allow_html=True)
        
        # 词族
        if word_family:
            st.markdown('<div class="mindmap-title">🌳 词族变形</div>', unsafe_allow_html=True)
            fam_html = ''.join([f'<span class="mindmap-item mindmap-family">{f.strip()}</span>' for f in word_family if f.strip()])
            st.markdown(fam_html, unsafe_allow_html=True)
        
        # 短语
        if phrases:
            st.markdown('<div class="mindmap-title" style="margin-top:15px;">🔗 短语搭配</div>', unsafe_allow_html=True)
            for p in phrases:
                imp_class = "mindmap-phrase" if any(ip["en"]==p["en"] for ip in important_phrases) else "mindmap-item"
                star = '<span class="phrase-important">必背</span>' if any(ip["en"]==p["en"] for ip in important_phrases) else ''
                st.markdown(f'<span class="mindmap-item {imp_class}"><b>{p["en"]}</b> {p["zh"]}{star}</span>', unsafe_allow_html=True)
        
        # 近义词/反义词
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
        
        # 例句
        if example:
            st.markdown('<div class="mindmap-title" style="margin-top:15px;">📝 例句</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="mindmap-item mindmap-example"><b>EN:</b> {example}</div>', unsafe_allow_html=True)
            if example_zh:
                st.markdown(f'<div class="mindmap-item mindmap-example"><b>中文:</b> {example_zh}</div>', unsafe_allow_html=True)
        
        # 记忆技巧
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
mastered_records = data.get("mastered_records", {})
perfect_words = set(data.get("perfect_words", []))

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
- 🏆 完美掌握: {len(perfect_words)}
""")
if st.sidebar.button("🌙 夜间模式" if not st.session_state.night_mode else "☀️ 日间模式"):
    st.session_state.night_mode = not st.session_state.night_mode
    st.rerun()

# ---------- 主界面 ----------
st.title("🐢 笨鸟四级 · 思维导图记忆")
tabs = st.tabs(["📚 今日复习", "✍️ 综合默写", "📕 错题本", "📋 翻译题库", "🌐 翻译练习", "📅 完美掌握日历", "➕ 导入", "📖 词库"])

# ==================== 标签页0：今日复习（含中文默写） ====================
with tabs[0]:
    st.header("📅 智能复习")
    
    all_due = due_mistake + due_normal
    # 去重
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
            
            # 中文默写模式
            if not st.session_state.show_answer and not st.session_state.meaning_test_active:
                st.markdown(f'<div class="big-word">{word_str}</div>', unsafe_allow_html=True)
                if cur.get("phonetic"):
                    st.markdown(f'<div class="phonetic">🔊 /{cur["phonetic"]}/</div>', unsafe_allow_html=True)
                    st.components.v1.html(f"""<script>function speak(){{var msg=new SpeechSynthesisUtterance('{word_str}');msg.lang='en-US';window.speechSynthesis.speak(msg);}}</script><button onclick="speak()">🔊 听发音</button>""", height=50)
                
                user_meaning = st.text_area("✍️ 输入中文释义 (多个释义用分号分隔)", key=f"meaning_input_{idx}", height=80)
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("提交", key=f"submit_meaning_{idx}"):
                        correct_defs = get_word_meanings_list(cur)
                        user_defs = [d.strip() for d in user_meaning.replace("；", ";").split(";") if d.strip()]
                        # 简单比对：只要有交集就算部分正确，但要求覆盖大部分
                        matched = sum(1 for u in user_defs if any(u in c or c in u for c in correct_defs))
                        if matched >= max(1, len(correct_defs) * 0.6):
                            st.session_state.meaning_test_result = "correct"
                            # 正确：记录连续正确，可能移出错题本，加入完美掌握
                            data2 = load_data()
                            record_correct_in_mistake(data2, word_str)
                            # 增加 repetition 计数
                            prog = data2["progress"].get(word_str, init_progress(word_str, cur.get("difficulty",3)))
                            prog["repetitions"] += 1
                            data2["progress"][word_str] = prog
                            # 完美单词判断：正确3次以上
                            if prog["repetitions"] >= 3:
                                if word_str not in data2.get("perfect_words", []):
                                    data2["perfect_words"] = data2.get("perfect_words", []) + [word_str]
                            save_data(data2)
                        else:
                            st.session_state.meaning_test_result = "wrong"
                            data2 = load_data()
                            add_to_mistake_book(data2, word_str)
                            save_data(data2)
                        st.session_state.meaning_test_active = True
                        st.rerun()
                with col2:
                    if st.button("显示答案", key=f"show_ans_{idx}"):
                        st.session_state.show_answer = True
                        st.rerun()
            
            # 显示思维导图（答对或点击显示答案后）
            if st.session_state.show_answer or (st.session_state.meaning_test_active and st.session_state.meaning_test_result == "correct"):
                if st.session_state.meaning_test_result == "correct":
                    st.success("✅ 释义正确！")
                render_mindmap(cur)
                
                # 记忆反馈
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

# ==================== 标签页1：综合默写（单词+短语混合） ====================
with tabs[1]:
    st.header("✍️ 综合默写 (单词/短语混合)")
    
    if not words:
        st.warning("请先导入单词")
    else:
        if st.button("🔄 换一组") or "dict_items" not in st.session_state:
            # 构建默写项：单词英文、单词中文、短语英文、短语中文
            items = []
            for w in random.sample(words, min(10, len(words))):
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
                else:  # phrase_zh
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
                            # 中文比对宽松
                            correct = any(u in answer or answer in u for u in user_in.split(';'))
                        
                        if correct:
                            st.session_state.dict_correct += 1
                            st.session_state.dict_show_res = True
                            st.session_state.dict_res_correct = True
                            # 记录正确
                            data2 = load_data()
                            record_correct_in_mistake(data2, item["data"]["word"])
                            save_data(data2)
                        else:
                            st.session_state.dict_show_res = True
                            st.session_state.dict_res_correct = False
                            data2 = load_data()
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
    # 导入逻辑略（同前）
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
                            "chinese": row["中文原文"],
                            "reference": row["参考译文"]
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
                st.rerun()

# ==================== 标签页4：翻译练习 ====================
with tabs[4]:
    st.header("🌐 翻译练习")
    if not st.session_state.current_trans_q:
        st.info("请先在题库选题")
    else:
        q = st.session_state.current_trans_q
        st.markdown(f"**中文**: {q['chinese']}")
        user_trans = st.text_area("你的翻译", height=150)
        if st.button("提交评分"):
            # 简化评分，主要看单词覆盖
            ref_words = set(extract_english_words(q['reference']))
            user_words = set(extract_english_words(user_trans))
            score = len(ref_words & user_words) / max(1, len(ref_words)) * 15
            st.session_state.trans_score_detail = {"total": int(score), "matched": ref_words & user_words}
            st.session_state.trans_submitted = True
            # 错词加入错题本
            data2 = load_data()
            for w in user_words:
                if w not in ref_words:
                    add_to_mistake_book(data2, w)
            save_data(data2)
            st.rerun()
        
        if st.session_state.trans_submitted:
            d = st.session_state.trans_score_detail
            st.markdown(f"### 得分: {d['total']}/15")
            st.markdown(f"正确词汇: {', '.join(d['matched'])}")

# ==================== 标签页5：完美掌握日历 ====================
with tabs[5]:
    st.header("📅 完美掌握·每日复习")
    
    # 将完美单词按日期分组 (简单模拟：假设每次正确加入当天)
    # 实际需记录日期，这里用mastered_records字段：{date: [words]}
    today = datetime.now().date()
    
    # 显示日历
    st.subheader("学习日历")
    # 生成最近30天
    days = []
    for i in range(30):
        d = today - timedelta(days=i)
        days.append(d)
    days.reverse()
    
    cols = st.columns(7)
    for i, d in enumerate(days):
        day_str = d.isoformat()
        words_today = mastered_records.get(day_str, [])
        completed = len(words_today) > 0
        with cols[i % 7]:
            btn_label = f"{d.month}/{d.day}"
            if completed:
                btn_label += " ✅"
            if st.button(btn_label, key=f"cal_{day_str}"):
                st.session_state.current_day_review = day_str
                st.session_state.day_review_mode = "mixed"
                st.session_state.day_review_idx = 0
                st.session_state.day_review_correct = 0
                # 生成该天所有单词的四种默写
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
    
    # 当日复习界面
    if st.session_state.current_day_review:
        st.markdown("---")
        st.subheader(f"📖 {st.session_state.current_day_review} 复习")
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
                    # 完成
                    st.balloons()
                    st.markdown('<div class="reward-box"><h2>🎉 恭喜！</h2><p>你已完成今日完美单词复习！</p></div>', unsafe_allow_html=True)
                    # 记录完成
                    data2 = load_data()
                    if "mastered_records" not in data2: data2["mastered_records"] = {}
                    if st.session_state.current_day_review not in data2["mastered_records"]:
                        data2["mastered_records"][st.session_state.current_day_review] = []
                    save_data(data2)
                st.rerun()
        else:
            st.success("复习完成")
            if st.button("返回日历"):
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
    else:
        st.info("暂无单词")
