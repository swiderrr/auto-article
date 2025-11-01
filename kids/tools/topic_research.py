#!/usr/bin/env python3
import json
import os

# High-traffic topics in parenting (based on SEO research)
POPULAR_TOPICS = {
    "Rozwój dziecka": [
        "Kiedy dziecko zaczyna chodzić?",
        "Kiedy dziecko powinno zacząć mówić?",
        "Kamienie milowe rozwoju dziecka w pierwszym roku",
        "Jak wspierać rozwój mowy u dziecka?",
        "Rozwój motoryczny niemowlaka - co i kiedy?",
    ],
    "Karmienie i dieta": [
        "Jak rozszerzać dietę niemowlaka krok po kroku?",
        "Co powinno jeść roczne dziecko?",
        "Przepisy na zdrowe posiłki dla niemowlaka",
        "Kiedy wprowadzać gluten i produkty alergizujące?",
        "BLW czy tradycyjne rozszerzanie diety - co wybrać?",
    ],
    "Zdrowie": [
        "Jak radzić sobie z gorączką u dziecka?",
        "Kalendarz szczepień - co warto wiedzieć?",
        "Pierwsza pomoc dla niemowląt i małych dzieci",
        "Jak wzmocnić odporność dziecka naturalnie?",
        "Najczęstsze choroby wieku dziecięcego - objawy",
    ],
    "Sen i rutyna": [
        "Jak nauczyć dziecko spać całą noc?",
        "Rutyna snu dla niemowlaka - przykładowy plan",
        "Metody zasypiania dla niemowląt",
        "Co zrobić gdy dziecko się nie wysypia?",
        "Drzemki niemowlaka - jak zaplanować?",
    ],
    "Bezpieczeństwo": [
        "Jak przygotować mieszkanie dla niemowlaka?",
        "Lista wyprawki dla noworodka - co jest niezbędne?",
        "Bezpieczne zabawki dla niemowlaka",
        "Pierwsza pomoc dla dzieci - co trzeba wiedzieć?",
        "Jak wybrać bezpieczne krzesełko do karmienia?",
    ]
}

def get_trending_topics():
    """Return a list of popular topics with SEO potential."""
    topics = []
    for category, category_topics in POPULAR_TOPICS.items():
        topics.extend(category_topics)
    return topics

def save_topics_file(topics_file):
    """Save researched topics to topics.txt."""
    topics = get_trending_topics()
    with open(topics_file, 'w', encoding='utf-8') as f:
        for topic in topics:
            f.write(topic + '\n')

if __name__ == "__main__":
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    topics_file = os.path.join(base, "topics.txt")
    save_topics_file(topics_file)
    print(f"Updated {topics_file} with trending topics")