import streamlit as st
import pandas as pd
import random
import json
import os
import re
from datetime import datetime, timedelta

# ---------- 页面配置 ----------
st.set_page_config(page_title="🐢 笨鸟四级·全能进阶", layout="wide")
st.markdown("""
<style>
    body { background-color: white; }
    .main { color: black; }
    .red { color: #d32f2f; font-weight: bold; }
    .blue { color: #1976d2; }
    .green-bg { background-color: #e8f5e9; padding: 10px; border-radius: 8px; border-left: 5px solid #4caf50; }
    .red-bg { background-color: #ffebee; padding: 10px; border-radius: 8px; border-left: 5px solid #d32f2f; }
    .big-word { font-size: 64px; font-weight: bold; text-align: center; margin: 20px 0; }
    .phonetic { font-size: 24px; color: #1976d2; text-align: center; margin-bottom: 10px; }
    .pos-tag { background-color: #d32f2f; color: white; padding: 4px 12px; border-radius: 20px; font-size: 18px; display: inline-block; margin-right: 10px; }
    .meaning { font-size: 32px; color: black; margin: 15px 0; }
    .example { color: #333; margin-top: 10px; padding: 10px; background-color: #f5f5f5; border-radius: 8px; }
    .memory-tip { color: #1b5e20; margin-top: 10px; padding: 12px; background-color: #f1f8e9; border-left: 5px solid #4caf50; border-radius: 8px; }
    .stButton>button { width: 100%; height: 3.5rem; font-size: 1.2rem; }
    .stats-box { background-color: #f0f2f6; padding: 15px; border-radius: 10px; margin-bottom: 20px; }
    .correct-word { font-size: 28px; font-weight: bold; color: #2e7d32; }
    .wrong-word { font-size: 28px; font-weight: bold; color: #d32f2f; text-decoration: line-through; }
</style>
""", unsafe_allow_html=True)

# ---------- 数据文件 ----------
DATA_FILE = "word_data_ultimate.json"
if not os.path.exists(DATA_FILE):
    default_data = {
        "words": [],
        "progress": {},
        "user_stats": {"streak": 0, "last_study": None},
        "mistake_book": {}
    }
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(default_data, f, ensure_ascii=False, indent=2)

def load_data():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def update_streak(data):
    today = datetime.now().date().isoformat()
    last = data["user_stats"].get("last_study")
    if last != today:
        if last and (datetime.fromisoformat(last).date() == datetime.now().date() - timedelta(days=1)):
            data["user_stats"]["streak"] += 1
        else:
            data["user_stats"]["streak"] = 1
        data["user_stats"]["last_study"] = today
        save_data(data)

def init_progress(word, difficulty):
    return {
        "ease_factor": 2.5,
        "interval": 0,
        "next_review": datetime.now().date().isoformat(),
        "repetitions": 0,
        "difficulty": difficulty
    }

def calculate_next_review(ease_factor, interval, quality, error_count=0):
    penalty = 1.0 / (1 + error_count * 0.3)
    if quality == 0:
        interval = 0
        next_date = datetime.now().date()
    elif quality == 1:
        interval = max(1, int(1 * penalty))
        next_date = datetime.now().date() + timedelta(days=interval)
    else:
        if interval == 0:
            interval = 1
        elif interval == 1:
            interval = max(2, int(6 * penalty))
        else:
            interval = int(interval * ease_factor * penalty)
        next_date = datetime.now().date() + timedelta(days=interval)
    ease_factor = max(1.3, ease_factor + (0.1 - (3 - quality) * (0.08 + (3 - quality) * 0.02)))
    return ease_factor, interval, next_date

def add_to_mistake_book(data, word):
    if "mistake_book" not in data:
        data["mistake_book"] = {}
    today = datetime.now().date().isoformat()
    if word in data["mistake_book"]:
        data["mistake_book"][word]["error_count"] += 1
        data["mistake_book"][word]["last_error"] = today
    else:
        data["mistake_book"][word] = {"error_count": 1, "last_error": today, "added": today}

