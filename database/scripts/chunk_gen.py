"""Token-bounded PDF chunks with overlap and source-page provenance."""

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import re
import unicodedata

from pypdf import PdfReader
import tiktoken


@dataclass(frozen=True)
class Chunk:
    text: str
    stop: str
    type: str
    source: str
    page: int
    chunk_index: int
    token_count: int


class ChunkGen:
    """Prefer paragraphs, lines, sentences, then words; never mix pages or documents."""

    def __init__(self, max_tokens: int = 400, overlap_tokens: int = 60) -> None:
        if max_tokens < 2 or not 0 <= overlap_tokens < max_tokens:
            raise ValueError("Require max_tokens >= 2 and 0 <= overlap_tokens < max_tokens.")
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.encoding = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        return len(self.encoding.encode(text, disallowed_special=()))

    def _units(self, text: str, budget: int) -> list[str]:
        if self.count_tokens(text) <= budget:
            return [text]
        for separator in (r"(?<=\n)\s*\n", r"(?<=\n)", r"(?<=[.!?])(?=\s)", r"(?<=\s)(?=\S)"):
            parts = re.split(separator, text)
            if len(parts) > 1:
                return [unit for part in parts if part for unit in self._units(part, budget)]
        # Split unusually long words without cutting a UTF-8 character in half.
        units: list[str] = []
        current = ""
        for character in text:
            if self.count_tokens(character) > budget:
                raise ValueError("Token budget is too small to preserve a Unicode character.")
            if self.count_tokens(current + character) > budget:
                units.append(current)
                current = ""
            current += character
        if current:
            units.append(current)
        return units

    def _overlap(self, text: str) -> str:
        if not self.overlap_tokens:
            return ""
        words = re.findall(r"\S+\s*", text)
        tail = ""
        for word in reversed(words):
            if self.count_tokens(word + tail) > self.overlap_tokens:
                break
            tail = word + tail
        return tail

    def split_text(self, text: str) -> list[str]:
        text = unicodedata.normalize("NFC", text).replace("\x00", "").replace("\x7f", " ").strip()
        if not text:
            raise ValueError("Cannot chunk empty text.")
        chunks: list[str] = []
        current = ""
        for unit in self._units(text, self.max_tokens - self.overlap_tokens):
            if current and self.count_tokens(current + unit) > self.max_tokens:
                chunks.append(current.strip())
                current = self._overlap(current)
                if self.count_tokens(current + unit) > self.max_tokens:
                    current = ""
            current += unit
        if current.strip():
            chunks.append(current.strip())
        return chunks

    def generate(self, pdf: Path, *, docs_root: Path) -> list[Chunk]:
        relative = pdf.resolve().relative_to(docs_root.resolve())
        if len(relative.parts) != 3:
            raise ValueError(f"Expected <stop>/<type>/<document.pdf>, got {relative}.")
        stop, category, _ = relative.parts
        reader = PdfReader(pdf)
        if reader.is_encrypted:
            raise ValueError(f"Encrypted PDF is not supported: {pdf}")
        pages = [
            [line.rstrip() for line in (page.extract_text(extraction_mode="layout") or "").splitlines()]
            for page in reader.pages
        ]
        if not pages:
            raise ValueError(f"PDF has no pages: {pdf}")
        # Only repeated edge lines qualify as running headers/footers.
        def edge_indices(lines: list[str]) -> set[int]:
            nonempty = [index for index, line in enumerate(lines) if line.strip()]
            return set(nonempty[:2] + nonempty[-2:])

        def edge_key(line: str) -> str:
            without_page = re.sub(r"\bPage \d+(?: of \d+)?\s*$", "", line, flags=re.I)
            return re.sub(r"\s+", " ", without_page).strip()

        edges: Counter[str] = Counter()
        for lines in pages:
            edges.update({edge_key(lines[index]) for index in edge_indices(lines)})
        repeated = {
            line for line, count in edges.items()
            if len(pages) >= 3 and count >= max(3, (len(pages) + 1) // 2)
        }
        chunks: list[Chunk] = []
        for page_number, lines in enumerate(pages, start=1):
            indices = edge_indices(lines)
            cleaned = [
                line for index, line in enumerate(lines)
                if not (
                    index in indices
                    and (
                        edge_key(line) in repeated
                        or re.fullmatch(r"Page \d+(?: of \d+)?", line.strip(), re.I)
                    )
                )
            ]
            if not any(line.strip() for line in cleaned):
                raise ValueError(f"No extractable text in {pdf}, page {page_number}; OCR is required.")
            for text in self.split_text("\n".join(cleaned)):
                chunks.append(Chunk(
                    text=text,
                    stop=stop,
                    type=category,
                    source=relative.as_posix(),
                    page=page_number,
                    chunk_index=len(chunks),
                    token_count=self.count_tokens(text),
                ))
        return chunks