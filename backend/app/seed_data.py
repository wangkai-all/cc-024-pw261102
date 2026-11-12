"""Deterministic demo dataset.

Every economic result in the application is reconstructed from
``contract_events``.  The contracts table only carries descriptive
attributes (plan name, initial terms); all MRR state lives in the event
stream.

Prepared scenarios (also indexed by ``SCENARIOS`` at the bottom of the file):

* C003 智造云      – scheduled cancellation: MRR only drops after the period
                     end; June-end snapshot still shows ``scheduled_cancel``.
* C004 观潮网络    – multiple contracts: the old contract ends on the same
                     day that a replacement starts, at customer level this is
                     an upgrade, never churn.
* C008 拾光教育    – two changes in one month, plus a fully offsetting
                     up/down pair in the following month.
* C002 / C013 / C029 – annual contracts; 100,000 / 12 produces a repeating
                     decimal, used to demonstrate the rounding tail.
* C005              – a trial month is ignored; the customer is new when the
                     contract converts to paid.
* C007 / C024       – pause and resume take effect on their effective dates.
* C018              – refund is a cash metric and does not change MRR.
"""

from __future__ import annotations

from datetime import date


CUSTOMERS = [
    {"customer_id": "C001", "name": "云帆科技", "city": "北京", "segment": "企业服务", "created_at": date(2025, 1, 5)},
    {"customer_id": "C002", "name": "星澜数据", "city": "上海", "segment": "数据服务", "created_at": date(2025, 2, 1)},
    {"customer_id": "C003", "name": "智造云", "city": "深圳", "segment": "工业软件", "created_at": date(2025, 1, 1)},
    {"customer_id": "C004", "name": "观潮网络", "city": "杭州", "segment": "营销科技", "created_at": date(2025, 3, 1)},
    {"customer_id": "C005", "name": "木棉生活", "city": "成都", "segment": "消费品牌", "created_at": date(2025, 1, 10)},
    {"customer_id": "C006", "name": "海珠传媒", "city": "广州", "segment": "传媒", "created_at": date(2025, 2, 1)},
    {"customer_id": "C007", "name": "极光软件", "city": "南京", "segment": "软件", "created_at": date(2025, 1, 20)},
    {"customer_id": "C008", "name": "拾光教育", "city": "武汉", "segment": "教育", "created_at": date(2025, 4, 1)},
    {"customer_id": "C009", "name": "蓝湖医疗", "city": "苏州", "segment": "医疗", "created_at": date(2025, 6, 1)},
    {"customer_id": "C010", "name": "北辰物流", "city": "天津", "segment": "物流", "created_at": date(2025, 5, 1)},
    {"customer_id": "C011", "name": "微光互动", "city": "西安", "segment": "游戏", "created_at": date(2025, 9, 1)},
    {"customer_id": "C012", "name": "青禾零售", "city": "重庆", "segment": "零售", "created_at": date(2025, 8, 1)},
    {"customer_id": "C013", "name": "山海文旅", "city": "厦门", "segment": "文旅", "created_at": date(2025, 11, 1)},
    {"customer_id": "C014", "name": "灵犀智能", "city": "青岛", "segment": "人工智能", "created_at": date(2026, 1, 5)},
    {"customer_id": "C015", "name": "松果设计", "city": "长沙", "segment": "设计", "created_at": date(2025, 3, 10)},
    {"customer_id": "C016", "name": "云梯基建", "city": "郑州", "segment": "建筑", "created_at": date(2025, 2, 15)},
    {"customer_id": "C017", "name": "远山农业", "city": "昆明", "segment": "农业", "created_at": date(2025, 5, 1)},
    {"customer_id": "C018", "name": "知行咨询", "city": "合肥", "segment": "咨询", "created_at": date(2025, 9, 15)},
    {"customer_id": "C019", "name": "星野游戏", "city": "福州", "segment": "游戏", "created_at": date(2026, 2, 1)},
    {"customer_id": "C020", "name": "拾贝金融", "city": "宁波", "segment": "金融", "created_at": date(2026, 4, 1)},
    {"customer_id": "C021", "name": "木星广告", "city": "无锡", "segment": "广告", "created_at": date(2025, 12, 1)},
    {"customer_id": "C022", "name": "花开母婴", "city": "南昌", "segment": "母婴", "created_at": date(2026, 5, 1)},
    {"customer_id": "C023", "name": "深蓝安全", "city": "东莞", "segment": "安全", "created_at": date(2025, 6, 15)},
    {"customer_id": "C024", "name": "驰远出行", "city": "佛山", "segment": "出行", "created_at": date(2025, 10, 1)},
    {"customer_id": "C025", "name": "云雀工具", "city": "珠海", "segment": "工具", "created_at": date(2026, 7, 1)},
    {"customer_id": "C026", "name": "山海教育", "city": "中山", "segment": "教育", "created_at": date(2025, 7, 1)},
    {"customer_id": "C027", "name": "一页文档", "city": "惠州", "segment": "文档", "created_at": date(2025, 2, 1)},
    {"customer_id": "C028", "name": "麦田影像", "city": "江门", "segment": "影像", "created_at": date(2026, 6, 1)},
    {"customer_id": "C029", "name": "数聚云", "city": "嘉兴", "segment": "数据服务", "created_at": date(2026, 2, 1)},
]


