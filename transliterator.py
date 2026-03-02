import torch
import argparse

# 🔥 Fix for PyTorch 2.6 weights_only issue
torch.serialization.add_safe_globals([argparse.Namespace])

import pandas as pd
import os
from ai4bharat.transliteration import XlitEngine


class CSVTransliterator:
    def __init__(self, beam_width=5):
        print("\n🔄 Initializing Hindi transliterator...")
        self.engine = XlitEngine("hi", beam_width=beam_width, rescore=True)
        print("✅ Transliterator ready!\n")

    def transliterate_word(self, text):
        try:
            result = self.engine.translit_word(str(text).strip())
            suggestions = result.get("hi", [])
            return suggestions[0] if suggestions else ""
        except Exception:
            return ""

    def transliterate_csv(
        self,
        input_csv,
        output_csv,
        source_column,
        output_column="hindi_transliteration",
        progress_callback=None,
    ):
        if not os.path.exists(input_csv):
            raise FileNotFoundError(f"Input file not found: {input_csv}")

        df = pd.read_csv(input_csv)

        if source_column not in df.columns:
            raise ValueError(
                f"Column '{source_column}' not found. "
                f"Available columns: {list(df.columns)}"
            )

        total = len(df)
        results = []

        for i, text in enumerate(df[source_column].astype(str)):
            hindi = self.transliterate_word(text.lower())
            results.append(hindi)

            if progress_callback and (i % 100 == 0 or i == total - 1):
                progress_callback(i + 1, total)

        df[output_column] = results
        df.to_csv(output_csv, index=False, encoding="utf-8")

        return output_csv
