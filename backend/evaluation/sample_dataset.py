"""
A hand-labeled evaluation set for the `sentiment_analysis` task.

A targeted stress test rather than a benchmark: it mixes easy examples
(clear lexicon signal) with the phenomena bag-of-words models get wrong —
negation, sarcasm, mixed sentiment, very short text. Use the SST-2
validation split for headline accuracy numbers.
"""

from dataclasses import dataclass
from typing import List


@dataclass
class LabeledExample:
    text: str
    true_label: str


SENTIMENT_EVAL_SET: List[LabeledExample] = [
    # --- Clear positive ---
    LabeledExample("This product exceeded my expectations in every way.", "POSITIVE"),
    LabeledExample("Absolutely wonderful service, the staff were so friendly.", "POSITIVE"),
    LabeledExample("Best purchase I've made all year, highly recommend.", "POSITIVE"),
    LabeledExample("The build quality is excellent and it feels very solid.", "POSITIVE"),
    LabeledExample("Fast shipping and the item arrived in perfect condition.", "POSITIVE"),
    LabeledExample("I love how comfortable and lightweight this is.", "POSITIVE"),
    LabeledExample("Great value for the price, works exactly as described.", "POSITIVE"),
    LabeledExample("The support team was incredibly helpful and resolved it fast.", "POSITIVE"),
    LabeledExample("A genuinely delightful experience from start to finish.", "POSITIVE"),
    LabeledExample("This is hands down the best version they've released.", "POSITIVE"),
    # --- Clear negative ---
    LabeledExample("This is the worst customer service I have ever experienced.", "NEGATIVE"),
    LabeledExample("Completely broken on arrival, total waste of money.", "NEGATIVE"),
    LabeledExample("The app crashed every single time I tried to use it.", "NEGATIVE"),
    LabeledExample("Cheap materials and it fell apart within a week.", "NEGATIVE"),
    LabeledExample("Extremely disappointing, nothing like the description.", "NEGATIVE"),
    LabeledExample("I regret this purchase and want a refund immediately.", "NEGATIVE"),
    LabeledExample("Rude staff and a confusing, frustrating checkout process.", "NEGATIVE"),
    LabeledExample("The battery life is awful, barely lasts two hours.", "NEGATIVE"),
    LabeledExample("Overpriced for what is fundamentally a flimsy product.", "NEGATIVE"),
    LabeledExample("Avoid this at all costs, it is simply not reliable.", "NEGATIVE"),
    # --- Negation: flips a positive word negative ---
    LabeledExample("This was not a good experience at all.", "NEGATIVE"),
    LabeledExample("Honestly, it is not great and I wouldn't buy it again.", "NEGATIVE"),
    LabeledExample("The service was not impressive given the price we paid.", "NEGATIVE"),
    LabeledExample("It's not comfortable and definitely not worth it.", "NEGATIVE"),
    LabeledExample("I can't say this was a pleasant experience.", "NEGATIVE"),
    # --- Negation: flips a negative word positive ---
    LabeledExample("It's never disappointing, every order has been great.", "POSITIVE"),
    LabeledExample("Not bad at all — actually pretty impressive for the price.", "POSITIVE"),
    LabeledExample("This never crashed once during the entire trip.", "POSITIVE"),
    LabeledExample("I wasn't disappointed, it worked better than expected.", "POSITIVE"),
    LabeledExample("Nothing about this felt cheap or unreliable.", "POSITIVE"),
    # --- Sarcasm / mixed signal — genuinely hard for a bag-of-words model ---
    LabeledExample("Oh great, another update that broke the app completely.", "NEGATIVE"),
    LabeledExample("Wonderful, my order arrived a month late and damaged.", "NEGATIVE"),
    LabeledExample("Love how it stopped working after just two days. Fantastic.", "NEGATIVE"),
    LabeledExample("Sure, 'excellent' service — three hours on hold and no answer.", "NEGATIVE"),
    LabeledExample("Great, the one time I need support, no one responds. Perfect.", "NEGATIVE"),
    LabeledExample("The design is beautiful but it broke after one use, so overall bad.", "NEGATIVE"),
    LabeledExample("Good packaging, terrible product — I'd still avoid buying this.", "NEGATIVE"),
    LabeledExample("It looks amazing but is so slow it's basically useless.", "NEGATIVE"),
    # --- Very short text ---
    LabeledExample("Works great!", "POSITIVE"),
    LabeledExample("Total junk.", "NEGATIVE"),
    LabeledExample("Loved it.", "POSITIVE"),
    LabeledExample("Never again.", "NEGATIVE"),
    LabeledExample("Solid buy.", "POSITIVE"),
    LabeledExample("Waste of money.", "NEGATIVE"),
    # --- Longer, mixed-but-net-clear text ---
    LabeledExample(
        "I was skeptical at first because of some mixed reviews, but after using it "
        "daily for three weeks I've been consistently impressed by how reliable and "
        "fast it is, and the customer support team was helpful when I had a question.",
        "POSITIVE",
    ),
    LabeledExample(
        "The initial setup was fine and the packaging looked nice, but within days "
        "the performance dropped off, it started overheating, and when I reached out "
        "for help I was met with a confusing automated system that never resolved "
        "anything, so overall I would not recommend this to anyone.",
        "NEGATIVE",
    ),
    LabeledExample(
        "It does what it says on the box, arrived on time, and the price was "
        "reasonable — nothing spectacular, but a genuinely solid, dependable "
        "purchase that I'm happy with.",
        "POSITIVE",
    ),
    LabeledExample(
        "Between the delayed shipping, the rude response from support, and the "
        "product arriving with visible damage, this has been an exhausting and "
        "frustrating ordeal that I would not wish on anyone else.",
        "NEGATIVE",
    ),
]
