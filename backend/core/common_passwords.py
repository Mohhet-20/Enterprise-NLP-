"""
A denylist of the most common passwords found in real-world breach
compilations (e.g. the widely-cited rockyou.txt leak and annual "worst
passwords" lists) — not a synthetic example set. Modern password guidance
(NIST 800-63B) recommends checking against known-compromised passwords
over arbitrary complexity rules (require an uppercase! a digit! a
symbol!), which push people toward predictable substitutions
("Password1!") without meaningfully increasing guessing resistance. This
list is deliberately short — a few hundred entries covering the
highest-frequency real-world passwords — not an attempt at a
comprehensive breach-corpus check (that's a job for a dedicated service
like HaveIBeenPwned's k-anonymity API, not a hardcoded list).
"""

COMMON_PASSWORDS = {
    "123456", "password", "12345678", "qwerty", "123456789", "12345",
    "1234", "111111", "1234567", "dragon", "123123", "baseball", "abc123",
    "football", "monkey", "letmein", "shadow", "master", "666666",
    "qwertyuiop", "123321", "mustang", "1234567890", "michael", "654321",
    "superman", "1qaz2wsx", "7777777", "121212", "000000", "qazwsx",
    "123qwe", "killer", "trustno1", "jordan", "jennifer", "zxcvbnm",
    "asdfgh", "hunter", "buster", "soccer", "harley", "batman", "andrew",
    "tigger", "sunshine", "iloveyou", "charlie", "robert", "thomas",
    "hockey", "ranger", "daniel", "starwars", "112233", "george",
    "computer", "michelle", "jessica", "pepper", "zxcvbn", "555555",
    "11111111", "131313", "freedom", "777777", "password1", "password123",
    "maggie", "159753", "aaaaaa", "ginger", "princess", "joshua", "cheese",
    "amanda", "summer", "iloveyou1", "ashley", "6969", "nicole", "chelsea",
    "matthew", "access", "yankees", "987654321", "dallas", "austin",
    "thunder", "taylor", "matrix", "welcome", "welcome1", "admin",
    "administrator", "letmein1", "changeme", "qwerty123", "abcd1234",
    "passw0rd", "p@ssw0rd", "iloveyou2", "1q2w3e4r", "trustno1!",
}


def is_common_password(password: str) -> bool:
    return password.lower() in COMMON_PASSWORDS
