"""
任务颜色管理模块 - 统一管理任务高亮颜色和状态颜色

提供现代化的配色方案，支持：
- 状态颜色：已完成、进行中、已取消、未开始
- 日期紧迫性颜色：已过期、今日到期、3天内、7天内、正常
"""

from PySide6.QtGui import QColor
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional


class DateUrgency(Enum):
    """日期紧迫性级别"""
    OVERDUE = "overdue"        # 已过期
    TODAY = "today"            # 今日到期（最紧急）
    WITHIN_3_DAYS = "within_3_days"  # 3天内（较紧急）
    WITHIN_7_DAYS = "within_7_days"  # 7天内（一般紧急）
    NORMAL = "normal"          # 正常
    LONG_TERM = "long_term"    # 长期任务
    NO_DEADLINE = "no_deadline"  # 无固定期限


class TaskColorManager:
    """
    任务颜色管理类
    
    使用现代化的配色方案，颜色更加柔和舒适
    """
    
    # ==================== 状态颜色（柔和现代） ====================
    # 已完成 - 柔和的薄荷绿
    STATUS_COMPLETED = QColor("#BBF7D0")  # 更柔和的绿色
    STATUS_COMPLETED_TEXT = QColor("#15803D")  # 深绿色文字
    
    # 进行中 - 柔和的琥珀/黄色（统一使用此颜色）
    STATUS_IN_PROGRESS = QColor("#FEF08A")  # 柔和的黄色
    STATUS_IN_PROGRESS_TEXT = QColor("#A16207")  # 深黄色文字
    
    # 已取消 - 柔和的中性灰色
    STATUS_CANCELLED = QColor("#E5E7EB")  # 浅灰色
    STATUS_CANCELLED_TEXT = QColor("#4B5563")  # 深灰色文字
    
    # 未开始 - 很浅的蓝色（更淡）
    STATUS_NOT_STARTED = QColor("#DBEAFE")  # 很浅的蓝色
    STATUS_NOT_STARTED_TEXT = QColor("#2563EB")  # 蓝色文字
    
    # ==================== 日期紧迫性颜色（红色系分层） ====================
    # 已过期 - 中等红色（醒目度中下，已过期但已不是当天）
    DATE_OVERDUE = QColor("#FECACA")  # 浅红偏粉
    DATE_OVERDUE_TEXT = QColor("#B91C1C")  # 深红色文字
    
    # 今日到期 - 最深最醒目的红色（最紧急）
    DATE_TODAY = QColor("#EF4444")  # 鲜红色
    DATE_TODAY_TEXT = QColor("#FFFFFF")  # 白色文字（对比度最高）
    
    # 3天内到期 - 较深的红色（醒目度中上）
    DATE_WITHIN_3_DAYS = QColor("#FCA5A5")  # 中等红色
    DATE_WITHIN_3_DAYS_TEXT = QColor("#991B1B")  # 深红色文字
    
    # 7天内到期 - 很浅的粉色（醒目度较低，仅提示）
    DATE_WITHIN_7_DAYS = QColor("#FFE4E6")  # 很浅的粉红
    DATE_WITHIN_7_DAYS_TEXT = QColor("#BE123C")  # 玫红色文字
    
    # 正常 - 无特殊颜色
    DATE_NORMAL_BG = QColor("#FFFFFF")  # 白色背景
    DATE_NORMAL_TEXT = QColor("#374151")  # 正常文字色
    
    # 长期/无期限 - 柔和紫色
    DATE_LONG_TERM = QColor("#F3E8FF")  # 很浅的紫色
    DATE_LONG_TERM_TEXT = QColor("#7C3AED")  # 紫色文字
    
    @classmethod
    def get_status_color(cls, status: str) -> tuple[QColor, QColor]:
        """
        获取状态对应的背景色和文字色
        
        Args:
            status: 状态字符串
            
        Returns:
            tuple: (背景色, 文字色)
        """
        status_map = {
            "已完成": (cls.STATUS_COMPLETED, cls.STATUS_COMPLETED_TEXT),
            "进行中": (cls.STATUS_IN_PROGRESS, cls.STATUS_IN_PROGRESS_TEXT),
            "已取消": (cls.STATUS_CANCELLED, cls.STATUS_CANCELLED_TEXT),
            "未开始": (cls.STATUS_NOT_STARTED, cls.STATUS_NOT_STARTED_TEXT),
        }
        return status_map.get(status, (QColor("#FFFFFF"), QColor("#374151")))
    
    @classmethod
    def get_date_urgency(cls, due_date: str) -> DateUrgency:
        """
        判断日期的紧迫性级别
        
        Args:
            due_date: 日期字符串 (格式: yyyy-MM-dd 或特殊日期 1999-09-09, 1999-09-10)
            
        Returns:
            DateUrgency: 紧迫性级别
        """
        if not due_date:
            return DateUrgency.NORMAL
            
        # 处理特殊日期
        if due_date == "1999-09-09":
            return DateUrgency.NO_DEADLINE
        if due_date == "1999-09-10":
            return DateUrgency.LONG_TERM
            
        try:
            # 尝试解析日期
            if " " in due_date:
                date_obj = datetime.strptime(due_date, "%Y-%m-%d %H:%M")
            else:
                date_obj = datetime.strptime(due_date, "%Y-%m-%d")
        except ValueError:
            return DateUrgency.NORMAL
            
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        date_obj = date_obj.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 计算天数差
        days_diff = (date_obj - today).days
        
        if days_diff < 0:
            return DateUrgency.OVERDUE
        elif days_diff == 0:
            return DateUrgency.TODAY
        elif days_diff <= 3:
            return DateUrgency.WITHIN_3_DAYS
        elif days_diff <= 7:
            return DateUrgency.WITHIN_7_DAYS
        else:
            return DateUrgency.NORMAL
    
    @classmethod
    def get_date_urgency_color(cls, urgency: DateUrgency) -> tuple[QColor, QColor]:
        """
        获取日期紧迫性对应的颜色
        
        Args:
            urgency: 紧迫性级别
            
        Returns:
            tuple: (背景色, 文字色)
        """
        color_map = {
            DateUrgency.OVERDUE: (cls.DATE_OVERDUE, cls.DATE_OVERDUE_TEXT),
            DateUrgency.TODAY: (cls.DATE_TODAY, cls.DATE_TODAY_TEXT),
            DateUrgency.WITHIN_3_DAYS: (cls.DATE_WITHIN_3_DAYS, cls.DATE_WITHIN_3_DAYS_TEXT),
            DateUrgency.WITHIN_7_DAYS: (cls.DATE_WITHIN_7_DAYS, cls.DATE_WITHIN_7_DAYS_TEXT),
            DateUrgency.NORMAL: (cls.DATE_NORMAL_BG, cls.DATE_NORMAL_TEXT),
            DateUrgency.LONG_TERM: (cls.DATE_LONG_TERM, cls.DATE_LONG_TERM_TEXT),
            DateUrgency.NO_DEADLINE: (cls.DATE_LONG_TERM, cls.DATE_LONG_TERM_TEXT),
        }
        return color_map.get(urgency, (cls.DATE_NORMAL_BG, cls.DATE_NORMAL_TEXT))
    
    @classmethod
    def get_date_color(cls, due_date: str) -> tuple[QColor, QColor]:
        """
        根据日期字符串获取颜色
        
        Args:
            due_date: 日期字符串
            
        Returns:
            tuple: (背景色, 文字色)
        """
        urgency = cls.get_date_urgency(due_date)
        return cls.get_date_urgency_color(urgency)
    
    @classmethod
    def get_urgency_display_text(cls, urgency: DateUrgency) -> str:
        """
        获取紧迫性的显示文本
        
        Args:
            urgency: 紧迫性级别
            
        Returns:
            str: 显示文本
        """
        text_map = {
            DateUrgency.OVERDUE: "⚠️ 已过期",
            DateUrgency.TODAY: "🔴 今日到期",
            DateUrgency.WITHIN_3_DAYS: "⏰ 3天内到期",
            DateUrgency.WITHIN_7_DAYS: "📅 7天内到期",
            DateUrgency.NORMAL: "",
            DateUrgency.LONG_TERM: "长期",
            DateUrgency.NO_DEADLINE: "无期限",
        }
        return text_map.get(urgency, "")
