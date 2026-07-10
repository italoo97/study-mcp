import torch
from transformers import AutoModel, AutoTokenizer
from transformers.modeling_utils import PreTrainedModel
from transformers.tokenization_utils_base import PreTrainedTokenizerBase

from study_mcp.core.config import settings


class EmbeddingEngine:
    def __init__(self) -> None:
        self._tokenizer: PreTrainedTokenizerBase | None = None
        self._model: PreTrainedModel | None = None

    def _load_model(self) -> None:
        if self._tokenizer is None:
            self._tokenizer = AutoTokenizer.from_pretrained(
                settings.EMBEDDING_MODEL
            )
        if self._model is None:
            self._model = AutoModel.from_pretrained(
                settings.EMBEDDING_MODEL,
                device_map='auto',
            )
            self._model.eval()

    @staticmethod
    def _mean_pooling(
        last_hidden_state: torch.Tensor,
        attention_mask: torch.Tensor,
    ) -> torch.Tensor:
        mask_expanded = (
            attention_mask.unsqueeze(-1)
            .expand(last_hidden_state.size())
            .float()
        )
        return torch.sum(last_hidden_state * mask_expanded, 1) / torch.clamp(
            mask_expanded.sum(1), min=1e-9
        )

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        self._load_model()

        all_embeddings: list[list[float]] = []
        batch_size = 32

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            encoded = self._tokenizer(  # type: ignore[misc]
                batch,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors='pt',
            )
            with torch.no_grad():
                output = self._model(**encoded)  # type: ignore[misc]

            embeddings = self._mean_pooling(
                output.last_hidden_state,
                encoded['attention_mask'],
            )
            embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
            all_embeddings.extend(embeddings.cpu().numpy().tolist())

        return all_embeddings

    def embed_query(self, query: str) -> list[float]:
        return self.embed_texts([query])[0]


embedding_engine = EmbeddingEngine()
