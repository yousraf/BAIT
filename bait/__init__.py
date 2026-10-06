"""BAIT: cognitive bias trigger detection benchmark - evaluation code."""
from .data import BIAS_CODES, BIAS_NAMES, Document, bias_code, load_documents
from .align import align_prediction
from .parse import parse_completion
from .evaluate import doc_level_metrics, accumulate_span_counts, span_metrics
