from django import template
from datetime import datetime

register = template.Library()

@register.filter
def format_date_with_day(value):
    if not value:
        return ''
    
    DAYS = {
        'Mon': '월',
        'Tue': '화',
        'Wed': '수',
        'Thu': '목',
        'Fri': '금',
        'Sat': '토',
        'Sun': '일'
    }
    
    date_str = value.strftime('%Y-%m-%d')
    day = DAYS[value.strftime('%a')]
    return f"{date_str}({day})"  # '요일'을 제거하고 한글 요일만 표시