CONTRACTS = [
    {"contract_id": "CT001", "customer_id": "C001", "plan_name": "旗舰版", "billing_cycle": "monthly", "amount_rmb": 12800, "currency": "CNY", "signed_date": date(2025, 1, 5)},
    {"contract_id": "CT002", "customer_id": "C002", "plan_name": "企业版·年付", "billing_cycle": "annual", "amount_rmb": 100000, "currency": "CNY", "signed_date": date(2025, 2, 1)},
    {"contract_id": "CT003", "customer_id": "C003", "plan_name": "标准版", "billing_cycle": "monthly", "amount_rmb": 8000, "currency": "CNY", "signed_date": date(2025, 1, 1)},
    {"contract_id": "CT004A", "customer_id": "C004", "plan_name": "基础版", "billing_cycle": "monthly", "amount_rmb": 6000, "currency": "CNY", "signed_date": date(2025, 3, 1)},
    {"contract_id": "CT004B", "customer_id": "C004", "plan_name": "增值模块", "billing_cycle": "monthly", "amount_rmb": 4000, "currency": "CNY", "signed_date": date(2025, 10, 1)},
    {"contract_id": "CT004C", "customer_id": "C004", "plan_name": "旗舰版", "billing_cycle": "monthly", "amount_rmb": 12000, "currency": "CNY", "signed_date": date(2026, 4, 1)},
    {"contract_id": "CT005", "customer_id": "C005", "plan_name": "成长版", "billing_cycle": "monthly", "amount_rmb": 5000, "currency": "CNY", "signed_date": date(2025, 1, 10)},
    {"contract_id": "CT006", "customer_id": "C006", "plan_name": "标准版", "billing_cycle": "monthly", "amount_rmb": 7500, "currency": "CNY", "signed_date": date(2025, 2, 1)},
    {"contract_id": "CT006B", "customer_id": "C006", "plan_name": "成长版", "billing_cycle": "monthly", "amount_rmb": 9000, "currency": "CNY", "signed_date": date(2026, 5, 1)},
    {"contract_id": "CT007", "customer_id": "C007", "plan_name": "专业版", "billing_cycle": "monthly", "amount_rmb": 5500, "currency": "CNY", "signed_date": date(2025, 1, 20)},
    {"contract_id": "CT008", "customer_id": "C008", "plan_name": "标准版", "billing_cycle": "monthly", "amount_rmb": 6500, "currency": "CNY", "signed_date": date(2025, 4, 1)},
    {"contract_id": "CT009", "customer_id": "C009", "plan_name": "企业版·年付", "billing_cycle": "annual", "amount_rmb": 120000, "currency": "CNY", "signed_date": date(2025, 6, 1)},
    {"contract_id": "CT010", "customer_id": "C010", "plan_name": "专业版", "billing_cycle": "monthly", "amount_rmb": 11000, "currency": "CNY", "signed_date": date(2025, 5, 1)},
    {"contract_id": "CT011", "customer_id": "C011", "plan_name": "标准版", "billing_cycle": "monthly", "amount_rmb": 4500, "currency": "CNY", "signed_date": date(2025, 9, 1)},
    {"contract_id": "CT012", "customer_id": "C012", "plan_name": "基础版", "billing_cycle": "monthly", "amount_rmb": 3800, "currency": "CNY", "signed_date": date(2025, 8, 1)},
    {"contract_id": "CT013", "customer_id": "C013", "plan_name": "企业版·年付", "billing_cycle": "annual", "amount_rmb": 60000, "currency": "CNY", "signed_date": date(2025, 11, 1)},
    {"contract_id": "CT014", "customer_id": "C014", "plan_name": "专业版", "billing_cycle": "monthly", "amount_rmb": 9800, "currency": "CNY", "signed_date": date(2026, 1, 5)},
    {"contract_id": "CT015", "customer_id": "C015", "plan_name": "基础版", "billing_cycle": "monthly", "amount_rmb": 4200, "currency": "CNY", "signed_date": date(2025, 3, 10)},
    {"contract_id": "CT015B", "customer_id": "C015", "plan_name": "成长版", "billing_cycle": "monthly", "amount_rmb": 6000, "currency": "CNY", "signed_date": date(2025, 12, 1)},
    {"contract_id": "CT016A", "customer_id": "C016", "plan_name": "主合同", "billing_cycle": "monthly", "amount_rmb": 7000, "currency": "CNY", "signed_date": date(2025, 2, 15)},
    {"contract_id": "CT016B", "customer_id": "C016", "plan_name": "增值模块", "billing_cycle": "monthly", "amount_rmb": 3000, "currency": "CNY", "signed_date": date(2025, 7, 1)},
    {"contract_id": "CT017", "customer_id": "C017", "plan_name": "基础版·年付", "billing_cycle": "monthly", "amount_rmb": 2500, "currency": "CNY", "signed_date": date(2025, 5, 1)},
    {"contract_id": "CT018", "customer_id": "C018", "plan_name": "专业版", "billing_cycle": "monthly", "amount_rmb": 8000, "currency": "CNY", "signed_date": date(2025, 9, 15)},
    {"contract_id": "CT019", "customer_id": "C019", "plan_name": "旗舰版", "billing_cycle": "monthly", "amount_rmb": 15000, "currency": "CNY", "signed_date": date(2026, 2, 1)},
    {"contract_id": "CT020", "customer_id": "C020", "plan_name": "企业版·年付", "billing_cycle": "annual", "amount_rmb": 150000, "currency": "CNY", "signed_date": date(2026, 4, 1)},
    {"contract_id": "CT021", "customer_id": "C021", "plan_name": "标准版", "billing_cycle": "monthly", "amount_rmb": 6000, "currency": "CNY", "signed_date": date(2025, 12, 1)},
    {"contract_id": "CT022", "customer_id": "C022", "plan_name": "基础版", "billing_cycle": "monthly", "amount_rmb": 3500, "currency": "CNY", "signed_date": date(2026, 5, 1)},
    {"contract_id": "CT023", "customer_id": "C023", "plan_name": "专业版", "billing_cycle": "monthly", "amount_rmb": 10000, "currency": "CNY", "signed_date": date(2025, 6, 15)},
    {"contract_id": "CT024", "customer_id": "C024", "plan_name": "标准版", "billing_cycle": "monthly", "amount_rmb": 5000, "currency": "CNY", "signed_date": date(2025, 10, 1)},
    {"contract_id": "CT025", "customer_id": "C025", "plan_name": "标准版", "billing_cycle": "monthly", "amount_rmb": 6800, "currency": "CNY", "signed_date": date(2026, 7, 1)},
    {"contract_id": "CT026", "customer_id": "C026", "plan_name": "企业版·年付", "billing_cycle": "annual", "amount_rmb": 48000, "currency": "CNY", "signed_date": date(2025, 7, 1)},
    {"contract_id": "CT027", "customer_id": "C027", "plan_name": "基础版", "billing_cycle": "monthly", "amount_rmb": 4000, "currency": "CNY", "signed_date": date(2025, 2, 1)},
    {"contract_id": "CT027B", "customer_id": "C027", "plan_name": "成长版", "billing_cycle": "monthly", "amount_rmb": 6000, "currency": "CNY", "signed_date": date(2026, 3, 1)},
    {"contract_id": "CT028", "customer_id": "C028", "plan_name": "旗舰版", "billing_cycle": "monthly", "amount_rmb": 9000, "currency": "CNY", "signed_date": date(2026, 6, 1)},
    {"contract_id": "CT029", "customer_id": "C029", "plan_name": "企业版·年付", "billing_cycle": "annual", "amount_rmb": 100000, "currency": "CNY", "signed_date": date(2026, 2, 1)},
]


