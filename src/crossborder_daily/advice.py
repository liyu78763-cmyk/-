from __future__ import annotations

from collections.abc import Sequence

from crossborder_daily.models import AdviceType, Category, NewsItem


def advice_type_for_item(item: NewsItem) -> AdviceType:
    text = _text(item)
    if item.category == Category.POLICY_COMPLIANCE:
        return AdviceType.COMPLIANCE
    if item.category == Category.ADS_TRAFFIC:
        return AdviceType.ADS
    if item.category == Category.LOGISTICS:
        if any(keyword in text for keyword in ["fee", "surcharge", "cost", "tariff"]):
            return AdviceType.COST
        return AdviceType.LOGISTICS
    if any(keyword in text for keyword in ["fee", "tariff", "surcharge", "cost"]):
        return AdviceType.COST
    if item.category == Category.MARKET_PLATFORM:
        return AdviceType.MARKET
    return AdviceType.OPERATIONS


def actions_for_item(item: NewsItem, *, action_priority: str) -> list[str]:
    text = _text(item)
    if item.category == Category.POLICY_COMPLIANCE:
        return [
            "核对在售 ASIN、类目和供应商资料是否落入公告涉及范围",
            "检查 Seller Central、监管机构原文和账户通知，避免只依据二手解读操作",
            "对可能受影响商品暂缓新增广告预算或补货，先完成合规确认",
        ][: _action_count(action_priority)]
    if item.category == Category.ADS_TRAFFIC:
        return [
            "检查相关广告产品、投放权限和活动设置是否出现新选项",
            "用小预算测试受影响广告活动，单独观察 CTR、CVR、ACOS 变化",
            "同步更新关键词、否定词和预算上限，避免自动化规则误放量",
        ][: _action_count(action_priority)]
    if item.category == Category.LOGISTICS:
        return [
            "复核未来 4 周 FBA 入库、在途货件和安全库存",
            "重新测算受费用、附加费或时效变化影响 SKU 的毛利和补货节奏",
            "对高风险线路准备备选承运商或海外仓方案",
        ][: _action_count(action_priority)]
    if any(keyword in text for keyword in ["fee", "tariff", "surcharge", "cost"]):
        return [
            "重新计算受影响 SKU 的 landed cost、毛利率和盈亏平衡 ACOS",
            "评估是否需要调整售价、优惠券、广告预算或补货量",
            "保留政策原文和测算表，便于后续复盘成本变化",
        ][: _action_count(action_priority)]
    if item.category == Category.AMAZON_PLATFORM:
        return [
            "检查 Seller Central 公告、账户健康和 Listing 合规提醒",
            "核对相关 ASIN 的标题、图片、属性、变体和类目设置",
            "将本周新品上架和促销计划与公告要求重新对齐",
        ][: _action_count(action_priority)]
    return [
        "评估该变化是否影响目标类目、竞品价格或平台流量分配",
        "把相关平台政策页加入本周复查清单",
        "暂不做不可逆调整，等待官方或更权威来源的新增信息",
    ][: _action_count(action_priority)]


def checklist_for_items(items: Sequence[object]) -> tuple[str, str, str]:
    if not items:
        return (
            "今日暂无需要立即处理的重大行业变化，建议按正常节奏持续关注平台及监管机构通知。",
            "复查 Seller Central 账户通知、广告预算和 FBA 在途货件。",
            "持续跟踪 Amazon、监管机构和物流承运商官方公告。",
        )
    immediate = "检查是否存在 P0/P1 新闻涉及的 ASIN、广告活动、FBA 货件或合规资料。"
    weekly = "本周完成受影响 SKU 的成本、库存、广告预算和 Listing 合规复核。"
    observe = "继续跟踪官方原文、政策生效日期、承运商服务变化和竞争平台后续公告。"
    return immediate, weekly, observe


def _action_count(action_priority: str) -> int:
    if action_priority == "P0":
        return 3
    if action_priority == "P1":
        return 2
    return 1


def _text(item: NewsItem) -> str:
    return f"{item.title} {item.summary} {item.content}".lower()