def import_from_excel(uploaded_file):
    df = pd.read_excel(uploaded_file)
    required_cols = ["word", "meaning"]
    for col in required_cols:
        if col not in df.columns:
            st.error(f"Excel 必须包含列：{col}")
            return None
    df["pos"] = df.get("pos", "")
    df["phonetic"] = df.get("phonetic", "")
    df["memory_tip"] = df.get("memory_tip", "")
    df["example"] = df.get("example", "")
    df["note"] = df.get("note", "")
    df["difficulty"] = df.get("difficulty", 3).fillna(3).astype(int)
    df["tags"] = df.get("tags", "")
    return df

# ---------- 侧边栏 ----------
data = load_data()
update_streak(data)
words_count = len(data["words"])
mistake_count = len(data.get("mistake_book", {}))
today_str = datetime.now().date().isoformat()

progress = data["progress"]
due_words_normal = [w for w in data["words"] if progress.get(w["word"], init_progress(w["word"], w.get("difficulty", 3)))["next_review"] <= today_str]
due_words_mistake = []
for m_word in data.get("mistake_book", {}):
    word_obj = next((w for w in data["words"] if w["word"] == m_word), None)
    if word_obj:
        p = progress.get(m_word, init_progress(m_word, word_obj.get("difficulty", 3)))
        if p["next_review"] > today_str:
            due_words_mistake.append(word_obj)

st.sidebar.markdown("## 📊 学习进度")
st.sidebar.markdown(f"""
<div class='stats-box'>
    <h3>📚 词库总量：{words_count}</h3>
    <h3>⏳ 今日待复习：{len(due_words_normal) + len(due_words_mistake)}</h3>
    <h3>📕 错题本：{mistake_count} 词</h3>
    <h3>🔥 连续学习：{data['user_stats']['streak']} 天</h3>
</div>
""", unsafe_allow_html=True)

st.title("🐢 笨鸟四级 · 错题强化 + 基础入门")
st.caption("专为极低基础设计 · 四级翻译评分 · 错题优先 · 云端进度保存")

tabs = st.tabs(["📚 今日复习", "✍️ 单词默写", "📕 错题本", "➕ 导入单词", "🌐 翻译练习", "🎓 基础学习"])

