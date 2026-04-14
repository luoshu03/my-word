import streamlit as st
import pandas as pd
import random
import json
import os
import re
from datetime import datetime, timedelta
from difflib import SequenceMatcher

# ---------- 页面配置 ----------
st.set_page_config(page_title="笨鸟四级·零基础修复", page_icon="🐢", layout="wide")

# ---------- 初始化 session_state ----------
def init_session_state():
    defaults = {
        'review_list': [], 'review_idx': 0, 'show_answer': False,
        'dict_words': [], 'dict_idx': 0, 'dict_correct': 0, 'dict_done': False,
        'dict_show_res': False, 'dict_res_correct': False, 'user_ans': '',
        'show_guide': True, 'night_mode': False,
        'trans_word_list': [], 'trans_current_word_idx': 0,
        'trans_practice_active': False,
        'trans_bank': [],
        'current_trans_q': None,
        'trans_submitted': False,
        'trans_score_detail': None,
        'trans_corrections': [],
        # 新增：复习乱序种子
        'review_shuffle_seed': random.randint(1, 10000)
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session_state()

# ---------- 夜间模式样式 ----------
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
    .big-word {{ font-size: 4rem; font-weight: bold; text-align: center; margin: 15px 0; }}
    .phonetic {{ font-size: 1.6rem; color: #2c7da0; text-align: center; margin-bottom: 10px; }}
    .pos-tag {{ background-color: #d32f2f; color: white; padding: 4px 12px; border-radius: 20px; font-size: 1rem; display: inline-block; }}
    .meaning {{ font-size: 2rem; margin: 15px 0; font-weight: 500; }}
    .example-box {{ background-color: {'#2a2a2a' if st.session_state.night_mode else '#f0f4f8'}; padding: 18px; border-radius: 12px; margin: 10px 0; border-left: 5px solid #2c7da0; }}
    .memory-tip {{ color: #2d6a4f; padding: 14px; background-color: {'#1e3a1e' if st.session_state.night_mode else '#e8f5e9'}; border-left: 5px solid #40916c; border-radius: 10px; margin: 15px 0; }}
    .mistake-card {{ background-color: {'#2a2a2a' if st.session_state.night_mode else '#fff5f5'}; padding: 18px; border-radius: 12px; margin: 12px 0; border-left: 5px solid #d32f2f; }}
    .feedback-bad {{ color: #d32f2f; font-weight: bold; }}
    .feedback-good {{ color: #2e7d32; font-weight: bold; }}
    .score-box {{ background: linear-gradient(135deg, {'#1e3a5f' if st.session_state.night_mode else '#e3f2fd'}, {'#2a4a6f' if st.session_state.night_mode else '#bbdefb'}); padding: 20px; border-radius: 16px; text-align: center; margin: 15px 0; }}
    .stButton>button {{ width: 100%; height: 3rem; font-size: 1.1rem; border-radius: 10px; }}
    .stats-box {{ background-color: {'#2d2d2d' if st.session_state.night_mode else '#e9ecef'}; padding: 18px; border-radius: 12px; }}
    .th-tip {{ background-color: {'#3a2a1a' if st.session_state.night_mode else '#fff3e0'}; padding: 10px; border-radius: 8px; border: 1px dashed #ff9800; }}
</style>
{night_css}
""", unsafe_allow_html=True)

# ---------- 数据文件 ----------
DATA_FILE = "cet4_zero_data.json"
TRANS_BANK_FILE = "trans_bank.json"

DEFAULT_DATA = {
    "words": [],
    "progress": {},
    "user_stats": {"streak": 0, "last_study": None, "total_days": 0},
    "mistake_book": {},  # 格式: {"word": {"error_count": 0, "correct_streak": 0, "last_error": "", "added": ""}}
    "user_notes": {},
    "daily_plan": {"target": 20, "completed_today": 0}
}

def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            for key in DEFAULT_DATA:
                if key not in data:
                    data[key] = DEFAULT_DATA[key]
            # 确保错题本字段完整
            for w, info in data.get("mistake_book", {}).items():
                if "correct_streak" not in info:
                    info["correct_streak"] = 0
            return data
    except:
        return DEFAULT_DATA.copy()

def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"保存失败: {e}")

def load_trans_bank():
    try:
        with open(TRANS_BANK_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_trans_bank(bank):
    try:
        with open(TRANS_BANK_FILE, "w", encoding="utf-8") as f:
            json.dump(bank, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"保存翻译题库失败: {e}")

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
    return {
        "ease_factor": 2.5,
        "interval": 0,
        "next_review": datetime.now().date().isoformat(),
        "repetitions": 0,
        "difficulty": difficulty
    }

def calculate_next_review(ease_factor, interval, quality, error_count=0):
    penalty = 1.0 / (1 + error_count * 0.35)
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
        data["mistake_book"][word]["error_count"] = data["mistake_book"][word].get("error_count", 0) + 1
        data["mistake_book"][word]["last_error"] = today
        data["mistake_book"][word]["correct_streak"] = 0  # 重置连续正确次数
    else:
        data["mistake_book"][word] = {
            "error_count": 1, 
            "correct_streak": 0,
            "last_error": today, 
            "added": today
        }

def record_correct_in_mistake(data, word):
    """记录错题本中单词的正确回答，连续正确5次自动移除"""
    if word in data.get("mistake_book", {}):
        data["mistake_book"][word]["correct_streak"] = data["mistake_book"][word].get("correct_streak", 0) + 1
        # 连续正确5次，自动移出错题本
        if data["mistake_book"][word]["correct_streak"] >= 5:
            del data["mistake_book"][word]
            return True
    return False

def extract_english_words(text):
    if not text:
        return []
    text = text.lower()
    words = re.findall(r'\b[a-zA-Z]{2,}\b', text)
    return list(set(words))

def extract_key_chinese_terms(chinese_text):
    """从中文提取关键词（用于句意覆盖评分）"""
    # 简单规则：提取2-4字的名词短语
    terms = re.findall(r'[\u4e00-\u9fff]{2,4}', chinese_text)
    # 过滤常见虚词
    stopwords = {'这是', '那是', '这个', '那个', '一个', '一种', '一些', '很多', '非常', '十分', '特别'}
    return [t for t in terms if t not in stopwords][:10]

def calculate_word_accuracy(user_words, reference_words):
    """计算单词拼写准确率"""
    if not reference_words:
        return 0, []
    
    user_set = set(user_words)
    ref_set = set(reference_words)
    
    correct_words = user_set & ref_set
    accuracy = len(correct_words) / len(ref_set) if ref_set else 0
    
    missing = list(ref_set - user_set)
    extra = list(user_set - ref_set)
    
    return accuracy, correct_words, missing, extra

# ---------- 重构：四级翻译评分系统（务实版）----------
class PracticalTranslationScorer:
    """基于句意覆盖和单词拼写的务实评分器"""
    
    def __init__(self, reference_en, chinese_text=""):
        self.reference = reference_en
        self.chinese = chinese_text
        self.ref_words = extract_english_words(reference_en)
        self.key_terms = extract_key_chinese_terms(chinese_text) if chinese_text else []
    
    def score(self, user_trans):
        """返回: (总分15, 评分详情dict)"""
        if not user_trans or len(user_trans.strip()) < 3:
            return 0, {
                "total": 0,
                "word_score": 0,
                "meaning_score": 0,
                "grade": "不及格 (0分)",
                "issues": ["译文过短，无法评分"],
                "missing_words": [],
                "extra_words": [],
                "suggestions": []
            }
        
        user_words = extract_english_words(user_trans)
        
        # 1. 单词拼写评分 (8分)
        word_accuracy, correct_words, missing_words, extra_words = calculate_word_accuracy(
            user_words, self.ref_words
        )
        word_score = min(8, int(word_accuracy * 8))
        
        # 2. 句意覆盖评分 (7分) - 基于关键词命中率
        meaning_score = 0
        if self.key_terms:
            # 检查中文关键词是否在英文翻译中有对应（简单版：检查是否有相关英文词）
            # 这里用粗略估算：用户词数/参考词数 和 用户词是否覆盖常见主题词
            coverage = len(user_words) / max(1, len(self.ref_words))
            meaning_score = min(7, int(coverage * 7))
        else:
            # 无中文原文时，基于词数比例
            coverage = len(user_words) / max(1, len(self.ref_words))
            meaning_score = min(7, int(coverage * 7))
        
        total = word_score + meaning_score
        
        # 确定分档
        if total >= 13:
            grade = "优秀 (13-15分)"
        elif total >= 10:
            grade = "良好 (10-12分)"
        elif total >= 7:
            grade = "中等 (7-9分)"
        elif total >= 4:
            grade = "及格 (4-6分)"
        else:
            grade = "不及格 (1-3分)"
        
        # 生成问题和建议
        issues = []
        suggestions = []
        
        if missing_words:
            issues.append(f"遗漏关键词: {', '.join(missing_words[:5])}")
            suggestions.append("检查是否遗漏了中文原文的关键信息")
        
        if extra_words and len(extra_words) > 3:
            issues.append(f"可能存在多余或拼写错误的词: {', '.join(extra_words[:5])}")
            suggestions.append("确认这些单词是否必要，或检查拼写")
        
        if word_accuracy < 0.5:
            issues.append("单词拼写错误较多")
            suggestions.append("建议先背诵题目相关的核心词汇")
        
        if len(user_trans.split()) < 5:
            issues.append("句子过短，表达不完整")
            suggestions.append("尝试写出完整的简单句，如'主谓宾'结构")
        
        return total, {
            "total": total,
            "word_score": word_score,
            "meaning_score": meaning_score,
            "grade": grade,
            "issues": issues,
            "missing_words": missing_words[:5],
            "extra_words": extra_words[:5],
            "correct_words": list(correct_words)[:10],
            "suggestions": suggestions,
            "word_accuracy": f"{word_accuracy*100:.0f}%"
        }

# ---------- 加载数据 ----------
data = load_data()
update_streak(data)
words = data["words"]
progress = data["progress"]
mistake_dict = data["mistake_book"]
user_notes = data.get("user_notes", {})

if not st.session_state.trans_bank:
    st.session_state.trans_bank = load_trans_bank()

today_str = datetime.now().date().isoformat()

# 计算待复习单词
due_normal = [w for w in words if progress.get(w["word"], init_progress(w["word"], w.get("difficulty",3)))["next_review"] <= today_str]
due_mistake = []
for m_word in mistake_dict:
    w_obj = next((w for w in words if w["word"] == m_word), None)
    if w_obj:
        p = progress.get(m_word, init_progress(m_word, w_obj.get("difficulty",3)))
        if p["next_review"] > today_str:
            due_mistake.append(w_obj)

# ---------- 侧边栏 ----------
st.sidebar.markdown("## 🐢 笨鸟数据")
st.sidebar.markdown(f"""
<div class='stats-box'>
    <h3>📚 词库：{len(words)}</h3>
    <h3>⏳ 待复习：{len(due_normal)+len(due_mistake)}</h3>
    <h3>📕 错题本：{len(mistake_dict)}</h3>
    <h3>🔥 连续：{data['user_stats']['streak']} 天</h3>
    <h3>📅 总天数：{data['user_stats']['total_days']}</h3>
    <h3>📋 题库：{len(st.session_state.trans_bank)} 题</h3>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("---")
target = data["daily_plan"].get("target", 20)
st.sidebar.markdown(f"### 🎯 每日目标：{target}词")
new_target = st.sidebar.number_input("调整目标", min_value=5, max_value=100, value=target, step=5)
if new_target != target:
    data["daily_plan"]["target"] = new_target
    save_data(data)

if st.sidebar.button("🌙 夜间模式" if not st.session_state.night_mode else "☀️ 日间模式"):
    st.session_state.night_mode = not st.session_state.night_mode
    st.rerun()

# ---------- 新手引导 ----------
if st.session_state.show_guide:
    with st.expander("🐣 零基础必读（点击收起）", expanded=True):
        st.markdown("""
        ### 🔥 使用指南
        1. **导入单词**：在「导入单词」上传Excel词库
        2. **翻译练习**：导入真题后，系统基于「句意覆盖+单词拼写」评分
        3. **错题本**：错误单词自动收录，连续正确5次自动移出
        4. **每日复习**：错题优先，每次进入顺序随机打乱
        """)
        if st.button("开始学习"):
            st.session_state.show_guide = False
            st.rerun()

# ---------- 主界面 ----------
st.title("🐢 笨鸟四级 · 务实翻译版")
st.caption("句意评分 · 错题强化 · 乱序复习")

tabs = st.tabs(["📚 复习", "✍️ 默写", "📕 错题本", "📋 翻译题库", "🌐 翻译练习", "➕ 导入单词", "📖 词库", "📊 数据"])

# ==================== 标签页1：今日复习（乱序+错题优先） ====================
with tabs[0]:
    st.header("📅 智能复习（每次进入顺序随机）")
    
    # 合并待复习列表，错题优先
    all_due = due_mistake + due_normal
    
    # 每次刷新或进入时重新乱序
    if st.button("🔄 刷新/重新乱序") or "review_list" not in st.session_state:
        random.seed(st.session_state.review_shuffle_seed)
        random.shuffle(all_due)
        # 但仍让错题尽量靠前（加权排序：错题次数多的在前）
        all_due.sort(key=lambda w: mistake_dict.get(w["word"], {}).get("error_count", 0), reverse=True)
        st.session_state.review_list = all_due
        st.session_state.review_idx = 0
        st.session_state.show_answer = False
        st.session_state.review_shuffle_seed = random.randint(1, 10000)

    if not all_due:
        st.success("🎉 今日暂无复习任务！去「翻译练习」练练手吧。")
    else:
        idx = st.session_state.review_idx
        if idx < len(st.session_state.review_list):
            cur = st.session_state.review_list[idx]
            word_str = cur["word"]
            meaning = cur["meaning"]
            pos = cur.get("pos", "")
            phonetic = cur.get("phonetic", "")
            memory_tip = cur.get("memory_tip", "")
            example = cur.get("example", "")

            err_count = mistake_dict.get(word_str, {}).get("error_count", 0)
            correct_streak = mistake_dict.get(word_str, {}).get("correct_streak", 0)
            
            if err_count > 0:
                st.markdown(f"⚠️ 错题本：错误 {err_count} 次 | 连续正确 {correct_streak}/5 次")
                if correct_streak >= 4:
                    st.info("💪 再正确一次即可移出错题本！")

            st.markdown(f'<div class="big-word">{word_str}</div>', unsafe_allow_html=True)
            if phonetic:
                st.markdown(f'<div class="phonetic">🔊 /{phonetic}/</div>', unsafe_allow_html=True)
                st.components.v1.html(f"""
                <script>
                function speak() {{
                    var msg = new SpeechSynthesisUtterance('{word_str}');
                    msg.lang = 'en-US';
                    msg.rate = 0.8;
                    window.speechSynthesis.speak(msg);
                }}
                </script>
                <button onclick="speak()" style="padding:8px 16px; background:#2c7da0; color:white; border:none; border-radius:20px;">🔊 听发音</button>
                """, height=50)

            if 'th' in word_str.lower():
                st.markdown("""
                <div class='th-tip'>
                🦷 <b>TH音口型提示</b>：舌尖轻贴上齿背，气流从缝隙挤出。
                </div>
                """, unsafe_allow_html=True)

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
                    st.markdown(f'<div class="memory-tip">💡 {memory_tip}</div>', unsafe_allow_html=True)

                if example:
                    st.markdown("---")
                    st.markdown(f'<div class="example-box"><b>📝 例句</b><br>{example}</div>', unsafe_allow_html=True)

                st.subheader("🤔 记忆反馈")
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
                            # 正确回答，记录连续正确
                            removed = record_correct_in_mistake(data2, w)
                            if removed:
                                st.toast(f"🎉 {w} 已从错题本毕业！", icon="✅")
                        
                        save_data(data2)
                        st.session_state.show_answer = False
                        st.session_state.review_idx += 1
                    return cb

                q1.button("😭 完全忘记", key=f"zero_{word_str}_{idx}", on_click=make_cb(0, word_str, cur))
                q2.button("😕 有点困难", key=f"hard_{word_str}_{idx}", on_click=make_cb(1, word_str, cur))
                q3.button("🙂 记住了", key=f"good_{word_str}_{idx}", on_click=make_cb(2, word_str, cur))
                q4.button("😎 太简单", key=f"easy_{word_str}_{idx}", on_click=make_cb(3, word_str, cur))
        else:
            st.success("✅ 今日复习完成！")
            if st.button("🔄 重新开始复习"):
                random.shuffle(all_due)
                all_due.sort(key=lambda w: mistake_dict.get(w["word"], {}).get("error_count", 0), reverse=True)
                st.session_state.review_list = all_due
                st.session_state.review_idx = 0
                st.session_state.show_answer = False
                st.rerun()

# ==================== 标签页2：单词默写 ====================
with tabs[1]:
    st.header("✍️ 单词拼写默写")
    if not words:
        st.warning("请先导入单词")
    else:
        if st.button("🔄 换一组默写词") or "dict_words" not in st.session_state:
            mistake_words = [w for w in words if w["word"] in mistake_dict]
            normal_words = [w for w in words if w["word"] not in mistake_dict]
            # 错题优先，但仍随机抽取
            random.shuffle(mistake_words)
            random.shuffle(normal_words)
            candidates = mistake_words[:5] + normal_words[:5]
            random.shuffle(candidates)
            st.session_state.dict_words = candidates
            st.session_state.dict_idx = 0
            st.session_state.dict_correct = 0
            st.session_state.dict_done = False
            st.session_state.dict_show_res = False

        if not st.session_state.dict_done:
            idx = st.session_state.dict_idx
            wlist = st.session_state.dict_words
            if idx < len(wlist):
                cur = wlist[idx]
                word_str = cur["word"]
                meaning = cur["meaning"]
                pos = cur.get("pos", "")
                phonetic = cur.get("phonetic", "")
                tip = cur.get("memory_tip", "")

                st.markdown(f"### 📌 {idx+1}/{len(wlist)}")
                st.markdown(f"**释义**：<span class='feedback-bad'>{meaning}</span>", unsafe_allow_html=True)
                if pos: st.markdown(f"**词性**：{pos}")
                if phonetic: st.markdown(f"**音标**：/{phonetic}/")
                
                if st.button(f"🔊 听发音", key=f"hear_{idx}"):
                    st.components.v1.html(f"""
                    <script>
                        var msg = new SpeechSynthesisUtterance('{word_str}');
                        msg.lang = 'en-US';
                        window.speechSynthesis.speak(msg);
                    </script>
                    """, height=0)

                user_in = st.text_input("输入英文", key=f"dict_input_{idx}")

                c1, c2 = st.columns([1,3])
                with c1:
                    if st.button("提交", key=f"sub_{idx}"):
                        data2 = load_data()
                        if user_in.strip().lower() == word_str.lower():
                            st.session_state.dict_correct += 1
                            st.session_state.dict_show_res = True
                            st.session_state.dict_res_correct = True
                            # 正确时记录连续正确
                            record_correct_in_mistake(data2, word_str)
                        else:
                            st.session_state.dict_show_res = True
                            st.session_state.dict_res_correct = False
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
                    else:
                        st.error("❌ 拼写错误")
                        st.markdown(f"**你的输入**：{st.session_state.user_ans}  →  **正确答案**：{word_str}")
                        if tip: st.markdown(f'<div class="memory-tip">💡 {tip}</div>', unsafe_allow_html=True)
                    if st.button("➡️ 下一题", key=f"next_dict_{idx}"):
                        st.session_state.dict_idx += 1
                        st.session_state.dict_show_res = False
                        if st.session_state.dict_idx >= len(wlist):
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
                for k in ["dict_words","dict_idx","dict_correct","dict_done","dict_show_res"]:
                    if k in st.session_state: del st.session_state[k]
                st.rerun()

# ==================== 标签页3：错题本（增强显示） ====================
with tabs[2]:
    st.header("📕 错题本 · 强化复习")
    mb = data.get("mistake_book", {})
    if not mb:
        st.info("暂无错题，去翻译练习或默写积累吧")
    else:
        st.markdown(f"### 📊 共 {len(mb)} 个错题")
        st.markdown("连续正确5次可自动移出，也可手动移出")
        
        # 按错误次数排序显示
        sorted_mistakes = sorted(mb.items(), key=lambda x: x[1].get("error_count", 0), reverse=True)
        
        for w, info in sorted_mistakes:
            w_obj = next((x for x in words if x["word"] == w), None)
            if w_obj:
                with st.container():
                    st.markdown(f"""
                    <div class='mistake-card'>
                        <h3>🔤 {w} 
                        <span style='font-size:1rem; margin-left:15px;'>❌ 错误 {info.get('error_count', 0)} 次</span>
                        <span style='font-size:1rem; margin-left:15px; color: {'#2e7d32' if info.get('correct_streak',0) >= 3 else '#f57c00'};'>
                            ✅ 连续正确 {info.get('correct_streak', 0)}/5
                        </span>
                        </h3>
                        <p><b>释义：</b>{w_obj['meaning']}</p>
                        <p><b>词性：</b>{w_obj.get('pos', '—')}  |  <b>音标：</b>/{w_obj.get('phonetic', '—')}/</p>
                    """, unsafe_allow_html=True)
                    
                    if w_obj.get('memory_tip'):
                        st.markdown(f"<p><b>💡 记忆技巧：</b>{w_obj['memory_tip']}</p>", unsafe_allow_html=True)
                    
                    if w_obj.get('example'):
                        st.markdown(f"<p><b>📝 例句：</b>{w_obj['example']}</p>", unsafe_allow_html=True)
                    
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                    # 快速操作
                    col_op1, col_op2, col_op3 = st.columns(3)
                    with col_op1:
                        if st.button(f"🔊 听发音", key=f"mistake_hear_{w}"):
                            st.components.v1.html(f"""
                            <script>
                                var msg = new SpeechSynthesisUtterance('{w}');
                                msg.lang = 'en-US';
                                window.speechSynthesis.speak(msg);
                            </script>
                            """, height=0)
                    with col_op2:
                        if st.button(f"📝 立即复习", key=f"mistake_review_{w}"):
                            # 将这个单词加入今日复习并跳转
                            st.session_state.review_list = [w_obj]
                            st.session_state.review_idx = 0
                            st.session_state.show_answer = False
                            st.success(f"已添加 {w} 到复习列表，请前往「复习」标签页")
                    with col_op3:
                        if st.button(f"🗑️ 手动移出", key=f"mistake_remove_{w}"):
                            del data["mistake_book"][w]
                            save_data(data)
                            st.success(f"已移出 {w}")
                            st.rerun()
                    
                    # 进度条
                    progress_pct = info.get('correct_streak', 0) / 5
                    st.progress(progress_pct, text=f"毕业进度 {info.get('correct_streak', 0)}/5")
                    st.markdown("---")
        
        # 批量操作
        st.markdown("### ⚙️ 批量操作")
        if st.button("🗑️ 清空所有错题", type="secondary"):
            data["mistake_book"] = {}
            save_data(data)
            st.success("错题本已清空")
            st.rerun()

# ==================== 标签页4：翻译题库 ====================
with tabs[3]:
    st.header("📋 翻译真题库")
    st.markdown("导入Excel，需包含「中文原文」和「参考译文」两列")
    
    with st.expander("➕ 导入翻译真题", expanded=False):
        trans_file = st.file_uploader("选择Excel文件", type=["xlsx"], key="trans_bank_upload")
        if trans_file:
            try:
                df = pd.read_excel(trans_file)
                if "中文原文" not in df.columns or "参考译文" not in df.columns:
                    st.error("Excel必须包含「中文原文」和「参考译文」两列")
                else:
                    df = df.fillna("")
                    st.dataframe(df.head())
                    if st.button("确认导入到题库"):
                        new_items = []
                        for _, row in df.iterrows():
                            ch = str(row["中文原文"]).strip()
                            en = str(row["参考译文"]).strip()
                            if ch and en:
                                new_items.append({
                                    "id": datetime.now().timestamp() + len(new_items),
                                    "chinese": ch,
                                    "reference": en,
                                    "topic": str(row.get("话题", "")),
                                    "difficulty": int(row.get("难度", 3))
                                })
                        st.session_state.trans_bank.extend(new_items)
                        save_trans_bank(st.session_state.trans_bank)
                        st.success(f"成功导入 {len(new_items)} 道翻译题")
                        st.rerun()
            except Exception as e:
                st.error(f"导入失败：{e}")
    
    if not st.session_state.trans_bank:
        st.info("暂无翻译题目，请先导入真题")
    else:
        st.markdown(f"### 📚 当前题库（共{len(st.session_state.trans_bank)}题）")
        
        for i, item in enumerate(st.session_state.trans_bank[:15]):
            with st.container():
                col1, col2, col3 = st.columns([6, 2, 2])
                with col1:
                    st.markdown(f"**{i+1}. {item['chinese'][:60]}...**")
                    if st.button("📝 练习", key=f"practice_{i}"):
                        st.session_state.current_trans_q = item
                        st.session_state.trans_submitted = False
                        st.session_state.trans_score_detail = None
                        st.success(f"已选题，请前往「翻译练习」作答")
                with col2:
                    st.markdown(f"难度：{'⭐'*item.get('difficulty',3)}")
                with col3:
                    if st.button("🗑️", key=f"del_trans_{i}"):
                        st.session_state.trans_bank.pop(i)
                        save_trans_bank(st.session_state.trans_bank)
                        st.rerun()
                st.markdown("---")

# ==================== 标签页5：翻译练习（务实评分） ====================
with tabs[4]:
    st.header("🌐 四级翻译练习（句意+单词评分）")
    
    # 选题
    if st.session_state.trans_bank:
        options = [f"{i+1}. {q['chinese'][:40]}..." for i, q in enumerate(st.session_state.trans_bank)]
        selected_idx = st.selectbox("从题库选题", range(len(options)), format_func=lambda x: options[x])
        if st.button("📌 选定此题"):
            st.session_state.current_trans_q = st.session_state.trans_bank[selected_idx]
            st.session_state.trans_submitted = False
            st.session_state.trans_score_detail = None
            st.rerun()
    
    if st.button("🔄 自由练习模式"):
        st.session_state.current_trans_q = None
        st.session_state.trans_submitted = False
        st.rerun()
    
    st.markdown("---")
    
    # 题目展示
    if st.session_state.current_trans_q:
        q = st.session_state.current_trans_q
        st.markdown("### 📝 当前题目")
        st.markdown(f"""
        <div class='example-box'>
            <b>中文原文：</b><br>
            {q['chinese']}
        </div>
        """, unsafe_allow_html=True)
        
        with st.expander("🔍 查看参考译文（建议先自己翻译）"):
            st.markdown(f"**参考译文**：{q['reference']}")
        
        ref_text = q['reference']
        chinese_text = q['chinese']
    else:
        st.markdown("### ✏️ 自由练习")
        chinese_text = st.text_area("输入中文原文（用于句意评分）", height=60, 
                                    placeholder="例如：火锅在中国非常受欢迎。")
        ref_text = st.text_area("输入参考译文（用于单词评分）", height=80, 
                               placeholder="例如：Hot pot is very popular in China.")
    
    user_trans = st.text_area("✍️ 你的英文翻译", height=150, 
                             placeholder="在这里输入你的英文翻译...",
                             key="user_trans_input")
    
    if st.button("📊 提交评分", type="primary"):
        if not user_trans:
            st.warning("请输入翻译")
        else:
            st.session_state.trans_submitted = True
            
            # 使用务实评分器
            if ref_text:
                scorer = PracticalTranslationScorer(ref_text, chinese_text)
                score, detail = scorer.score(user_trans)
            else:
                # 无参考译文时只做基础单词提取
                user_words = extract_english_words(user_trans)
                score = 0
                detail = {
                    "total": 0,
                    "word_score": 0,
                    "meaning_score": 0,
                    "grade": "无法评分（无参考译文）",
                    "issues": ["请提供参考译文以获得准确评分"],
                    "missing_words": [],
                    "extra_words": user_words[:5],
                    "suggestions": ["建议导入或输入参考译文"]
                }
            
            st.session_state.trans_score_detail = detail
            
            # 提取生词加入错题本
            user_words = extract_english_words(user_trans)
            known_words = {w["word"].lower() for w in words}
            common_words = {'the','a','an','is','are','was','were','be','been','have','has','had',
                           'do','does','did','and','but','or','of','in','on','at','to','for','with',
                           'by','from','as','it','this','that','these','those','i','you','he','she',
                           'we','they','my','your','his','her','our','their','me','him','us','them'}
            
            new_word_count = 0
            data2 = load_data()
            for w in user_words:
                if w not in known_words and w not in common_words and len(w) > 2:
                    add_to_mistake_book(data2, w)
                    new_word_count += 1
            save_data(data2)
            
            if new_word_count > 0:
                st.info(f"📚 从翻译中收录 {new_word_count} 个生词到错题本")
            
            st.rerun()
    
    # 显示评分结果
    if st.session_state.trans_submitted and st.session_state.trans_score_detail:
        detail = st.session_state.trans_score_detail
        
        st.markdown("---")
        st.markdown("### 📊 评分结果")
        
        st.markdown(f"""
        <div class='score-box'>
            <h2 style='margin:0; font-size:3rem;'>{detail['total']}/15</h2>
            <p style='margin:5px 0; font-size:1.2rem;'>{detail['grade']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            st.metric("单词拼写得分", f"{detail['word_score']}/8")
            st.caption(f"正确率: {detail.get('word_accuracy', '—')}")
        with col_s2:
            st.metric("句意覆盖得分", f"{detail['meaning_score']}/7")
        
        # 正确拼写的单词
        if detail.get('correct_words'):
            st.markdown(f"✅ **拼写正确的词**：{', '.join(detail['correct_words'])}")
        
        # 问题与建议
        if detail.get('issues'):
            st.markdown("#### ⚠️ 发现问题")
            for issue in detail['issues']:
                st.markdown(f"- {issue}")
        
        if detail.get('missing_words'):
            st.markdown(f"#### 📌 遗漏的关键词")
            st.markdown(f"`{', '.join(detail['missing_words'])}`")
            
            # 一键加入复习
            if st.button("📚 将这些词加入今日复习"):
                for w in detail['missing_words']:
                    if w not in [word["word"] for word in words]:
                        # 临时加入词库
                        new_word = {
                            "word": w, "meaning": "(待补充)", "pos": "", "phonetic": "",
                            "memory_tip": "来自翻译练习", "example": "", "difficulty": 3
                        }
                        data["words"].append(new_word)
                        data["progress"][w] = init_progress(w, 3)
                    add_to_mistake_book(data, w)
                save_data(data)
                st.success("已加入错题本，稍后复习")
        
        if detail.get('extra_words'):
            st.markdown(f"#### 🔍 可能拼写有误的词")
            st.markdown(f"`{', '.join(detail['extra_words'])}`")
        
        if detail.get('suggestions'):
            st.markdown("#### 💡 改进建议")
            for sug in detail['suggestions']:
                st.markdown(f"- {sug}")
        
        # 重新翻译
        if st.button("🔄 重新翻译"):
            st.session_state.trans_submitted = False
            st.session_state.trans_score_detail = None
            st.rerun()

# ==================== 标签页6：导入单词 ====================
with tabs[5]:
    st.header("📥 导入Excel词库")
    st.markdown("必需列：word, meaning；可选：pos, phonetic, memory_tip, example, difficulty")
    up = st.file_uploader("选择.xlsx", type=["xlsx"])
    if up:
        try:
            df = pd.read_excel(up)
            if "word" not in df.columns or "meaning" not in df.columns:
                st.error("缺少word或meaning列")
            else:
                df = df.fillna("")
                st.dataframe(df.head())
                if st.button("确认导入"):
                    data = load_data()
                    exist = {w["word"].lower() for w in data["words"]}
                    new = 0
                    for _, row in df.iterrows():
                        w = str(row["word"]).strip()
                        if not w or w.lower() in exist:
                            continue
                        entry = {
                            "word": w, "meaning": str(row["meaning"]),
                            "pos": str(row.get("pos", "")), "phonetic": str(row.get("phonetic", "")),
                            "memory_tip": str(row.get("memory_tip", "")), "example": str(row.get("example", "")),
                            "difficulty": int(row.get("difficulty", 3))
                        }
                        data["words"].append(entry)
                        data["progress"][w] = init_progress(w, entry["difficulty"])
                        new += 1
                    save_data(data)
                    st.success(f"导入 {new} 个新词")
                    st.rerun()
        except Exception as e:
            st.error(f"导入失败：{e}")

# ==================== 标签页7：单词库 ====================
with tabs[6]:
    st.header("📖 单词库管理")
    if words:
        df_words = pd.DataFrame(words)
        st.dataframe(df_words[["word","meaning","pos","difficulty"]])
        to_del = st.multiselect("删除单词", df_words["word"].tolist())
        if st.button("删除选中"):
            data["words"] = [w for w in words if w["word"] not in to_del]
            for w in to_del:
                if w in data["progress"]: del data["progress"][w]
                if w in data["mistake_book"]: del data["mistake_book"][w]
            save_data(data)
            st.success("删除成功")
            st.rerun()
    else:
        st.info("暂无单词")

# ==================== 标签页8：学习数据 ====================
with tabs[7]:
    st.header("📊 详细学习数据")
    data = load_data()
    st.markdown(f"- 总单词量：{len(words)}")
    st.markdown(f"- 错题本单词数：{len(data.get('mistake_book', {}))}")
    st.markdown(f"- 连续打卡：{data['user_stats']['streak']} 天")
    st.markdown(f"- 总学习天数：{data['user_stats']['total_days']} 天")
    st.markdown(f"- 翻译题库：{len(st.session_state.trans_bank)} 题")
    if words:
        total_reviews = sum(p.get("repetitions", 0) for p in data["progress"].values())
        st.markdown(f"- 累计复习次数：{total_reviews}")
