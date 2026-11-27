from pathlib import Path

import joblib
import pandas as pd

from ml.preprocessing.features import ERROR_TAXONOMY, ExecutionSample, build_feature_document


def test_dataset_and_model_artifact_exist_and_predict_valid_classes() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    csv_path = repo_root / "ml" / "datasets" / "python_errors_v1.csv"
    artifact_path = repo_root / "ml" / "artifacts" / "error_classifier_v1.joblib"

    assert csv_path.exists(), "Validated dataset CSV must exist"
    assert artifact_path.exists(), "Trained model artifact joblib must exist"

    df = pd.read_csv(csv_path)
    assert len(df) >= 250
    assert df["program_family"].nunique() >= 30
    assert set(df["label"].unique()).issubset(set(ERROR_TAXONOMY))
    assert len(set(df["label"].unique())) == len(ERROR_TAXONOMY)

    bundle = joblib.load(artifact_path)
    pipe = bundle["pipeline"]
    sample = ExecutionSample(
        source_code=(
            "def total_range(a, b):\n"
            "    s = 0\n"
            "    for i in range(a, b):\n"
            "        s += i\n"
            "    return s\n"
        ),
        verdict="wrong_answer",
        stdout_actual="7",
        stdout_expected="12",
        passed_tests=0,
        total_tests=2,
    )
    doc = build_feature_document(sample)
    pred = pipe.predict([doc])[0]
    probs = pipe.predict_proba([doc])[0]
    assert pred in ERROR_TAXONOMY
    assert abs(float(sum(probs)) - 1.0) < 1e-5


def test_rag_evaluation_default_threshold_022_and_multilanguage_ood_rejection() -> None:
    from app.services.mentor.embeddings import LocalSemanticEmbedder, cosine_similarity
    from app.services.mentor.knowledge_corpus import (
        ALL_APPROVED_KNOWLEDGE_DOCS,
        chunk_markdown_document,
    )
    from ml.evaluation.evaluate_rag import run_rag_evaluation

    report = run_rag_evaluation()
    assert report["similarity_threshold"] == 0.22
    assert report["hit_at_1"] == 1.0
    assert report["hit_at_3"] == 1.0
    assert report["mrr"] == 1.0
    assert report["no_match_rejection_rate"] == 1.0

    # Multi-language OOD regression check across all 26 approved docs
    embedder = LocalSemanticEmbedder(dimensions=256)
    threshold = 0.22
    chunk_vecs = []
    for doc in ALL_APPROVED_KNOWLEDGE_DOCS:
        for heading, body in chunk_markdown_document(doc.content_md):
            embed_input = (
                f"{doc.title}\nLanguage: {doc.language_slug}\nTopic: {doc.topic}\n"
                f"Errors: {' '.join(doc.error_codes)}\n{heading}\n{body}"
            )
            chunk_vecs.append((doc.slug, embedder.embed(embed_input)))

    ood_queries = [
        "sourdough bread fermentation hydration starter recipe oven temperature",
        "medieval french cathedral flying buttress limestone masonry architecture",
        "photosynthesis chlorophyll thylakoid membrane calvin cycle botany",
        "world cup football offside rule goalkeeper penalty shootout",
        "espresso extraction portafilter grind size crema roast profile",
    ]
    for query in ood_queries:
        qvec = embedder.embed(query)
        max_sim = max(cosine_similarity(qvec, cvec) for _, cvec in chunk_vecs)
        assert max_sim < threshold, (
            f"OOD query {query!r} exceeded threshold {threshold} (max_sim={max_sim:.4f})"
        )