# ==================== 标签页1：今日复习 ====================
with tabs[0]:
    st.header("📅 智能复习（错题优先）")
    data = load_data()
    progress = data["progress"]
    mistake_dict = data.get("mistake_book", {})
    today_str = datetime.now().date().isoformat()

    due_normal = [w for w in data["words"] if progress.get(w["word"], init_progress(w["word"], w.get("difficulty", 3)))["next_review"] <= today_str]
    due_mistake = []
    for m_word in mistake_dict:
        word_obj = next((w for w in data["words"] if w["word"] == m_word), None)
        if word_obj:
            p = progress.get(m_word, init_progress(m_word, word_obj.get("difficulty", 3)))
            if p["next_review"] > today_str:
                due_mistake.append(word_obj)
    all_due = due_mistake + due_normal
    all_due.sort(key=lambda w: mistake_dict.get(w["word"], {}).get("error_count", 0), reverse=True)

    if not all_due:
        st.success("🎉 太棒了！今日暂无复习任务。")
    else:
        if "review_list" not in st.session_state or st.button("🔄 刷新列表"):
            st.session_state.review_list = all_due
            st.session_state.review_idx = 0
            st.session_state.show_answer = False
            st.session_state.review_finished = False

        idx = st.session_state.review_idx
        if idx < len(st.session_state.review_list):
            current = st.session_state.review_list[idx]
            word_str = current["word"]
            meaning = current["meaning"]
            pos = current.get("pos", "")
            phonetic = current.get("phonetic", "")
            memory_tip = current.get("memory_tip", "")
            example = current.get("example", "")
            note = current.get("note", "")
            err_count = mistake_dict.get(word_str, {}).get("error_count", 0)
            if err_count > 0:
                st.markdown(f"⚠️ 错题本记录：已错误 **{err_count}** 次")

            st.markdown(f'<div class="big-word">{word_str}</div>', unsafe_allow_html=True)
            if phonetic:
                st.markdown(f'<div class="phonetic">/{phonetic}/</div>', unsafe_allow_html=True)

            col1, col2, _ = st.columns([2,2,6])
            with col1:
                if st.button("🔍 显示释义", key=f"show_{idx}"):
                    st.session_state.show_answer = True
            with col2:
                if st.button("⏭️ 下一个", key=f"next_{idx}"):
                    st.session_state.show_answer = False
                    st.session_state.review_idx += 1
                    st.rerun()

            if st.session_state.show_answer:
                if pos:
                    st.markdown(f'<span class="pos-tag">{pos}</span>', unsafe_allow_html=True)
                st.markdown(f'<div class="meaning">✨ {meaning}</div>', unsafe_allow_html=True)
                if memory_tip:
                    st.markdown(f'<div class="memory-tip">💡 笨鸟记忆法：{memory_tip}</div>', unsafe_allow_html=True)
                if example:
                    st.markdown(f'<div class="example">📝 例句：{example}</div>', unsafe_allow_html=True)
                if note:
                    st.markdown(f'<span class="blue">📌 考点：{note}</span>', unsafe_allow_html=True)

                st.markdown("---")
                st.subheader("🤔 记忆反馈")
                q1, q2, q3, q4 = st.columns(4)
                p = progress.get(word_str, init_progress(word_str, current.get("difficulty", 3)))

                def make_cb(quality, w, cur_word_obj):
                    def cb():
                        data2 = load_data()
                        prog = data2["progress"].get(w, init_progress(w, cur_word_obj.get("difficulty", 3)))
                        err_cnt = data2.get("mistake_book", {}).get(w, {}).get("error_count", 0)
                        ease, interval, next_date = calculate_next_review(prog["ease_factor"], prog["interval"], quality, err_cnt)
                        prog.update({"ease_factor": ease, "interval": interval, "next_review": next_date.isoformat(), "repetitions": prog["repetitions"]+1})
                        data2["progress"][w] = prog
                        if quality == 0:
                            add_to_mistake_book(data2, w)
                        save_data(data2)
                        st.session_state.show_answer = False
                        st.session_state.review_idx += 1
                    return cb

                q1.button("😭 完全没印象", key=f"zero_{word_str}_{idx}", on_click=make_cb(0, word_str, current))
                q2.button("😕 有点困难", key=f"hard_{word_str}_{idx}", on_click=make_cb(1, word_str, current))
                q3.button("🙂 记住了", key=f"good_{word_str}_{idx}", on_click=make_cb(2, word_str, current))
                q4.button("😎 太简单", key=f"easy_{word_str}_{idx}", on_click=make_cb(3, word_str, current))
        else:
            if not st.session_state.get('review_finished', False):
                st.balloons()
                st.session_state.review_finished = True
            st.success("✅ 今日复习任务已完成！")
            if st.button("🔄 重新开始今日复习"):
                st.session_state.review_list = all_due
                st.session_state.review_idx = 0
                st.session_state.show_answer = False
                st.session_state.review_finished = False
                st.rerun()

