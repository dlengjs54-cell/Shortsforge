"""
일일 주제 자동 생성기
- Claude로 매일 새로운 쇼츠 주제 생성
- 중복 방지 (이전 주제 이력 참조)
- 주제 뱅크(topic_bank.json)에 축적
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import anthropic
from core.config_loader import Config


TOPIC_BANK_FILE = "topic_bank.json"

# 주제 카테고리 (리키항공 도메인에 최적화)
CATEGORIES = {
    "해외출장": [
        "출장 준비", "공항 이용", "호텔/숙소", "현지 교통",
        "비용 절약", "업무 효율", "안전/보험", "귀국 정산",
    ],
    "해외박람회": [
        "박람회 준비", "부스 운영", "네트워킹", "현지 마케팅",
        "통역/언어", "물류/샘플", "사후 관리", "박람회 선정",
    ],
    "기업연수": [
        "연수 기획", "예산 관리", "항공/숙소", "현지 프로그램",
        "단체 관리", "안전 관리", "성과 보고", "연수지 추천",
    ],
}

PROMPT_TEMPLATE = """당신은 해외출장/해외박람회/기업연수 전문 콘텐츠 기획자입니다.
유튜브 쇼츠(60초)에 적합한 주제를 {count}개 생성하세요.

[조건]
- 타겟: 해외출장을 보내는 기업 담당자, 관공서 공무원
- 톤: 실전에서 바로 쓸 수 있는 구체적 꿀팁
- 형식: "~하는 법", "~꿀팁 N가지", "~실수 N가지" 등 클릭 유도형
- 카테고리: {category} > {subcategory}
- 시의성: {season_hint}

[중복 금지 - 아래 주제는 이미 사용됨]
{used_topics}

[출력 형식 - JSON만 출력]
{{
  "topics": [
    {{"topic": "주제 텍스트", "category": "{category}", "subcategory": "{subcategory}", "hook_idea": "후킹 아이디어 한줄"}},
    ...
  ]
}}

