import streamlit as st
import pandas as pd
import random
import json
import os
import re
from datetime import datetime, timedelta
from difflib import SequenceMatcher
import Levenshtein  # 需要安装：pip install python-Levenshtein

# ---------- 页面配置 ----------
st.set_page_config(page_title="笨鸟四级·零基础修复", page_icon="🐢", layout="wide")

# ---------- 初始化 session_state ----------
def init_session_state():
    defaults = {
        'review_list': [], 'review_idx': 0, 'show_answer': False,
        'dict_words': [], 'dict_idx': 0, 'dict_correct': 0, 'dict_done': False,
        'dict_show_res': False, 'dict_res_correct': False, 'user_ans': '',
        'show_guide': True, 'night_mode': False,
        # 翻译联动模块
        'trans_word_list': [],
        'trans_current_word_idx': 0,
        'trans_practice_active': False,
        'last_translation_text': "",
        # 翻译题库相关
        'trans_bank': [],  # 存储导入的翻译题目
        'current_trans_q': None,  # 当前选中的题目
        'trans_submitted': False,  # 是否已提交评分
        'trans_score_detail': None,  # 评分详情
        'trans_corrections': []  # 纠错列表
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session_state()

# ---------- 夜间模式样式 ----------
night_css = """
<style>
    body { background-color: #1e1e1e; color: #e0e0e0; }
    .stButton>button { background-color: #333; color: white; border: 1px solid #555; transition: all 0.1s ease; }
    .stButton>button:active { background-color: #4a4a4a; transform: scale(0.98); }
    .stTextInput>div>div>input { background-color: #2d2d2d; color: white; }
    .stTextArea>div>textarea { background-color: #2d2d2d; color: white; }
</style>
""" if st.session_state.night_mode else ""

st.markdown(f"""
<style>
    body {{ background-color: {'#1e1e1e' if st.session_state.night_mode else '#fafafa'}; }}
    .main {{ color: {'#e0e0e0' if st.session_state.night_mode else '#1e1e1e'}; }}
    .big-word {{ font-size: 4.5rem; font-weight: bold; text-align: center; margin: 15px 0; letter-spacing: 2px; }}
    .phonetic {{ font-size: 1.8rem; color: #2c7da0; text-align: center; margin-bottom: 10px; cursor: pointer; }}
    .pos-tag {{ background-color: #d32f2f; color: white; padding: 4px 12px; border-radius: 20px; font-size: 1.1rem; display: inline-block; }}
    .meaning {{ font-size: 2.2rem; margin: 15px 0; font-weight: 500; }}
    .example-box {{ background-color: {'#2a2a2a' if st.session_state.night_mode else '#f0f4f8'}; padding: 18px; border-radius: 12px; margin: 10px 0; border-left: 5px solid #2c7da0; }}
    .memory-tip {{ color: #2d6a4f; padding: 14px; background-color: {'#1e3a1e' if st.session_state.night_mode else '#e8f5e9'}; border-left: 5px solid #40916c; border-radius: 10px; margin: 15px 0; }}
    .th-tip {{ background-color: {'#3a2a1a' if st.session_state.night_mode else '#fff3e0'}; padding: 10px; border-radius: 8px; border: 1px dashed #ff9800; }}
    .feedback-bad {{ color: #d32f2f; font-weight: bold; }}
    .feedback-good {{ color: #2e7d32; font-weight: bold; }}
    .feedback-warn {{ color: #f57c00; font-weight: bold; }}
    .score-box {{ background: linear-gradient(135deg, {'#1e3a5f' if st.session_state.night_mode else '#e3f2fd'}, {'#2a4a6f' if st.session_state.night_mode else '#bbdefb'}); padding: 20px; border-radius: 16px; text-align: center; margin: 15px 0; }}
    .correction-item {{ background-color: {'#2a2a2a' if st.session_state.night_mode else '#f5f5f5'}; padding: 12px; border-radius: 8px; margin: 8px 0; border-left: 4px solid; }}
    .stButton>button {{ width: 100%; height: 3rem; font-size: 1.1rem; border-radius: 10px; }}
    .stats-box {{ background-color: {'#2d2d2d' if st.session_state.night_mode else '#e9ecef'}; padding: 18px; border-radius: 12px; }}
    @media (max-width: 600px) {{
        .big-word {{ font-size: 3.2rem; }}
        .meaning {{ font-size: 1.6rem; }}
    }}
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
    "mistake_book": {},
    "user_notes": {},
    "daily_plan": {"target": 20, "completed_today": 0},
    "trans_collected_words": []
}

def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            for key in DEFAULT_DATA:
                if key not in data:
                    data[key] = DEFAULT_DATA[key]
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
        data["mistake_book"][word]["error_count"] += 1
        data["mistake_book"][word]["last_error"] = today
    else:
        data["mistake_book"][word] = {"error_count": 1, "last_error": today, "added": today}

def extract_english_words(text):
    if not text:
        return []
    text = text.lower()
    words = re.findall(r'\b[a-zA-Z]{2,}\b', text)
    return list(set(words))

def calculate_similarity(a, b):
    """计算两个字符串的相似度（0-1）"""
    if not a or not b:
        return 0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

# ---------- 四级翻译评分系统（模拟CET-4标准）----------
class CET4TranslationScorer:
    """四级翻译评分器：满分15分，分档：13-15, 10-12, 7-9, 4-6, 1-3, 0"""
    
    def __init__(self, reference):
        self.reference = reference
        self.ref_words = set(extract_english_words(reference))
        self.ref_lower = reference.lower()
    
    def score_and_analyze(self, user_trans):
        """返回: (总分, 分档描述, 详细扣分项列表, 纠错建议列表)"""
        if not user_trans or len(user_trans.strip()) < 3:
            return 0, "空白或过短", [], [{"type": "error", "msg": "译文过短，无法评分"}]
        
        deductions = []
        corrections = []
        total_score = 15
        
        user_lower = user_trans.lower()
        user_words = set(extract_english_words(user_trans))
        
        # 1. 内容完整性评分 (0-5分)
        content_score = 5
        # 漏译检测：参考译文中关键词在用户译文中出现情况
        key_terms = self._extract_key_terms(self.reference)
        missing_terms = []
        for term in key_terms:
            if term.lower() not in user_lower:
                missing_terms.append(term)
                content_score -= 0.5
        
        if len(missing_terms) > 0:
            deductions.append(f"内容遗漏：{', '.join(missing_terms[:5])}")
            corrections.append({
                "type": "content",
                "severity": "warning",
                "msg": f"可能遗漏的关键内容：{', '.join(missing_terms[:3])}",
                "suggestion": "检查是否有重要信息未翻译"
            })
        
        # 2. 语言准确性评分 (0-7分)
        language_score = 7
        
        # 单词拼写/用词错误
        common_words = {'the','a','an','is','are','was','were','be','been','have','has','had',
                       'do','does','did','and','but','or','of','in','on','at','to','for','with',
                       'by','from','as','it','this','that','these','those','i','you','he','she',
                       'we','they','my','your','his','her','our','their','me','him','us','them'}
        
        user_word_list = extract_english_words(user_trans)
        known_words = {w["word"].lower() for w in data.get("words", [])}
        
        spelling_errors = []
        for w in user_word_list:
            if w not in common_words and w not in known_words:
                # 检查是否接近某个已知词
                close_match = None
                for kw in known_words:
                    if Levenshtein.distance(w, kw) <= 2:
                        close_match = kw
                        break
                if close_match:
                    spelling_errors.append(f"{w} → {close_match}")
                    language_score -= 0.5
                else:
                    spelling_errors.append(w)
                    language_score -= 0.3
        
        if spelling_errors:
            deductions.append(f"拼写/用词问题：{', '.join(spelling_errors[:5])}")
            corrections.append({
                "type": "spelling",
                "severity": "error",
                "msg": f"可能错误的单词：{', '.join(spelling_errors[:5])}",
                "suggestion": "检查拼写，或使用更熟悉的词汇"
            })
        
        # 语法结构检查
        grammar_issues = self._check_grammar(user_trans)
        for issue in grammar_issues:
            language_score -= issue.get("penalty", 0.5)
            corrections.append(issue)
        
        if grammar_issues:
            deductions.append(f"语法结构问题：{len(grammar_issues)}处")
        
        # 3. 结构连贯性评分 (0-3分)
        coherence_score = 3
        # 检查连接词使用
        connectors = ['and', 'but', 'because', 'so', 'however', 'therefore', 'which', 'that', 'when', 'where']
        has_connector = any(c in user_lower for c in connectors)
        if not has_connector and len(user_trans.split()) > 8:
            coherence_score -= 1
            deductions.append("缺少连接词，句子连贯性差")
            corrections.append({
                "type": "coherence",
                "severity": "warning",
                "msg": "译文缺少连接词",
                "suggestion": "尝试使用and/but/because等连接词使句子更流畅"
            })
        
        # 句子长度合理性
        if len(user_trans.split()) < 5:
            coherence_score -= 1
            deductions.append("句子过短，表达不完整")
        
        content_score = max(0, min(5, content_score))
        language_score = max(0, min(7, language_score))
        coherence_score = max(0, min(3, coherence_score))
        
        total_score = int(content_score + language_score + coherence_score)
        
        # 确定分档
        if total_score >= 13:
            grade = "优秀 (13-15分)"
            grade_desc = "译文准确表达了原文意思，用词贴切，行文流畅"
        elif total_score >= 10:
            grade = "良好 (10-12分)"
            grade_desc = "译文基本表达了原文意思，文字通顺连贯，无重大语言错误"
        elif total_score >= 7:
            grade = "中等 (7-9分)"
            grade_desc = "译文勉强表达了原文意思，有一些语言错误"
        elif total_score >= 4:
            grade = "及格 (4-6分)"
            grade_desc = "译文仅表达小部分原文意思，语言错误较多"
        else:
            grade = "不及格 (1-3分)"
            grade_desc = "译文支离破碎，除个别词语外，绝大部分未表达原意"
        
        detail = {
            "total": total_score,
            "content": content_score,
            "language": language_score,
            "coherence": coherence_score,
            "grade": grade,
            "grade_desc": grade_desc,
            "deductions": deductions
        }
        
        return total_score, grade, detail, corrections
    
    def _extract_key_terms(self, text):
        """提取关键词（名词短语等）"""
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text)
        # 过滤常见词
        common = {'the','and','but','for','with','that','this','have','from','are','was',
                  'were','been','will','would','could','should','about','their','there'}
        return [w for w in words if w.lower() not in common][:8]
    
    def _check_grammar(self, text):
        """基础语法检查"""
        issues = []
        text_lower = text.lower()
        
        # 主谓一致检查（简单规则）
        if 'there is' in text_lower:
            following = text_lower.split('there is')[-1].strip()
            if following and following[0].isalpha():
                first_word = following.split()[0]
                if first_word.endswith('s') and not first_word.endswith('ss'):
                    issues.append({
                        "type": "grammar",
                        "severity": "error",
                        "penalty": 1,
                        "msg": f"'There is' 后接复数名词 '{first_word}' 可能不一致",
                        "suggestion": "复数用 'There are'"
                    })
        
        if 'there are' in text_lower:
            following = text_lower.split('there are')[-1].strip()
            if following and following[0].isalpha():
                first_word = following.split()[0]
                if not first_word.endswith('s') and first_word not in ['people', 'children', 'men', 'women']:
                    issues.append({
                        "type": "grammar",
                        "severity": "warning",
                        "penalty": 0.5,
                        "msg": f"'There are' 后接单数名词 '{first_word}' 可能不一致",
                        "suggestion": "单数用 'There is'"
                    })
        
        # 冠词缺失检查（简单）
        if re.search(r'\b(is|was|am|are|were|be)\s+[a-z]+', text_lower):
            pass  # 复杂的冠词检查略过
        
        # 句子是否有主语谓语
        has_subject = bool(re.search(r'\b(i|you|he|she|it|we|they|this|that|these|those|[a-z]+s?)\s+(is|am|are|was|were|have|has|had|do|does|did|can|could|will|would|may|might|must|[a-z]+s?)\b', text_lower))
        if not has_subject and len(text.split()) > 3:
            issues.append({
                "type": "structure",
                "severity": "error",
                "penalty": 1,
                "msg": "句子可能缺少主语或谓语",
                "suggestion": "确保每个句子有主语和谓语动词"
            })
        
        return issues

# ---------- 加载数据 ----------
data = load_data()
update_streak(data)
words = data["words"]
progress = data["progress"]
mistake_dict = data["mistake_book"]
user_notes = data.get("user_notes", {})

# 加载翻译题库
if not st.session_state.trans_bank:
    st.session_state.trans_bank = load_trans_bank()

today_str = datetime.now().date().isoformat()
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
    <h3>📋 翻译题库：{len(st.session_state.trans_bank)} 题</h3>
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
    with st.expander("🐣 零基础必读·语音修复指南（点击收起）", expanded=True):
        st.markdown("""
        ### 🔥 核心问题：你的英语声音系统未激活
        - **症状**：单词记不住拼写、听力听不懂、发音不自信。
        - **病根**：背单词时只用眼睛和手，耳朵和嘴巴在睡觉。
        
        ### ✅ 本工具专属修复方案
        1. **翻译真题练习**：导入四级翻译真题，提交后获得详细评分和纠错建议。
        2. **生词自动收录**：翻译中的错误单词自动进入错题本和生词卡。
        3. **发音口型提示**：遇到th音、v音时，查看口型提示，用「纸巾法」检验。
        4. **智能复习**：错题优先，科学间隔。
        """)
        if st.button("我明白了，开始修复"):
            st.session_state.show_guide = False
            st.rerun()

# ---------- 主界面 ----------
st.title("🐢 笨鸟四级 · 翻译专项训练")
st.caption("真题评分 · 生词收录 · 口型模仿 · 错题优先")

tabs = st.tabs(["📚 复习", "✍️ 默写", "📕 错题本", "📋 翻译题库", "🌐 翻译练习", "➕ 导入单词", "📖 词库", "📊 数据"])

# ==================== 标签页1：今日复习 ====================
with tabs[0]:
    st.header("📅 智能复习（错题优先）")
    all_due = due_mistake + due_normal
    all_due.sort(key=lambda w: mistake_dict.get(w["word"], {}).get("error_count", 0), reverse=True)

    if not all_due:
        st.success("🎉 今日暂无复习任务！去「翻译练习」练练手吧。")
    else:
        if "review_list" not in st.session_state or st.button("🔄 刷新列表"):
            st.session_state.review_list = all_due
            st.session_state.review_idx = 0
            st.session_state.show_answer = False

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
            if err_count > 0:
                st.markdown(f"⚠️ 错题本记录：已错 {err_count} 次")

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
                🦷 <b>TH音口型提示</b>：舌尖轻贴上齿背，气流从缝隙挤出。<br>
                👄 <b>无声模仿</b>：先不发声，只用嘴型感受舌尖位置，再轻轻送气。
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
                    st.subheader("📖 例句")
                    st.markdown(f'<div class="example-box"><b>📝</b> {example}</div>', unsafe_allow_html=True)

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
            if st.button("🔄 重新复习"):
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
            candidates = mistake_words[:5] + random.sample(normal_words, min(5, len(normal_words)))
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

# ==================== 标签页3：错题本 ====================
with tabs[2]:
    st.header("📕 错题本")
    mb = data.get("mistake_book", {})
    if not mb:
        st.info("暂无错题，去翻译练习或默写积累吧")
    else:
        rows = []
        for w, info in mb.items():
            w_obj = next((x for x in words if x["word"] == w), None)
            meaning = w_obj["meaning"] if w_obj else ""
            rows.append({"单词": w, "释义": meaning, "错误次数": info["error_count"], "最近错误": info.get("last_error", "")})
        df = pd.DataFrame(rows)
        st.dataframe(df)
        to_remove = st.multiselect("移出错题本", df["单词"].tolist())
        if st.button("✅ 移出"):
            for w in to_remove:
                if w in data["mistake_book"]:
                    del data["mistake_book"][w]
            save_data(data)
            st.success("已移出")
            st.rerun()

# ==================== 标签页4：翻译题库（新增） ====================
with tabs[3]:
    st.header("📋 翻译真题库")
    st.markdown("导入四级翻译真题（Excel格式），包含「中文原文」和「参考译文」两列。")
    
    # 导入功能
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
                                    "topic": row.get("话题", ""),
                                    "difficulty": int(row.get("难度", 3))
                                })
                        st.session_state.trans_bank.extend(new_items)
                        save_trans_bank(st.session_state.trans_bank)
                        st.success(f"成功导入 {len(new_items)} 道翻译题")
                        st.rerun()
            except Exception as e:
                st.error(f"导入失败：{e}")
    
    # 题库展示与管理
    if not st.session_state.trans_bank:
        st.info("暂无翻译题目，请先导入真题")
    else:
        st.markdown(f"### 📚 当前题库（共{len(st.session_state.trans_bank)}题）")
        
        # 显示题目列表
        for i, item in enumerate(st.session_state.trans_bank[:10]):  # 最多显示10题
            with st.container():
                col1, col2, col3 = st.columns([6, 2, 2])
                with col1:
                    st.markdown(f"**{i+1}. {item['chinese'][:50]}...**")
                    if st.button("📝 练习此题", key=f"practice_{i}"):
                        st.session_state.current_trans_q = item
                        st.session_state.trans_submitted = False
                        st.session_state.trans_score_detail = None
                        st.session_state.trans_corrections = []
                        st.success(f"已选题：{item['chinese'][:30]}... 请前往「翻译练习」标签页作答")
                with col2:
                    difficulty = item.get('difficulty', 3)
                    st.markdown(f"难度：{'⭐'*difficulty}")
                with col3:
                    if st.button("🗑️ 删除", key=f"del_trans_{i}"):
                        st.session_state.trans_bank.pop(i)
                        save_trans_bank(st.session_state.trans_bank)
                        st.rerun()
                st.markdown("---")
        
        if len(st.session_state.trans_bank) > 10:
            st.info(f"...还有 {len(st.session_state.trans_bank)-10} 道题")
        
        if st.button("🗑️ 清空题库", type="secondary"):
            st.session_state.trans_bank = []
            save_trans_bank([])
            st.success("题库已清空")
            st.rerun()

# ==================== 标签页5：翻译练习（增强评分） ====================
with tabs[4]:
    st.header("🌐 四级翻译练习（智能评分+纠错）")
    
    # 选题区
    col_sel1, col_sel2 = st.columns([3, 1])
    with col_sel1:
        if st.session_state.trans_bank:
            options = [f"{i+1}. {q['chinese'][:40]}..." for i, q in enumerate(st.session_state.trans_bank)]
            selected_idx = st.selectbox("从题库选题", range(len(options)), format_func=lambda x: options[x])
            if st.button("📌 选定此题"):
                st.session_state.current_trans_q = st.session_state.trans_bank[selected_idx]
                st.session_state.trans_submitted = False
                st.session_state.trans_score_detail = None
                st.session_state.trans_corrections = []
                st.rerun()
        else:
            st.info("暂无题库，请先在「翻译题库」导入真题，或使用下方自由练习")
    
    with col_sel2:
        if st.button("🔄 自由练习模式"):
            st.session_state.current_trans_q = None
            st.session_state.trans_submitted = False
            st.session_state.trans_score_detail = None
            st.rerun()
    
    st.markdown("---")
    
    # 当前题目展示
    if st.session_state.current_trans_q:
        q = st.session_state.current_trans_q
        st.markdown("### 📝 当前题目")
        st.markdown(f"""
        <div class='example-box'>
            <b>中文原文：</b><br>
            {q['chinese']}
        </div>
        """, unsafe_allow_html=True)
        
        # 可折叠查看参考译文（评分前隐藏）
        with st.expander("🔍 查看参考译文（建议先自己翻译）"):
            st.markdown(f"**参考译文**：{q['reference']}")
        
        ref_text = q['reference']
    else:
        st.markdown("### ✏️ 自由练习")
        ref_text = st.text_area("输入参考译文（用于评分对比）", height=80, 
                               placeholder="如果没有参考译文，可以留空，系统将只做基础语法检查")
    
    # 用户翻译输入
    user_trans = st.text_area("✍️ 你的英文翻译", height=150, 
                             placeholder="在这里输入你的英文翻译...",
                             key="user_trans_input")
    
    # 评分按钮
    col_btn1, col_btn2 = st.columns([1, 3])
    with col_btn1:
        submit_btn = st.button("📊 提交评分", type="primary", use_container_width=True)
    
    if submit_btn and user_trans:
        st.session_state.trans_submitted = True
        
        # 执行评分
        if ref_text:
            scorer = CET4TranslationScorer(ref_text)
            score, grade, detail, corrections = scorer.score_and_analyze(user_trans)
        else:
            # 无参考译文时只做基础检查
            score = 0
            grade = "无法评分（无参考译文）"
            detail = {"total": 0, "content": 0, "language": 0, "coherence": 0, 
                     "grade_desc": "请提供参考译文以获得准确评分", "deductions": []}
            corrections = []
            # 基础语法检查
            grammar_issues = CET4TranslationScorer("")._check_grammar(user_trans)
            corrections.extend(grammar_issues)
        
        st.session_state.trans_score_detail = detail
        st.session_state.trans_corrections = corrections
        
        # 提取生词并加入错题本
        user_words = extract_english_words(user_trans)
        known_words = {w["word"].lower() for w in words}
        common_words = {'the','a','an','is','are','was','were','be','been','have','has','had',
                       'do','does','did','and','but','or','of','in','on','at','to','for','with',
                       'by','from','as','it','this','that','these','those','i','you','he','she',
                       'we','they','my','your','his','her','our','their','me','him','us','them'}
        
        new_word_count = 0
        for w in user_words:
            if w not in known_words and w not in common_words:
                add_to_mistake_book(data, w)
                new_word_count += 1
        
        if new_word_count > 0:
            save_data(data)
            st.info(f"📚 从翻译中收录 {new_word_count} 个生词到错题本")
        
        st.rerun()
    
    # 显示评分结果
    if st.session_state.trans_submitted and st.session_state.trans_score_detail:
        detail = st.session_state.trans_score_detail
        corrections = st.session_state.trans_corrections
        
        st.markdown("---")
        st.markdown("### 📊 评分结果")
        
        # 总分展示
        st.markdown(f"""
        <div class='score-box'>
            <h2 style='margin:0; font-size:3rem;'>{detail['total']}/15</h2>
            <p style='margin:5px 0; font-size:1.2rem;'>{detail['grade']}</p>
            <p style='margin:0; opacity:0.9;'>{detail['grade_desc']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # 分项得分
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            st.metric("内容完整性", f"{detail['content']}/5")
        with col_s2:
            st.metric("语言准确性", f"{detail['language']}/7")
        with col_s3:
            st.metric("结构连贯性", f"{detail['coherence']}/3")
        
        # 扣分项
        if detail.get('deductions'):
            st.markdown("#### ⚠️ 主要问题")
            for d in detail['deductions']:
                st.markdown(f"- {d}")
        
        # 详细纠错
        if corrections:
            st.markdown("#### 🔧 纠错建议")
            for i, corr in enumerate(corrections):
                severity_color = "#d32f2f" if corr.get('severity') == 'error' else "#f57c00"
                st.markdown(f"""
                <div class='correction-item' style='border-left-color: {severity_color};'>
                    <b>{corr.get('type', 'issue').upper()}</b>: {corr.get('msg', '')}<br>
                    <span style='color: #2c7da0;'>💡 {corr.get('suggestion', '')}</span>
                </div>
                """, unsafe_allow_html=True)
        
        # 参考译文对比
        if st.session_state.current_trans_q:
            with st.expander("📖 对照参考译文"):
                st.markdown(f"**你的译文**：{user_trans}")
                st.markdown(f"**参考译文**：{st.session_state.current_trans_q['reference']}")
                
                # 计算相似度
                similarity = calculate_similarity(user_trans, st.session_state.current_trans_q['reference'])
                st.progress(similarity, text=f"与参考译文相似度：{similarity*100:.1f}%")
        
        # 生词提取与背诵
        user_words = extract_english_words(user_trans)
        known_words = {w["word"].lower() for w in words}
        common_words = {'the','a','an','is','are','was','were','be','been','have','has','had',
                       'do','does','did','and','but','or','of','in','on','at','to','for','with',
                       'by','from','as','it','this','that','these','those','i','you','he','she',
                       'we','they','my','your','his','her','our','their','me','him','us','them'}
        
        new_words = [w for w in user_words if w not in known_words and w not in common_words]
        
        if new_words:
            st.markdown("---")
            st.markdown("### 📚 翻译中的生词（点击学习）")
            
            if st.button("🎯 开始背诵这些生词"):
                st.session_state.trans_word_list = list(set(new_words))
                st.session_state.trans_current_word_idx = 0
                st.session_state.trans_practice_active = True
                st.rerun()
        
        # 重新开始
        if st.button("🔄 重新翻译"):
            st.session_state.trans_submitted = False
            st.session_state.trans_score_detail = None
            st.session_state.trans_corrections = []
            st.rerun()
    
    # 生词背诵卡片（从翻译联动）
    if st.session_state.trans_practice_active and st.session_state.trans_word_list:
        st.markdown("---")
        st.subheader("📚 生词逐个击破")
        
        word_list = st.session_state.trans_word_list
        idx = st.session_state.trans_current_word_idx
        
        if idx < len(word_list):
            current_word = word_list[idx]
            w_obj = next((w for w in words if w["word"].lower() == current_word), None)
            
            st.markdown(f"### 🔤 单词 {idx+1}/{len(word_list)}：**{current_word}**")
            
            if st.button(f"🔊 听发音", key=f"trans_hear_{idx}"):
                st.components.v1.html(f"""
                <script>
                    var msg = new SpeechSynthesisUtterance('{current_word}');
                    msg.lang = 'en-US';
                    msg.rate = 0.8;
                    window.speechSynthesis.speak(msg);
                </script>
                """, height=0)
            
            if 'th' in current_word:
                st.markdown("""
                <div class='th-tip'>
                🦷 <b>TH音口型提示</b>：舌尖轻贴上齿背，气流从缝隙挤出。
                </div>
                """, unsafe_allow_html=True)
            
            if w_obj:
                st.markdown(f"**释义**：{w_obj['meaning']}")
                if w_obj.get('phonetic'):
                    st.markdown(f"**音标**：/{w_obj['phonetic']}/")
            else:
                user_meaning = st.text_input("📝 输入释义", key=f"temp_mean_{idx}")
                if st.button("保存并加入词库", key=f"save_temp_{idx}"):
                    if user_meaning:
                        new_word_entry = {
                            "word": current_word,
                            "meaning": user_meaning,
                            "pos": "",
                            "phonetic": "",
                            "memory_tip": "",
                            "example": "",
                            "note": "",
                            "difficulty": 3,
                            "tags": "翻译提取"
                        }
                        data["words"].append(new_word_entry)
                        data["progress"][current_word] = init_progress(current_word, 3)
                        save_data(data)
                        st.success(f"已添加 {current_word}")
                        st.rerun()
            
            user_spell = st.text_input("✍️ 拼写一遍", key=f"spell_{idx}")
            if user_spell and user_spell.strip().lower() == current_word:
                st.success("✅ 拼写正确！")
            
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("⏮️ 上一个", key=f"prev_{idx}") and idx > 0:
                    st.session_state.trans_current_word_idx -= 1
                    st.rerun()
            with c2:
                if st.button("⏭️ 下一个", key=f"next_{idx}"):
                    st.session_state.trans_current_word_idx += 1
                    st.rerun()
            with c3:
                if st.button("⏹️ 结束", key=f"end_{idx}"):
                    st.session_state.trans_practice_active = False
                    st.session_state.trans_word_list = []
                    st.rerun()
        else:
            st.success("🎉 所有生词已过一遍！")
            if st.button("完成背诵"):
                st.session_state.trans_practice_active = False
                st.session_state.trans_word_list = []
                st.rerun()

# ==================== 标签页6：导入单词 ====================
with tabs[5]:
    st.header("📥 导入Excel词库")
    st.markdown("列名：word, meaning, pos, phonetic, memory_tip, example, note, difficulty, tags")
    up = st.file_uploader("选择.xlsx", type=["xlsx"])
    if up:
        try:
            df = pd.read_excel(up)
            required = ["word", "meaning"]
            for col in required:
                if col not in df.columns:
                    st.error(f"缺少列：{col}")
                    st.stop()
            df = df.fillna("")
            for col in ["pos", "phonetic", "memory_tip", "example", "note", "tags"]:
                if col not in df.columns:
                    df[col] = ""
            if "difficulty" not in df.columns:
                df["difficulty"] = 3
            
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
                        "word": w, "meaning": str(row["meaning"]), "pos": str(row.get("pos","")),
                        "phonetic": str(row.get("phonetic","")), "memory_tip": str(row.get("memory_tip","")),
                        "example": str(row.get("example","")), "note": str(row.get("note","")),
                        "difficulty": int(row.get("difficulty",3)), "tags": str(row.get("tags",""))
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
        st.dataframe(df_words[["word","meaning","pos","difficulty","tags"]])
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
    st.markdown(f"- 错题本单词数：{len(mistake_dict)}")
    st.markdown(f"- 连续打卡：{data['user_stats']['streak']} 天")
    st.markdown(f"- 总学习天数：{data['user_stats']['total_days']} 天")
    st.markdown(f"- 翻译题库：{len(st.session_state.trans_bank)} 题")
    if words:
        total_reviews = sum(p["repetitions"] for p in data["progress"].values())
        st.markdown(f"- 累计复习次数：{total_reviews}")
