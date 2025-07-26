# utils/text_processor.py
import re
import uuid
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

        # Regex for aggressive character cleaning. Whitelists common characters.
        self.aggressive_clean_re = re.compile(r"[^a-zA-Z0-9\s'\",.?!-]")

        # Define patterns for spelled-out numbers from one to ninety-nine
        units = ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
        teens = ["ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
        tens = ["twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
        tens_pattern = "|".join(tens)
        units_pattern = "|".join(units)
        compound_pattern = f"(?:{tens_pattern})(?:[\\s-]?(?:{units_pattern}))?"
        number_words_pattern = f"(?:{compound_pattern}|{'|'.join(teens)}|{units_pattern})"

        self.chapter_regex = re.compile(
            rf'^\s*(chapter\s+([ivxlcdm]+|\d+|{number_words_pattern})|prologue|epilogue)',
            re.IGNORECASE
        )

    def clean_text_aggressively(self, text: str) -> str:
        """Removes characters not in a basic whitelist."""
        return self.aggressive_clean_re.sub('', text)

    def filter_non_english_words(self, text: str) -> str:
        """
        Removes words containing characters not typical in English.
        This is a heuristic and may remove valid but unusual words/names.
        It preserves sentence-ending punctuation.
        """
        words = text.split(' ')
        # A word is kept if it's purely alphabetic, or contains apostrophes/hyphens surrounded by letters.
        valid_word_re = re.compile(r"^[a-zA-Z]+(?:['-]?[a-zA-Z]+)*$")
        
        filtered_words = []
        for word in words:
            # Preserve punctuation by stripping it before checking, then re-adding it.
            leading_punc = ''
            trailing_punc = ''
            
            # Find leading non-alphanumeric characters
            match_lead = re.match(r'^[^a-zA-Z]*', word)
            if match_lead:
                leading_punc = match_lead.group(0)
            
            # Find trailing non-alphanumeric characters
            match_trail = re.search(r'[^a-zA-Z]*$', word)
            if match_trail:
                trailing_punc = match_trail.group(0)
                
            clean_word = word[len(leading_punc):len(word)-len(trailing_punc)]

            if valid_word_re.match(clean_word) or clean_word == '':
                filtered_words.append(word)
        
        return ' '.join(filtered_words)

    def group_sentences_into_chunks(self, sentences, max_chars=290):
        """Groups individual sentences into larger chunks for TTS processing."""
        chunks, current_chunk_items, current_chunk_text = [], [], ""
        
        def finalize_chunk(items):
            if not items: return None
            is_chapter = len(items) == 1 and items[0].get('is_chapter_heading', False)
            final_text = " ".join(item['original_sentence'] for item in items)
            
            return {
                "uuid": uuid.uuid4().hex,
                "original_sentence": final_text, 
                "paragraph": "no",
                "tts_generated": "no", 
                "marked": False,
                "is_chapter_heading": is_chapter
            }

        for sentence_data in sentences:
            sentence_text = sentence_data['original_sentence']

            if sentence_data.get('is_chapter_heading'):
                if current_chunk_items:
                    chunks.append(finalize_chunk(current_chunk_items))
                chunks.append(sentence_data)
                current_chunk_items, current_chunk_text = [], ""
                continue
            
            if len(sentence_text) >= max_chars:
                if current_chunk_items:
                    chunks.append(finalize_chunk(current_chunk_items))
                chunks.append(sentence_data)
                current_chunk_items, current_chunk_text = [], ""
                continue
            
            if len(current_chunk_text) + len(sentence_text) + (1 if current_chunk_text else 0) > max_chars:
                if current_chunk_items:
                    chunks.append(finalize_chunk(current_chunk_items))
                current_chunk_items = [sentence_data]
                current_chunk_text = sentence_text
            else:
                current_chunk_items.append(sentence_data)
                current_chunk_text += (" " if current_chunk_text else "") + sentence_text
        
        if current_chunk_items:
            chunks.append(finalize_chunk(current_chunk_items))
            
        for i, chunk in enumerate(chunks):
            chunk['sentence_number'] = str(i + 1)
        
        return chunks

    def preprocess_text(self, text, is_edited_text=False, aggressive_clean=False):
        """Splits raw text into sentences and identifies paragraph breaks."""
        if aggressive_clean:
            text = self.clean_text_aggressively(text)
        
        text = re.sub(r'\r\n?', '\n', text)
        text = re.sub(r'\t', ' ', text)

        if is_edited_text:
            paragraph_break_positions = {m.start() for m in re.finditer(r'\n', text)}
        else:
            text_with_marker = re.sub(r'\n{2,}', '[[PARAGRAPH]]', text)
            paragraph_break_positions = {m.start() for m in re.finditer(r'\[\[PARAGRAPH\]\]', text_with_marker)}
            text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)
            text = text.replace('[[PARAGRAPH]]', '\n')

        sentences = self.splitter.split(text)
        processed_sentences = []
        char_offset = 0
        
        for i, sentence_text in enumerate(sentences):
            clean_sentence = sentence_text.strip()
            if not clean_sentence:
                char_offset += len(sentence_text)
                continue

            is_chapter_heading = bool(self.chapter_regex.match(clean_sentence))

            try:
                sentence_start_pos = text.index(sentence_text, char_offset)
                is_paragraph = any(p_pos >= sentence_start_pos and p_pos < (sentence_start_pos + len(sentence_text)) for p_pos in paragraph_break_positions)
                char_offset = sentence_start_pos + len(sentence_text)
            except ValueError:
                is_paragraph = False
                char_offset += len(sentence_text)

            processed_sentences.append({
                "uuid": uuid.uuid4().hex,
                "sentence_number": str(i + 1), "original_sentence": clean_sentence,
                "paragraph": "yes" if is_paragraph else "no", "tts_generated": "no", "marked": False,
                "is_chapter_heading": is_chapter_heading
            })
            
        return processed_sentences