JSON 외에 다른 텍스트는 절대 출력하지 마세요.
"""


class TopicGenerator:
    """일일 주제 자동 생성"""

    def __init__(self, config: Config):
        self.config = config
        self.bank_path = config.output_dir / TOPIC_BANK_FILE
        self._bank = self._load_bank()

        api_key = config.get_api_key("ANTHROPIC_API_KEY")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model_name = config.get("script", "model", default="claude-sonnet-4-20250514")

    # ── 주제 생성 ──

    def generate_daily(self, count: int = 3) -> list[dict]:
        """
        오늘의 주제 N개 생성
        카테고리를 순환하며 고르게 분배
        """
        print(f"🎯 일일 주제 {count}개 생성 중...")

        # 카테고리 순환 선택
        cat, subcat = self._pick_category()
        season = self._get_season_hint()
        used = self._get_used_topics(limit=50)

        prompt = PROMPT_TEMPLATE.format(
            count=count,
            category=cat,
            subcategory=subcat,
            season_hint=season,
            used_topics="\n".join(f"- {t}" for t in used) if used else "(없음)",
        )

        response = self.client.messages.create(
            model=self.model_name,
            max_tokens=1024,
            temperature=0.9,
            messages=[{"role": "user", "content": prompt}],
        )
        result_text = response.content[0].text
        # JSON 파싱 (마크다운 코드블록 제거)
        clean = result_text.strip()
        if clean.startswith("```"):
            lines = clean.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            clean = "\n".join(lines)
        data = json.loads(clean)
        topics = data.get("topics", [])

        # 뱅크에 저장
        today = datetime.now().strftime("%Y-%m-%d")
        for t in topics:
            t["generated_date"] = today
            t["status"] = "pending"  # pending → used → skipped
            self._bank["topics"].append(t)

        self._save_bank()
        print(f"   ✅ {len(topics)}개 주제 생성 완료 [{cat} > {subcat}]")

        for i, t in enumerate(topics, 1):
            print(f"   {i}. {t['topic']}")
            print(f"      💡 {t.get('hook_idea', '')}")

        return topics

    def get_next_topics(self, count: int = 1) -> list[dict]:
        """다음에 사용할 주제 N개 (pending 상태에서)"""
        pending = [t for t in self._bank["topics"] if t.get("status") == "pending"]

        if len(pending) < count:
            print(f"⚠️  대기 주제 부족 ({len(pending)}개). 새로 생성합니다...")
            self.generate_daily(count=max(count, 3))
            pending = [t for t in self._bank["topics"] if t.get("status") == "pending"]

        return pending[:count]

    def mark_used(self, topic_text: str):
        """주제를 사용 완료로 표시"""
        for t in self._bank["topics"]:
            if t["topic"] == topic_text:
                t["status"] = "used"
                t["used_date"] = datetime.now().strftime("%Y-%m-%d")
                break
        self._save_bank()

    def mark_skipped(self, topic_text: str):
        """주제를 건너뜀으로 표시"""
        for t in self._bank["topics"]:
            if t["topic"] == topic_text:
                t["status"] = "skipped"
                break
        self._save_bank()

    # ── 주제 뱅크 관리 ──

    def get_bank_summary(self) -> dict:
        """주제 뱅크 요약"""
        topics = self._bank["topics"]
        return {
            "total": len(topics),
            "pending": len([t for t in topics if t.get("status") == "pending"]),
            "used": len([t for t in topics if t.get("status") == "used"]),
            "skipped": len([t for t in topics if t.get("status") == "skipped"]),
            "categories": self._count_categories(),
        }

    def get_pending_topics(self) -> list[dict]:
        """대기 중인 전체 주제 목록"""
        return [t for t in self._bank["topics"] if t.get("status") == "pending"]

    def add_manual_topic(self, topic: str, category: str = "해외출장", subcategory: str = "기타"):
        """수동 주제 추가"""
        self._bank["topics"].append({
            "topic": topic,
            "category": category,
            "subcategory": subcategory,
            "hook_idea": "",
            "generated_date": datetime.now().strftime("%Y-%m-%d"),
            "status": "pending",
            "source": "manual",
        })
        self._save_bank()

    # ── 내부 로직 ──

    def _pick_category(self) -> tuple[str, str]:
        """카테고리 순환 선택 (덜 사용된 쪽 우선)"""
        cat_counts = self._count_categories()

        # 가장 적게 생성된 카테고리
        min_cat = min(CATEGORIES.keys(), key=lambda c: cat_counts.get(c, 0))

        # 해당 카테고리의 서브카테고리 중 덜 사용된 것
        import random
        subcats = CATEGORIES[min_cat]
        subcat = random.choice(subcats)

        return min_cat, subcat

    def _count_categories(self) -> dict:
        counts = {}
        for t in self._bank["topics"]:
            cat = t.get("category", "기타")
            counts[cat] = counts.get(cat, 0) + 1
        return counts

    def _get_used_topics(self, limit: int = 50) -> list[str]:
        """이미 사용된 주제 텍스트 목록"""
        used = [t["topic"] for t in self._bank["topics"] if t.get("status") in ("used", "pending")]
        return used[-limit:]

    def _get_season_hint(self) -> str:
        """시의성 힌트 생성"""
        now = datetime.now()
        month = now.month

        hints = {
            1: "새해 출장 시즌, CES 박람회",
            2: "MWC 바르셀로나, 설 연휴 전후 출장",
            3: "1분기 마감 출장, 봄 박람회 시즌 시작",
            4: "상반기 박람회 본격화, 벚꽃 시즌 연수",
            5: "해외 전시회 성수기, 초여름 연수",
            6: "상반기 마감 출장, 여름 연수 기획",
            7: "하반기 출장 준비, 여름 휴가 겸 출장",
            8: "가을 박람회 준비, IFA 베를린",
            9: "가을 박람회 시즌, 추석 전후 출장",
            10: "하반기 박람회 절정, 기업 연수 성수기",
            11: "연말 출장, 예산 소진 시즌",
            12: "내년 출장 계획, 연말 정산 관련",
        }
        return hints.get(month, "일반 출장 시즌")

    def _load_bank(self) -> dict:
        if self.bank_path.exists():
            with open(self.bank_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"topics": [], "created_at": datetime.now().isoformat()}

    def _save_bank(self):
        self.bank_path.parent.mkdir(parents=True, exist_ok=True)
        self._bank["updated_at"] = datetime.now().isoformat()
        with open(self.bank_path, "w", encoding="utf-8") as f:
            json.dump(self._bank, f, ensure_ascii=False, indent=2)
