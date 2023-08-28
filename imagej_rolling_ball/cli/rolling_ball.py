import pathlib
import sys

import dask.array as da
import dask.config
import fire
import palom
import tifffile
from loguru import logger
from palom.cli import pyramid_tools as ptools

from .. import BackgroundSubtracter
from .. import __version__ as _version

ROLLING_BALL_DEFAULT = {
    'create_background': False,
    'light_background': False,
    'use_paraboloid': False,
    'do_presmooth': False,
    'correct_corners': True,
}


def process_ometiff(
    img_path,
    radius,
    out_path: str = None,
    target_chunk_size: int = 1024*5,
    overwrite: bool = False,
    java_options: str = None,
    imagej_version: str = None,
    pyramid_config: dict = None,
    rolling_ball_kwargs: dict = None,
    num_workers: int = 4
):
    img_path = pathlib.Path(img_path).resolve()
    reader = palom.reader.OmePyramidReader(img_path)
    stem = img_path.name.split('.')[0]
    out_path = ptools.validate_out_path(
        # FIXME out_path should be full path; this should be handled by
        # `validate_out_path`
        out_path if out_path is None else pathlib.Path(out_path).resolve(),
        img_path.parent / f"{stem}-ij_rolling_ball_{radius}.ome.tif",
        overwrite=overwrite
    )

    log_str = f"""

    Processing: {img_path.name}
    Rolling ball radius: {radius}
    Input shape: {reader.pyramid[0].shape}
    Output path: {out_path}

    """
    logger.info(log_str)
    if java_options is not None:
        logger.info(f"Java option: {java_options}")

    img = reader.pyramid[0]
    bg_subtracter = BackgroundSubtracter(
        java_options=java_options,
        _imagej_version=imagej_version
    )

    if rolling_ball_kwargs is None: rolling_ball_kwargs = {}
    out = []
    for channel in img:
        out.append(
            bg_subtracter.rolling_ball_background_chunked(
                channel, radius, target_chunk_size,
                **{**ROLLING_BALL_DEFAULT, **rolling_ball_kwargs}
            )
        )
    try:
        tif_tags = ptools.src_tif_tags(img_path)
    except Exception:
        tif_tags = {}
    tif_tags.update({'software': f"imagej-rolling-ball v{_version}"})
    # FIXME handle channel names?
    if pyramid_config is None: pyramid_config = {}

    with dask.config.set(scheduler='threads', num_workers=num_workers):
        palom.pyramid.write_pyramid(
            [da.array(out)],
            output_path=out_path,
            **{
                **dict(
                    pixel_size=reader.pixel_size,
                    kwargs_tifffile=tif_tags,
                ),
                **dict(
                    downscale_factor=2,
                    compression='zlib',
                    tile_size=1024,
                    save_RAM=True
                ),
                **pyramid_config
            }
        )
    try:
        ome_xml = tifffile.tiffcomment(img_path)
        tifffile.tiffcomment(out_path, ome_xml.encode())
    except Exception:
        logger.warning("Unable to transfer original ome-xml from input image")
    return 0


def main():
    sys.exit(fire.Fire(process_ometiff))


if __name__ == '__main__':
    main()