# ==================== 标签页2：单词默写 ====================
with tabs[1]:
    st.header("✍️ 单词拼写默写（错题自动收录）")
    data = load_data()
    all_words = data["words"]
    if not all_words:
        st.warning("请先导入单词")
    else:
        if "dict_words" not in st.session_state:
            st.session_state.dict_words = []
            st.session_state.dict_idx = 0
            st.session_state.dict_correct = 0
            st.session_state.dict_done = False
            st.session_state.dict_show_res = False
            st.session_state.dict_res_correct = False
            st.session_state.user_ans = ""

        if st.button("🔄 换一组默写词"):
            mistake_words = [w for w in all_words if w["word"] in data.get("mistake_book", {})]
            normal_words = [w for w in all_words if w["word"] not in data.get("mistake_book", {})]
            candidates = mistake_words[:5] + random.sample(normal_words, min(5, len(normal_words)))
            random.shuffle(candidates)
            st.session_state.dict_words = candidates
            st.session_state.dict_idx = 0
            st.session_state.dict_correct = 0
            st.session_state.dict_done = False
            st.session_state.dict_show_res = False
            st.rerun()

        if not st.session_state.dict_done:
            idx = st.session_state.dict_idx
            words = st.session_state.dict_words
            if idx < len(words):
                cur = words[idx]
                word_str = cur["word"]
                meaning = cur["meaning"]
                pos = cur.get("pos", "")
                phonetic = cur.get("phonetic", "")
                tip = cur.get("memory_tip", "")

                st.markdown(f"### 📌 {idx+1}/{len(words)}")
                st.markdown(f"**释义**：<span class='red'>{meaning}</span>", unsafe_allow_html=True)
                if pos:
                    st.markdown(f"**词性**：{pos}")
                if phonetic:
                    st.markdown(f"**音标**：/{phonetic}/")
                user_in = st.text_input("输入英文", key=f"dict_input_{idx}")

                c1, c2 = st.columns([1,3])
                with c1:
                    if st.button("提交", key=f"sub_{idx}"):
                        if user_in.strip().lower() == word_str.lower():
                            st.session_state.dict_correct += 1
                            st.session_state.dict_show_res = True
                            st.session_state.dict_res_correct = True
                        else:
                            st.session_state.dict_show_res = True
                            st.session_state.dict_res_correct = False
                            data2 = load_data()
                            add_to_mistake_book(data2, word_str)
                            prog = data2["progress"].get(word_str, init_progress(word_str, cur.get("difficulty",3)))
                            prog["next_review"] = (datetime.now().date() + timedelta(days=1)).isoformat()
                            data2["progress"][word_str] = prog
                            save_data(data2)
                        st.session_state.user_ans = user_in
                        st.rerun()
                with c2:
                    if st.button("跳过", key=f"skip_{idx}"):
                        st.session_state.dict_show_res = True
                        st.session_state.dict_res_correct = False
                        st.session_state.user_ans = ""
                        st.rerun()

                if st.session_state.dict_show_res:
                    if st.session_state.dict_res_correct:
                        st.success("✅ 正确！")
                        st.markdown(f"**{word_str}**")
                    else:
                        st.error("❌ 拼写错误")
                        st.markdown(f"<span class='wrong-word'>{st.session_state.user_ans}</span> → <span class='correct-word'>{word_str}</span>", unsafe_allow_html=True)
                        if tip:
                            st.markdown(f'<div class="memory-tip">💡 {tip}</div>', unsafe_allow_html=True)
                    if st.button("➡️ 下一题", key=f"next_dict_{idx}"):
                        st.session_state.dict_idx += 1
                        st.session_state.dict_show_res = False
                        if st.session_state.dict_idx >= len(words):
                            st.session_state.dict_done = True
                        st.rerun()
            else:
                st.session_state.dict_done = True
                st.rerun()
        else:
            total = len(st.session_state.dict_words)
            correct = st.session_state.dict_correct
            st.markdown(f"## 🏆 默写完成！正确 {correct}/{total}")
            if st.button("再来一组"):
                for key in ["dict_words","dict_idx","dict_correct","dict_done","dict_show_res","dict_res_correct","user_ans"]:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()

# ==================== 标签页3：错题本 ====================
with tabs[2]:
    st.header("📕 我的错题本")
    data = load_data()
    mb = data.get("mistake_book", {})
    if not mb:
        st.info("暂无错题，继续保持！")
    else:
        rows = []
        for w, info in mb.items():
            word_obj = next((x for x in data["words"] if x["word"] == w), None)
            meaning = word_obj["meaning"] if word_obj else ""
            rows.append({"单词": w, "释义": meaning, "错误次数": info["error_count"], "最近错误": info["last_error"]})
        df_mb = pd.DataFrame(rows)
        st.dataframe(df_mb)
        to_remove = st.multiselect("选择单词移出错题本", df_mb["单词"].tolist())
        if st.button("✅ 移出"):
            for w in to_remove:
                if w in data["mistake_book"]:
                    del data["mistake_book"][w]
            save_data(data)
            st.success("已移出")
            st.rerun()

