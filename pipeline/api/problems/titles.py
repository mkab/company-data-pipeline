from http import HTTPStatus


def sentence_case(phrase: str) -> str:
    """Return the phrase in sentence case, keeping its first word and every acronym as they are.

    `"Not Found"` becomes `"Not found"`, and `"HTTP Version Not Supported"` becomes `"HTTP version not supported"`.
    """
    first_word, *other_words = phrase.split(" ")
    words = [first_word]
    for word in other_words:
        words.append(word if word.isupper() else word.lower())
    return " ".join(words)


def status_title(status: int) -> str:
    """Return the status phrase in sentence case, such as `"Not found"` for 404."""
    return sentence_case(HTTPStatus(status).phrase)
