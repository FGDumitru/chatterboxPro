# parse_and_chunk.py
# A dedicated script to process a source document and generate the session JSON file.
# This allows for easy inspection of the text chunking logic.

import os
import re
import json
import argparse
from pathlib import Path

# Required libraries from your project
from sentence_splitter import SentenceSplitter
from pdftextract import XPdf
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import pypandoc

# --- Re-usable TextPreprocessor Class ---
# This is the same class used in the main application for consistency.

class TextPreprocessor:
    def __init__(self):
        # We only need English for this standalone script.
        self.splitter = SentenceSplitter(language='en')

    def group_sentences_into_chunks(self, sentences, max_chars=300):
        """
        Groups sentences into chunks that are close to, but not exceeding,
        the max_chars limit.
        """
        chunks = []
        current_chunk = ""
        is_first_in_chunk = True

        for sentence_data in sentences:
            sentence = sentence_data['original_sentence']
            # If a single sentence is already too long, it becomes its own chunk
            if len(sentence) >= max_chars:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                chunks.append(sentence)
                current_chunk = ""
                is_first_in_chunk = True
                continue
            
            # Check if adding the new sentence would exceed the limit
            if len(current_chunk) + len(sentence) + (0 if is_first_in_chunk else 1) > max_chars:
                chunks.append(current_chunk.strip())
                current_chunk = sentence
                is_first_in_chunk = False
            else:
                if not is_first_in_chunk:
                    current_chunk += " "
                current_chunk += sentence
                is_first_in_chunk = False

        if current_chunk:
            chunks.append(current_chunk.strip())
            
        # Re-structure into the final dictionary format
        chunked_data = []
        for i, chunk_text in enumerate(chunks):
             chunked_data.append({
                "sentence_number": str(i + 1),
                "original_sentence": chunk_text,
                "paragraph": "no", # Paragraph data is lost during grouping, which is expected
                "tts_generated": "no",
                "marked": False
            })
        return chunked_data

    def preprocess_text(self, text, is_pdf=False, is_edited_text=False):
        """
        Splits text into sentences and detects paragraph breaks.
        """
        text = re.sub(r'\r\n?', '\n', text)
        text = re.sub(r'\t', ' ', text)
        if is_pdf or is_edited_text:
            paragraph_breaks = list(re.finditer(r'\n', text))
        else:
            text = re.sub(r'\n{2,}', '[[PARAGRAPH]]', text)
            text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)
            text = text.replace('[[PARAGRAPH]]', '\n')
            paragraph_breaks = list(re.finditer(r'\n', text))
        
        sentences = self.splitter.split(text)
        processed_sentences = []
        for i, sentence in enumerate(sentences):
            if not sentence.strip(): continue
            is_paragraph = any(match.start() < (text.find(sentence) + len(sentence)) <= (match.start() + 2) for match in paragraph_breaks)
            processed_sentences.append({
                "sentence_number": str(i + 1),
                "original_sentence": sentence.strip(),
                "paragraph": "yes" if is_paragraph else "no",
                "tts_generated": "no",
                "marked": False
            })
        return processed_sentences

def extract_text_from_file(file_path):
    """
    Extracts raw text from various document formats.
    """
    file_path = Path(file_path)
    ext = file_path.suffix.lower()
    text = ""
    print(f"Extracting text from {file_path}...")
    try:
        if ext == '.txt':
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
        elif ext == '.pdf':
            pdf = XPdf(file_path)
            text = pdf.to_text()
        elif ext == '.epub':
            book = epub.read_epub(file_path)
            html_content = "".join([item.get_body_content().decode('utf-8', errors='ignore') for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT)])
            soup = BeautifulSoup(html_content, 'html.parser')
            text = soup.get_text("\n", strip=True)
        elif ext in ['.docx', '.mobi']:
            # This requires a system-level installation of Pandoc
            text = pypandoc.convert_file(file_path, 'plain')
        else:
            raise ValueError(f"Unsupported file type: {ext}")
    except Exception as e:
        print(f"ERROR: Failed to extract text from {file_path}. Reason: {e}")
        if ext in ['.docx', '.mobi']:
            print("INFO: Processing .docx or .mobi files requires Pandoc to be installed on your system and accessible in your PATH.")
        return None
    print("Text extraction successful.")
    return text

def main():
    parser = argparse.ArgumentParser(
        description="Process a document into a session JSON file for Chatterbox Pro.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "input_file",
        type=str,
        help="Path to the source document (.txt, .pdf, .epub, .docx, .mobi)."
    )
    parser.add_argument(
        "--max_chars",
        type=int,
        default=300,
        help="The maximum number of characters for each audio chunk. Default: 300."
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default=None,
        help="Directory to save the output JSON file. Defaults to the same directory as the input file."
    )

    args = parser.parse_args()

    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"ERROR: Input file not found at '{args.input_file}'")
        return

    # Determine output path
    session_name = input_path.stem
    if args.output_dir:
        output_path = Path(args.output_dir)
        os.makedirs(output_path, exist_ok=True)
    else:
        output_path = input_path.parent
    
    json_filename = output_path / f"{session_name}_session.json"
    
    # --- Main Processing Pipeline ---
    raw_text = extract_text_from_file(input_path)
    if raw_text is None:
        return

    processor = TextPreprocessor()
    
    print("Step 1: Splitting text into individual sentences...")
    sentences = processor.preprocess_text(raw_text, is_pdf=input_path.suffix.lower() == '.pdf')
    print(f"Found {len(sentences)} sentences.")

    print(f"Step 2: Grouping sentences into chunks with a max character limit of {args.max_chars}...")
    chunked_sentences = processor.group_sentences_into_chunks(sentences, args.max_chars)
    print(f"Grouped into {len(chunked_sentences)} final chunks.")

    # Create the final session data structure
    session_data = {
        "source_file_path": str(input_path.resolve()),
        "sentences": chunked_sentences
    }

    # Save the JSON file
    try:
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=4, ensure_ascii=False)
        print(f"\nSUCCESS! Session file created at:\n{json_filename}")
    except Exception as e:
        print(f"\nERROR: Could not save the JSON file. Reason: {e}")

if __name__ == "__main__":
    main()