# ==================== 标签页4：导入单词 ====================
with tabs[3]:
    st.header("📥 导入 Excel 词库")
    st.markdown("列名：word, meaning, pos, phonetic, memory_tip, example, note, difficulty, tags")
    up = st.file_uploader("选择 .xlsx", type=["xlsx"])
    if up:
        df = import_from_excel(up)
        if df is not None:
            st.dataframe(df.head())
            if st.button("确认导入"):
                data = load_data()
                exist = {w["word"] for w in data["words"]}
                new = 0
                for _, row in df.iterrows():
                    w = str(row["word"]).strip()
                    if not w or w in exist:
                        continue
                    entry = {
                        "word": w,
                        "meaning": str(row["meaning"]),
                        "pos": str(row.get("pos", "")),
                        "phonetic": str(row.get("phonetic", "")),
                        "memory_tip": str(row.get("memory_tip", "")),
                        "example": str(row.get("example", "")),
                        "note": str(row.get("note", "")),
                        "difficulty": int(row.get("difficulty", 3)),
                        "tags": str(row.get("tags", ""))
                    }
                    data["words"].append(entry)
                    data["progress"][w] = init_progress(w, entry["difficulty"])
                    new += 1
                save_data(data)
                st.success(f"导入 {new} 个新词")
                st.rerun()

# ==================== 标签页5：翻译练习 ====================
with tabs[4]:
    st.header("🌐 翻译练习（四级评分标准）")
    st.markdown("输入中文句子（支持长篇），系统将模拟四级翻译评分（满分15分），并标注错误单词（自动加入错题本）。")

    # 内置参考译文库（可自行扩展）
    trans_lib = {
        "中国结最初是由手工艺人编织的。": "The Chinese knot was originally woven by craftsmen.",
        "剪纸是中国最受欢迎的民间艺术之一。": "Paper cutting is one of China's most popular folk arts.",
        "茶在中国文化中占有重要地位。": "Tea occupies an important position in Chinese culture."
    }

    user_input = st.text_area("请输入中文句子", height=100)
    user_trans = st.text_area("你的英文翻译", height=150)

    if st.button("提交评分"):
        if not user_input or not user_trans:
            st.warning("请输入中文和英文翻译")
        else:
            # 获取参考译文（如果有）
            ref = trans_lib.get(user_input.strip(), "")
            if not ref:
                st.info("⚠️ 该句子无内置参考译文，将仅进行词汇拼写检查和通顺度评估。")
                ref = user_trans  # 无参考则与自己比较

            # 简单评分逻辑（模拟四级）
            score = 15
            feedback = []
            wrong_words = []

            # 1. 内容完整性（5分）：关键词覆盖率
            chinese_words = set(re.findall(r'[\u4e00-\u9fff]+', user_input))
            # 提取英文中的单词（小写）
            english_words = set(re.findall(r'\b[a-zA-Z]+\b', user_trans.lower()))
            # 这里简化为检查常见名词（需根据实际优化）
            expected_keywords = {"china", "knot", "woven", "craftsmen", "paper", "cutting", "folk", "art", "tea", "culture", "position"}
            found = expected_keywords & english_words
            coverage = len(found) / max(len(expected_keywords), 1)
            if coverage < 0.5:
                score -= 5
                feedback.append("内容缺失较多，关键词未译出。")
            elif coverage < 0.8:
                score -= 2
                feedback.append("部分关键词遗漏。")

            # 2. 语言准确性（5分）：拼写错误检查（对比词库）
            data = load_data()
            known_words = {w["word"].lower() for w in data["words"]}
            user_words = re.findall(r'\b[a-zA-Z]+\b', user_trans)
            for w in user_words:
                if w.lower() not in known_words:
                    wrong_words.append(w)
                    add_to_mistake_book(data, w)
            save_data(data)
            if wrong_words:
                score -= min(5, len(wrong_words))
                feedback.append(f"拼写错误或生词：{', '.join(wrong_words)}（已加入错题本）")
            else:
                feedback.append("单词拼写基本正确。")

            # 3. 结构连贯性（5分）：简单检查句子长度和连接词
            if len(user_trans.split()) < 5:
                score -= 3
                feedback.append("句子过短，结构不完整。")
            elif not re.search(r'\b(and|but|or|because|when|which|that)\b', user_trans, re.I):
                score -= 1
                feedback.append("缺少连接词，句子连贯性一般。")

            score = max(0, score)
            st.markdown(f"### 🎯 得分：{score}/15")
            for fb in feedback:
                st.markdown(f"- {fb}")

            st.markdown("#### ✏️ 优化建议与参考")
            if ref:
                st.markdown(f"**参考译文**：{ref}")
            if wrong_words:
                st.markdown(f"**错误单词已自动加入错题本**，可在「错题本」查看。")

