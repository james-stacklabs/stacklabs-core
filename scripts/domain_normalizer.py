#!/usr/bin/env python3
"""
StackLabs Domain Normalizer // SymSpell O(1) Ingestion Filter
Symmetric Delete algorithm for sub-50µs term normalization.
Target: Clio (100.91.229.87) | Python 3.12 (.venv)
"""
import os
import re
import time
from typing import Optional, List, Dict, Set

DEFAULT_LEXICON = "/home/james/stacklabs/data/lexicons/domain_lexicon.txt"

class SymSpellNormalizer:
    def __init__(self, lexicon_path: str = DEFAULT_LEXICON, max_edit_distance: int = 2):
        self.lexicon_path = lexicon_path
        self.max_edit_distance = max_edit_distance
        self.words: Dict[str, int] = {}
        self.deletes: Dict[str, List[str]] = {}
        self._load_lexicon()

    def _get_deletes(self, word: str, distance: int) -> Set[str]:
        deletes = set()
        queue = [word]
        for _ in range(distance):
            temp_queue = []
            for item in queue:
                for i in range(len(item)):
                    delete_item = item[:i] + item[i+1:]
                    if delete_item and delete_item not in deletes:
                        deletes.add(delete_item)
                        temp_queue.append(delete_item)
            queue = temp_queue
        return deletes

    def _load_lexicon(self):
        t0 = time.perf_counter()
        if not os.path.exists(self.lexicon_path):
            os.makedirs(os.path.dirname(self.lexicon_path), exist_ok=True)
            with open(self.lexicon_path, "w", encoding="utf-8") as f:
                f.write("systemd 1000\nclio 1500\nsynapse 1200\n")

        with open(self.lexicon_path, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split()
                if not parts:
                    continue
                word = parts[0].lower()
                freq = int(parts[1]) if len(parts) > 1 else 1
                self.words[word] = freq
                for del_word in self._get_deletes(word, self.max_edit_distance):
                    if del_word not in self.deletes:
                        self.deletes[del_word] = []
                    self.deletes[del_word].append(word)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        print(f"[*] SymSpell loaded {len(self.words)} terms ({len(self.deletes)} delete hashes) in {elapsed_ms:.2f}ms")

    def lookup(self, term: str) -> Optional[str]:
        clean_term = term.strip().lower()
        if clean_term in self.words:
            return clean_term
        candidates = self.deletes.get(clean_term, [])
        if candidates:
            candidates.sort(key=lambda w: self.words.get(w, 0), reverse=True)
            return candidates[0]
        for del_item in self._get_deletes(clean_term, self.max_edit_distance):
            if del_item in self.words:
                return del_item
            if del_item in self.deletes:
                matches = self.deletes[del_item]
                matches.sort(key=lambda w: self.words.get(w, 0), reverse=True)
                return matches[0]
        return None

    def normalize_sentence(self, text: str) -> str:
        tokens = re.split(r'(\s+)', text)
        result = []
        for token in tokens:
            if not token.strip():
                result.append(token)
                continue
            matched = self.lookup(token)
            result.append(matched if matched else token)
        return "".join(result)

_instance: Optional[SymSpellNormalizer] = None

def get_normalizer() -> SymSpellNormalizer:
    global _instance
    if _instance is None:
        _instance = SymSpellNormalizer()
    return _instance