def _e(event_id, contract_id, customer_id, event_type, event_date, effective_date=None,
       amount_rmb=None, billing_cycle=None, note=""):
    return {
        "event_id": event_id,
        "contract_id": contract_id,
        "customer_id": customer_id,
        "event_type": event_type,
        "event_date": event_date,
        "effective_date": effective_date or event_date,
        "amount_rmb": amount_rmb,
        "billing_cycle": billing_cycle,
        "note": note,
    }


# Event order matters for same-day effects: an old contract is terminated
# before its replacement starts (C004, 2026-04-01).
CONTRACT_EVENTS = [
    _e("E001", "CT001", "C001", "paid_start", date(2025, 1, 5), amount_rmb=12800, billing_cycle="monthly"),
    _e("E002", "CT001", "C001", "plan_change", date(2025, 7, 1), amount_rmb=15800, billing_cycle="monthly", note="专业版升级至旗舰版"),
    _e("E003", "CT001", "C001", "plan_change", date(2026, 2, 1), amount_rmb=216000, billing_cycle="annual", note="转为年付，月化 MRR 18,000"),

    _e("E004", "CT002", "C002", "paid_start", date(2025, 2, 1), amount_rmb=100000, billing_cycle="annual", note="年付，100,000 ÷ 12"),

    _e("E005", "CT003", "C003", "paid_start", date(2025, 1, 1), amount_rmb=8000, billing_cycle="monthly"),
    _e("E006", "CT003", "C003", "cancel_scheduled", date(2026, 5, 20), effective_date=date(2026, 7, 1), note="预约到期取消；合同到期日 2026-06-30，7/1 起停止计费"),

    _e("E007", "CT004A", "C004", "paid_start", date(2025, 3, 1), amount_rmb=6000, billing_cycle="monthly"),
    _e("E008", "CT004B", "C004", "paid_start", date(2025, 10, 1), amount_rmb=4000, billing_cycle="monthly", note="增购增值模块"),
    _e("E009", "CT004A", "C004", "contract_end", date(2026, 4, 1), note="升级替换，旧合同在同日终止"),
    _e("E010", "CT004C", "C004", "paid_start", date(2026, 4, 1), amount_rmb=12000, billing_cycle="monthly", note="旗舰版替换合同，同日生效"),

    _e("E011", "CT005", "C005", "trial_start", date(2025, 1, 10), note="30 天试用，不计 MRR"),
    _e("E012", "CT005", "C005", "paid_start", date(2025, 2, 10), amount_rmb=5000, billing_cycle="monthly", note="试用转付费"),

    _e("E013", "CT006", "C006", "paid_start", date(2025, 2, 1), amount_rmb=7500, billing_cycle="monthly"),
    _e("E014", "CT006", "C006", "contract_end", date(2025, 9, 15), note="主动退订"),
    _e("E015", "CT006B", "C006", "paid_start", date(2026, 5, 1), amount_rmb=9000, billing_cycle="monthly", note="老客户回流续签"),

    _e("E016", "CT007", "C007", "paid_start", date(2025, 1, 20), amount_rmb=5500, billing_cycle="monthly"),
    _e("E017", "CT007", "C007", "pause", date(2025, 7, 1), note="暂停计费"),
    _e("E018", "CT007", "C007", "resume", date(2025, 9, 1), note="恢复计费"),

    _e("E019", "CT008", "C008", "paid_start", date(2025, 4, 1), amount_rmb=6500, billing_cycle="monthly"),
    _e("E020", "CT008", "C008", "plan_change", date(2025, 10, 5), amount_rmb=9000, billing_cycle="monthly", note="同月第一次升级"),
    _e("E021", "CT008", "C008", "plan_change", date(2025, 10, 20), amount_rmb=7000, billing_cycle="monthly", note="同月降级"),
    _e("E022", "CT008", "C008", "plan_change", date(2025, 11, 3), amount_rmb=10000, billing_cycle="monthly", note="月内升级"),
    _e("E023", "CT008", "C008", "plan_change", date(2025, 11, 18), amount_rmb=7000, billing_cycle="monthly", note="月内降回原档，净变化为零"),

    _e("E024", "CT009", "C009", "paid_start", date(2025, 6, 1), amount_rmb=120000, billing_cycle="annual"),
    _e("E025", "CT009", "C009", "cancel_scheduled", date(2026, 4, 15), effective_date=date(2026, 7, 1), note="年付到期不续约；到期日 2026-06-30"),

    _e("E026", "CT010", "C010", "paid_start", date(2025, 5, 1), amount_rmb=11000, billing_cycle="monthly"),
    _e("E027", "CT010", "C010", "plan_change", date(2026, 1, 1), amount_rmb=14000, billing_cycle="monthly", note="升级"),
    _e("E028", "CT010", "C010", "plan_change", date(2026, 6, 1), amount_rmb=9000, billing_cycle="monthly", note="降级"),

    _e("E029", "CT011", "C011", "trial_start", date(2025, 9, 1), note="试用，不计 MRR"),
    _e("E030", "CT011", "C011", "paid_start", date(2025, 10, 1), amount_rmb=4500, billing_cycle="monthly", note="试用转付费"),

    _e("E031", "CT012", "C012", "paid_start", date(2025, 8, 1), amount_rmb=3800, billing_cycle="monthly"),
    _e("E032", "CT012", "C012", "contract_end", date(2026, 3, 1), note="退订"),

    _e("E033", "CT013", "C013", "paid_start", date(2025, 11, 1), amount_rmb=60000, billing_cycle="annual"),
    _e("E034", "CT013", "C013", "plan_change", date(2026, 2, 1), amount_rmb=100000, billing_cycle="annual", note="年付升级，100,000 ÷ 12"),

    _e("E035", "CT014", "C014", "paid_start", date(2026, 1, 5), amount_rmb=9800, billing_cycle="monthly"),
    _e("E036", "CT014", "C014", "plan_change", date(2026, 7, 1), amount_rmb=12800, billing_cycle="monthly", note="升级"),

    _e("E037", "CT015", "C015", "paid_start", date(2025, 3, 10), amount_rmb=4200, billing_cycle="monthly"),
    _e("E038", "CT015", "C015", "contract_end", date(2025, 7, 1), note="退订"),
    _e("E039", "CT015B", "C015", "paid_start", date(2025, 12, 1), amount_rmb=6000, billing_cycle="monthly", note="老客户回流"),

    _e("E040", "CT016A", "C016", "paid_start", date(2025, 2, 15), amount_rmb=7000, billing_cycle="monthly"),
    _e("E041", "CT016B", "C016", "paid_start", date(2025, 7, 1), amount_rmb=3000, billing_cycle="monthly", note="增购模块"),
    _e("E042", "CT016B", "C016", "contract_end", date(2026, 2, 1), note="模块停用，主合同继续，因此客户不算流失"),

    _e("E043", "CT017", "C017", "paid_start", date(2025, 5, 1), amount_rmb=2500, billing_cycle="monthly"),
    _e("E044", "CT017", "C017", "plan_change", date(2026, 3, 1), amount_rmb=30000, billing_cycle="annual", note="转年付，月化 MRR 不变（2,500）"),

    _e("E045", "CT018", "C018", "paid_start", date(2025, 9, 15), amount_rmb=8000, billing_cycle="monthly"),
    _e("E046", "CT018", "C018", "refund", date(2025, 12, 10), amount_rmb=2000, note="服务补偿退款，仅计入现金指标"),

    _e("E047", "CT019", "C019", "paid_start", date(2026, 2, 1), amount_rmb=15000, billing_cycle="monthly"),
    _e("E048", "CT019", "C019", "refund", date(2026, 5, 15), amount_rmb=5000, note="退款，仅计入现金指标"),
    _e("E049", "CT019", "C019", "plan_change", date(2026, 6, 1), amount_rmb=11000, billing_cycle="monthly", note="降级"),

    _e("E050", "CT020", "C020", "paid_start", date(2026, 4, 1), amount_rmb=150000, billing_cycle="annual"),

    _e("E051", "CT021", "C021", "paid_start", date(2025, 12, 1), amount_rmb=6000, billing_cycle="monthly"),
    _e("E052", "CT021", "C021", "contract_end", date(2026, 9, 1), note="退订"),

    _e("E053", "CT022", "C022", "paid_start", date(2026, 5, 1), amount_rmb=3500, billing_cycle="monthly"),
    _e("E054", "CT022", "C022", "cancel_scheduled", date(2026, 8, 20), effective_date=date(2026, 10, 1), note="预约取消；到期日 2026-09-30"),

    _e("E055", "CT023", "C023", "paid_start", date(2025, 6, 15), amount_rmb=10000, billing_cycle="monthly"),
    _e("E056", "CT023", "C023", "plan_change", date(2026, 9, 1), amount_rmb=13000, billing_cycle="monthly", note="升级"),

    _e("E057", "CT024", "C024", "paid_start", date(2025, 10, 1), amount_rmb=5000, billing_cycle="monthly"),
    _e("E058", "CT024", "C024", "pause", date(2026, 3, 1), note="暂停计费"),
    _e("E059", "CT024", "C024", "resume", date(2026, 5, 1), note="恢复计费"),

    _e("E060", "CT025", "C025", "paid_start", date(2026, 7, 1), amount_rmb=6800, billing_cycle="monthly"),

    _e("E061", "CT026", "C026", "paid_start", date(2025, 7, 1), amount_rmb=48000, billing_cycle="annual"),
    _e("E062", "CT026", "C026", "plan_change", date(2026, 7, 1), amount_rmb=72000, billing_cycle="annual", note="年付升级"),

    _e("E063", "CT027", "C027", "paid_start", date(2025, 2, 1), amount_rmb=4000, billing_cycle="monthly"),
    _e("E064", "CT027", "C027", "contract_end", date(2025, 9, 1), note="退订"),
    _e("E065", "CT027B", "C027", "paid_start", date(2026, 3, 1), amount_rmb=6000, billing_cycle="monthly", note="老客户回流"),

    _e("E066", "CT028", "C028", "paid_start", date(2026, 6, 1), amount_rmb=9000, billing_cycle="monthly"),
    _e("E067", "CT028", "C028", "plan_change", date(2026, 10, 1), amount_rmb=6000, billing_cycle="monthly", note="降级"),

    _e("E068", "CT029", "C029", "paid_start", date(2026, 2, 1), amount_rmb=100000, billing_cycle="annual", note="年付，100,000 ÷ 12"),
    _e("E069", "CT025", "C025", "plan_change", date(2026, 8, 1), amount_rmb=8200, billing_cycle="monthly", note="使用量升级"),
]