# ==================== 标签页6：基础学习 ====================
with tabs[5]:
    st.header("🎓 基础入门：音标·语法·句型·从句")
    sub_tab1, sub_tab2, sub_tab3, sub_tab4, sub_tab5 = st.tabs(["📢 48音标", "🔤 拼读规则", "🧩 句子成分", "🏗️ 五大句型", "🔗 三大从句"])

    with sub_tab1:
        st.markdown("### 国际音标表（48个）")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**元音 (20个)**")
            st.markdown("""
            **短元音 (7个)**  
            /æ/ (cat)  /e/ (bed)  /ɪ/ (sit)  /ɒ/ (hot)  /ʌ/ (cup)  /ʊ/ (book)  /ə/ (about)

            **长元音 (5个)**  
            /ɑ:/ (car)  /ɔ:/ (saw)  /ɜ:/ (bird)  /i:/ (see)  /u:/ (blue)

            **双元音 (8个)**  
            /eɪ/ (say)  /aɪ/ (my)  /ɔɪ/ (boy)  /aʊ/ (now)  /əʊ/ (go)  /ɪə/ (ear)  /eə/ (air)  /ʊə/ (tour)
            """)
        with col2:
            st.markdown("**辅音 (28个)**")
            st.markdown("""
            **清辅音 (11个)**  
            /p/ (pen)  /t/ (tea)  /k/ (cat)  /f/ (fish)  /s/ (see)  /θ/ (think)  /ʃ/ (she)  /tʃ/ (chair)  /h/ (hat)  /ts/ (cats)  /tr/ (tree)

            **浊辅音 (17个)**  
            /b/ (book)  /d/ (dog)  /g/ (go)  /v/ (van)  /z/ (zoo)  /ð/ (this)  /ʒ/ (vision)  /dʒ/ (job)  /m/ (man)  /n/ (no)  /ŋ/ (sing)  /l/ (leg)  /r/ (red)  /j/ (yes)  /w/ (we)  /dz/ (beds)  /dr/ (dress)
            """)

    with sub_tab2:
        st.markdown("### 自然拼读核心规则")
        st.markdown("""
        1. **辅音+元音**：b-a → ba；c-a-t → cat  
        2. **闭音节**（元音+辅音）：元音发短音，如 cat, bed, hot  
        3. **开音节**（元音+辅音+e）：元音发字母本音，e不发音，如 cake, like, home  
        4. **常见组合**：ch /tʃ/ (chair), sh /ʃ/ (she), th /θ/ 或 /ð/ (think/this)  
        """)

    with sub_tab3:
        st.markdown("### 句子成分（主谓宾定状补）")
        st.markdown("""
        - **主语**：动作发出者（谁/什么） → *I* love English.  
        - **谓语**：动作或状态 → I *love* English.  
        - **宾语**：动作承受者 → I love *English*.  
        - **定语**：修饰名词（...的） → a *red* apple  
        - **状语**：修饰动词（时间/地点/方式） → I run *in the morning*.  
        - **补语**：补充说明主语或宾语 → You make me *happy*.  
        """)

    with sub_tab4:
        st.markdown("### 五大基本句型")
        st.markdown("""
        1. **主谓**：I run.  
        2. **主谓宾**：I love English.  
        3. **主系表**：She is beautiful.  
        4. **主谓双宾**：He gives me a book.  
        5. **主谓宾补**：You make me smile.  
        """)

    with sub_tab5:
        st.markdown("### 三大从句速览")
        st.markdown("""
        **1. 定语从句（修饰名词）**  
        - 引导词：who (人), which (物), that (人/物)  
        - 例：The girl *who is singing* is my sister.

        **2. 状语从句（时间/原因/条件等）**  
        - 时间：*When* I come, I will call you.  
        - 原因：*Because* I like it, I learn English.  
        - 条件：*If* it rains, we will stay at home.

        **3. 名词性从句（作主语/宾语等）**  
        - 宾语从句：I know *that you are right*.  
        - 主语从句：*What he said* is true.
        """)

    st.info("💡 更多语法知识推荐：B站搜「英语的平行世界」「英语兔」")
