from django import template
from datetime import datetime

register = template.Library()

@register.filter
def format_date(value):
    if value:
        return value.strftime('%Y-%m-%d')
    return ''

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def format_date_with_day(value):
    if value:
        DAYS = ['월', '화', '수', '목', '금', '토', '일']
        day_name = DAYS[value.weekday()]  # weekday()는 0(월요일)부터 6(일요일)까지 반환
        return value.strftime(f'%y.%m.%d({day_name})')  # %Y가 아닌 %y를 사용하여 연도를 2자리로 표시
    return ''