"""
Пульсология — тренажёр пульсов и синдромов (Android-приложение).
Вопрос: описание пульса. Ответ: синдром + название пульса (порядок не важен).
Логика проверки — та же, что в телеграм-боте.
"""

import random
import re

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.core.window import Window
from kivy.utils import get_color_from_hex

from data import PULSES

# ---------- логика проверки ответа (идентична боту) ----------

STOPWORDS = {"или", "если", "из", "за", "на", "и", "по", "при", "что", "то", "в", "с",
             "синдром", "синдромы"}


def normalize(text):
    text = text.lower().replace("ё", "е")
    text = re.sub(r"[^a-zа-я0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _stem_match(a, b):
    if a == b:
        return True
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n >= 5


def _match_count(user_words, target_words):
    hits = 0
    for tw in target_words:
        if any(_stem_match(tw, uw) for uw in user_words):
            hits += 1
    return hits


def _pulse_words(pulse):
    return [w for w in normalize(pulse).split() if len(w) >= 2]


def _content_words(text):
    return [w for w in normalize(text).split()
            if len(w) >= 2 and w not in STOPWORDS]


def _syndrome_items(syndrome):
    items = []
    for part in re.split(r"[,;/()]", syndrome):
        for sub in re.split(r"\s+или\s+", part):
            ws = _content_words(sub)
            if ws:
                items.append(ws)
    return items


def check_answer(user_text, card):
    user_words = set(normalize(user_text).split())
    pulse_ok = _match_count(user_words, _pulse_words(card["pulse"])) > 0

    items = _syndrome_items(card["syndrome"])
    if items:
        all_words = [w for item in items for w in item]
        total_hits = _match_count(user_words, all_words)
        total_frac = total_hits / len(all_words)

        covered = 0
        full_long_item = False
        for item in items:
            hits = _match_count(user_words, item)
            need = len(item) if len(item) < 3 else max(2, round(len(item) * 0.75))
            if hits >= need:
                covered += 1
            if len(item) >= 3 and hits / len(item) >= 0.75:
                full_long_item = True
        items_frac = covered / len(items)

        syndrome_ok = total_frac >= 0.6 or items_frac >= 0.5 or full_long_item
        syndrome_frac = max(total_frac, items_frac)
    else:
        syndrome_ok = False
        syndrome_frac = 0.0

    return {"pulse_ok": pulse_ok, "syndrome_ok": syndrome_ok,
            "syndrome_frac": syndrome_frac, "fully_ok": pulse_ok and syndrome_ok}


# ---------- интерфейс ----------

BG = get_color_from_hex("#1E2430")
CARD = get_color_from_hex("#2A3242")
TEXT = get_color_from_hex("#E8ECF4")
ACCENT = get_color_from_hex("#5B8DEF")
GOOD = get_color_from_hex("#3FB27F")
BAD = get_color_from_hex("#E05B5B")
WARN = get_color_from_hex("#E0A93F")


class QuizApp(App):

    def build(self):
        self.title = "Пульсология — тренажёр"
        Window.clearcolor = BG

        root = BoxLayout(orientation="vertical", padding="12dp", spacing="10dp")

        self.counter = Label(text="", size_hint_y=None, height="28dp",
                             color=(0.6, 0.65, 0.75, 1))
        root.add_widget(self.counter)

        q_scroll = ScrollView()
        self.question = Label(text="", color=TEXT, font_size="17sp",
                              valign="top", padding=("10dp", "10dp"),
                              size_hint_y=None)
        self.question.bind(width=lambda inst, w: inst.setter("text_size")(inst, (w, None)))
        self.question.bind(texture_size=lambda inst, ts: inst.setter("size")(inst, (inst.width, ts[1])))
        q_scroll.add_widget(self.question)
        root.add_widget(q_scroll)

        self.answer = TextInput(hint_text="Напиши синдром и название пульса",
                                multiline=False, size_hint_y=None, height="48dp",
                                background_color=CARD, foreground_color=TEXT,
                                hint_text_color=(0.5, 0.55, 0.65, 1),
                                cursor_color=ACCENT, padding=("10dp", "12dp"))
        self.answer.bind(on_text_validate=self.check)
        root.add_widget(self.answer)

        self.check_btn = Button(text="Проверить", size_hint_y=None, height="48dp",
                                background_color=ACCENT, background_normal="")
        self.check_btn.bind(on_release=self.check)
        root.add_widget(self.check_btn)

        r_scroll = ScrollView()
        self.result = Label(text="Прочитай описание выше и напиши ответ.",
                            color=TEXT, font_size="15sp", valign="top",
                            padding=("10dp", "10dp"), size_hint_y=None)
        self.result.bind(width=lambda inst, w: inst.setter("text_size")(inst, (w, None)))
        self.result.bind(texture_size=lambda inst, ts: inst.setter("size")(inst, (inst.width, ts[1])))
        r_scroll.add_widget(self.result)
        root.add_widget(r_scroll)

        self.next_btn = Button(text="Следующий вопрос ➜", size_hint_y=None, height="48dp",
                               background_color=CARD, background_normal="",
                               disabled=True)
        self.next_btn.bind(on_release=self.next_question)
        root.add_widget(self.next_btn)

        self.deck = []
        self.current = None
        self.answered = 0
        self.next_question()
        return root

    def next_question(self, *args):
        if not self.deck:
            self.deck = list(range(len(PULSES)))
            random.shuffle(self.deck)
        if len(self.deck) > 1 and self.deck[-1] == self.current:
            random.shuffle(self.deck)
        self.current = self.deck.pop()
        card = PULSES[self.current]

        self.counter.text = f"Пройдено: {self.answered}   ·   Осталось в колоде: {len(self.deck)}"
        self.question.text = f"📝 Описание пульса:\n{card['description']}"
        self.answer.text = ""
        self.answer.disabled = False
        self.check_btn.disabled = False
        self.next_btn.disabled = True
        self.result.text = "Напиши синдром и название пульса, затем нажми «Проверить»."
        self.answer.focus = True

    def check(self, *args):
        if self.check_btn.disabled:
            return
        card = PULSES[self.current]
        result = check_answer(self.answer.text, card)
        pct = round(result.get("syndrome_frac", 0) * 100)

        if result["fully_ok"]:
            verdict = "🎉 Верно!"
            color = GOOD
        elif result["syndrome_ok"] and not result["pulse_ok"]:
            verdict = "⚠️ Синдром верный, но название пульса не угадано."
            color = WARN
        elif result["pulse_ok"] and result.get("syndrome_frac", 0) > 0:
            verdict = f"⚠️ Пульс верный, синдром частично ({pct}%)."
            color = WARN
        elif result["pulse_ok"]:
            verdict = "⚠️ Название пульса верное, но синдром не тот."
            color = WARN
        else:
            verdict = "❌ Неверно."
            color = BAD

        self.answered += 1
        self.counter.text = f"Пройдено: {self.answered}   ·   Осталось в колоде: {len(self.deck)}"
        self.result.text = (f"{verdict}\n\n"
                            f"✅ Правильный ответ:\n"
                            f"▪️ Пульс: {card['pulse']}\n"
                            f"▪️ Синдром: {card['syndrome']}\n"
                            f"▪️ Описание: {card['description']}")
        self.result.color = color
        self.answer.disabled = True
        self.check_btn.disabled = True
        self.next_btn.disabled = False


if __name__ == "__main__":
    QuizApp().run()
