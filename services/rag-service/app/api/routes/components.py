"""Component listing and info endpoints."""

from typing import List

from fastapi import APIRouter, HTTPException

from app.components.base.registry import ComponentRegistry
from app.components.base.factory import ComponentNotFoundError
from app.models.schemas import (
    ComponentInfo,
    ComponentListResponse,
    CategoryComponentsResponse,
)

# Import all component modules to register them
from app.components.parsers import (
    AutoParser, PDFParser, MarkdownParser, TextParser,
    DocxParser, HTMLParser, CSVParser
)
from app.components.chunkers import (
    RecursiveChunker, FixedChunker, SentenceChunker, SemanticChunker
)
from app.components.embedders import OpenAIEmbedder, LocalEmbedder
from app.components.indexers import MilvusIndexer, ElasticsearchIndexer
from app.components.searchers import SemanticSearcher, FulltextSearcher, HybridSearcher
from app.components.optimizers import (
    ScoreThresholdOptimizer, MaxResultsOptimizer,
    DeduplicationOptimizer, RerankingOptimizer
)

router = APIRouter()


@router.get("", response_model=ComponentListResponse)
async def list_all_components():
    """List all available components grouped by category."""
    all_components = ComponentRegistry.get_all_components()

    return ComponentListResponse(
        parsers=[ComponentInfo(**c) for c in all_components.get("parsers", [])],
        chunkers=[ComponentInfo(**c) for c in all_components.get("chunkers", [])],
        embedders=[ComponentInfo(**c) for c in all_components.get("embedders", [])],
        indexers=[ComponentInfo(**c) for c in all_components.get("indexers", [])],
        searchers=[ComponentInfo(**c) for c in all_components.get("searchers", [])],
        optimizers=[ComponentInfo(**c) for c in all_components.get("optimizers", [])],
    )


@router.get("/{category}", response_model=CategoryComponentsResponse)
async def list_category_components(category: str):
    """List all components in a specific category.

    Categories: parsers, chunkers, embedders, indexers, searchers, optimizers
    """
    valid_categories = ComponentRegistry.list_categories()

    if category not in valid_categories:
        raise HTTPException(
            status_code=404,
            detail=f"Category '{category}' not found. Available: {valid_categories}",
        )

    try:
        factory = ComponentRegistry.get_factory(category)
        components = factory.list_available()

        return CategoryComponentsResponse(
            category=category,
            components=[ComponentInfo(**c) for c in components],
            count=len(components),
        )
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Category '{category}' not found")


@router.get("/{category}/{name}", response_model=ComponentInfo)
async def get_component_info(category: str, name: str):
    """Get detailed information about a specific component."""
    try:
        info = ComponentRegistry.get_component_info(category, name)
        return ComponentInfo(**info)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Category '{category}' not found",
        )
    except ComponentNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        )
