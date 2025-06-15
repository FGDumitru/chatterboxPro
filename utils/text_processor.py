# utils/text_processor.py
import re
from sentence_splitter import SentenceSplitter

def punc_norm(text: str) -> str:
    """Quick cleanup func for punctuation from LLMs or containing chars not seen often in the dataset."""
    if not text:
        return "You need to add some text for me to talk."

    # Capitalise first letter
    if text and text[0].islower():
        text = text[0].upper() + text[1:]

    # Remove multiple space chars
    text = " ".join(text.split())

    # Replace uncommon/llm punc
    punc_to_replace = [
        ("...", ", "), ("…", ", "), (":", ","), (" - ", ", "), (";", ", "),
        ("—", "-"), ("–", "-"), (" ,", ","), ("“", "\""), ("”", "\""),
        ("‘", "'"), ("’", "'"),
    ]
    for old_char_sequence, new_char in punc_to_replace:
        text = text.replace(old_char_sequence, new_char)

    # Add full stop if no ending punc
    text = text.rstrip()
    sentence_enders = {".", "!", "?", "-", ","}
    if text and not any(text.endswith(p) for p in sentence_enders):
        text += "."

    return text

class TextPreprocessor:
    """Handles all text extraction and splitting logic."""
    def __init__(self):
        self.splitter = SentenceSplitter(language='en')
        # NEW FEATURE: Regex to identify chapter headings
        self.chapter_regex = re.compile(r'^\s*(chapter\s+\d+|prologue|epilogue)\s*$', re.IGNORECASE)

    def group_sentences_into_chunks(self, sentences, max_chars=350):
        """Groups individual sentences into larger chunks for TTS processing."""
        chunks, current_chunk, is_first_in_chunk = [], "", True
        for sentence_data in sentences:
            sentence = sentence_data['original_sentence']
            # NEW FEATURE: Don't group chapter headings with other sentences
            if sentence_data.get('is_chapter_heading'):
                if current_chunk:
                    chunks.append(current_chunk.strip())
                chunks.append(sentence)
                current_chunk, is_first_in_chunk = "", True
                continue

            if len(sentence) >= max_chars:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                chunks.append(sentence)
                current_chunk, is_first_in_chunk = "", True
                continue

            if len(current_chunk) + len(sentence) + (0 if is_first_in_chunk else 1) > max_chars:
                chunks.append(current_chunk.strip())
                current_chunk, is_first_in_chunk = sentence, False
            else:
                if not is_first_in_chunk:
                    current_chunk += " "
                current_chunk += sentence
                is_first_in_chunk = False

        if current_chunk:
            chunks.append(current_chunk.strip())

        return [{"sentence_number": str(i + 1), "original_sentence": chunk_text, "paragraph": "no", "tts_generated": "no", "marked": False} for i, chunk_text in enumerate(chunks)]

    def preprocess_text(self, text, is_edited_text=False):
        """Splits raw text into sentences and identifies paragraph breaks."""
        text = re.sub(r'\r\n?', '\n', text)
        text = re.sub(r'\t', ' ', text)

        if is_edited_text:
            paragraph_breaks = list(re.finditer(r'\n', text))
        else:
            text = re.sub(r'\n{2,}', '[[PARAGRAPH]]', text)
            text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)
            text = text.replace('[[PARAGRAPH]]', '\n')
            paragraph_breaks = list(re.finditer(r'\n', text))

        sentences = self.splitter.split(text)
        processed_sentences, char_offset = [], 0
        for i, sentence_text in enumerate(sentences):
            if not sentence_text.strip():
                char_offset += len(sentence_text)
                continue

            is_chapter_heading = bool(self.chapter_regex.match(sentence_text.strip()))

            try:
                sentence_start = text.index(sentence_text, char_offset)
                sentence_end = sentence_start + len(sentence_text)
                is_paragraph = any(match.start() >= sentence_start and match.start() <= sentence_end for match in paragraph_breaks)
                char_offset = sentence_end
            except ValueError:
                is_paragraph, char_offset = False, char_offset + len(sentence_text)

            processed_sentences.append({
                "sentence_number": str(i + 1), "original_sentence": sentence_text.strip(),
                "paragraph": "yes" if is_paragraph else "no", "tts_generated": "no", "marked": False,
                "is_chapter_heading": is_chapter_heading # NEW FEATURE
            })
        return processed_sentences