from django import template
from datetime import datetime  # Это уже сам класс datetime

register = template.Library()


@register.filter
def months_ago(value):
    if isinstance(
        value, datetime
    ):  # Используем datetime напрямую, без повторного обращения
        now = datetime.now()  # naive datetime
        if value.tzinfo is not None:  # Если value aware — делаем naive
            value = value.replace(tzinfo=None)
        diff = now - value
        months = diff.days // 30
        return f"{months} месяц{'а' if months != 1 else ''} назад"
    return value
