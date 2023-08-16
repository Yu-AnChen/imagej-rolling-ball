try:
    import importlib.metadata as importlib_metadata
except ModuleNotFoundError:
    import importlib_metadata

__version__ = importlib_metadata.version(__name__)

from .bg_subtracter import (
    BackgroundSubtracter,
    da_to_zarr,
    get_shrink_factor,
    compute_chunk_size_and_overlap
)