SCENARIOS = [
    {
        "id": "scheduled-cancel",
        "title": "预约取消，到期才减少",
        "description": "C003 在 5 月预约取消；6 月末仍有 MRR 并标记为待到期，7 月才转为流失。",
        "month": "2026-06",
        "customer_id": "C003",
        "tag": "预约取消",
    },
    {
        "id": "same-month-changes",
        "title": "同月多次升降级",
        "description": "C008 在 2025-10 先升级再降级，桥接只记净 +500；11 月升级后又降回原档，净变化为零，进入事件流水。",
        "month": "2025-10",
        "customer_id": "C008",
        "tag": "同月变动",
    },
    {
        "id": "annual-and-rounding",
        "title": "年付与舍入尾差",
        "description": "C002 / C029 的 100,000 年付月化为 8,333.3333；2026-02 桥接显示金额出现 +0.01 尾差。",
        "month": "2026-02",
        "customer_id": "C029",
        "tag": "年付 / 尾差",
    },
    {
        "id": "multi-contract-upgrade",
        "title": "多合同升级不算流失",
        "description": "C004 的旧合同与替换合同同日生效/终止；客户层 10,000 → 16,000，记为升级 +6,000。",
        "month": "2026-04",
        "customer_id": "C004",
        "tag": "多合同",
    },
    {
        "id": "trial-conversion",
        "title": "试用不计 MRR",
        "description": "C005 在 1 月试用（MRR=0），2 月转付费，按首付月份 2025-02 计入新增。",
        "month": "2025-02",
        "customer_id": "C005",
        "tag": "试用",
    },
    {
        "id": "pause-resume",
        "title": "暂停与恢复按生效时间",
        "description": "C007 7 月暂停、9 月恢复；暂停和恢复作为独立桥接项，不误记为流失/回流。",
        "month": "2025-07",
        "customer_id": "C007",
        "tag": "暂停",
    },
    {
        "id": "reactivation",
        "title": "流失后回流",
        "description": "C027 2025-09 流失，2026-03 以新合同回流，桥接计入回流。",
        "month": "2026-03",
        "customer_id": "C027",
        "tag": "回流",
    },
    {
        "id": "refund-cash",
        "title": "退款只进现金指标",
        "description": "C018 2025-12 退款 2,000，MRR 仍为 8,000，退款单列且不修改合同 MRR。",
        "month": "2025-12",
        "customer_id": "C018",
        "tag": "退款",
    },
]
