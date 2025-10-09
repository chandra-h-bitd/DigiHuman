from app.main import embed_with_sbert
import numpy as np


def test_sbert_shape():
    vecs = embed_with_sbert(["hello world", "test sentence"])
    assert isinstance(vecs, np.ndarray)
    assert vecs.shape[0] == 2
    assert vecs.shape[1] in (384, 768, 1024)
