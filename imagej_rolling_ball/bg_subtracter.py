import math

import imagej
import jpype
import numpy as np
import psutil
import scyjava

# `BackgroundSubtracter` is in ImageJ not ImageJ2 - use global variable to
# prevent multiple instances

# https://github.com/imagej/pyimagej/blob/fd7de5c192e712ec96fab0ffc0ee84b9ffbf1f12/doc/11-Working-with-the-original-ImageJ.ipynb
'''
ImageJ was not designed to run multiple simultaneous instances in the same JVM,
whereas ImageJ2 supports multiple gateways at once.

def legacy_status(gateway):
    print(f" legacy service: {gateway.legacy}") print(f"  legacy active?
    {gateway.legacy and gateway.legacy.isActive()}") print(f"ImageJ2 version:
    {gateway.getVersion()}")

another_ij = imagej.init() print("[ij - the original gateway]")
legacy_status(ij) print("\n[another_ij - a second gateway we constructed just
now]") legacy_status(another_ij)

[ij - the original gateway]
 legacy service: net.imagej.legacy.LegacyService [priority = 1.0]
  legacy active? True
ImageJ2 version: 2.14.0/1.54f

[another_ij - a second gateway we constructed just now]
 legacy service: net.imagej.legacy.LegacyService [priority = 1.0]
  legacy active? False
ImageJ2 version: 2.14.0/Inactive
'''
IJ = None


class BackgroundSubtracter():
    '''
    https://imagej.net/ij/developer/api/ij/ij/plugin/filter/BackgroundSubtracter.html#rollingBallBackground(ij.process.ImageProcessor,double,boolean,boolean,boolean,boolean,boolean)

    public void rollingBallBackground(ImageProcessor ip, double radius, boolean createBackground, boolean lightBackground, boolean useParaboloid, boolean doPresmooth, boolean correctCorners)

    Create or subtract a background, works for all image types. For RGB images, the background is subtracted from each channel separately
    
    Parameters:
    
    ip - The image. On output, it will become the background-subtracted image or
    the background (depending on createBackground).
    
    radius - Radius of the rolling ball creating the background (actually a
    paraboloid of rotation with the same curvature)
    
    createBackground - Whether to create a background, not to subtract it.
    
    lightBackground - Whether the image has a light background.
    
    useParaboloid - Whether to use the "sliding paraboloid" algorithm.
    
    doPresmooth - Whether the image should be smoothened (3x3 mean) before
    creating the background. With smoothing, the background will not necessarily
    be below the image data.
    
    correctCorners - Whether the algorithm should try to detect corner particles
    to avoid subtracting them as a background.
    '''
    def __init__(self, java_options=None, _imagej_version=None) -> None:
        global IJ
        if ('IJ' not in globals()) or IJ is None:
            if java_options is None:
                java_ram_fraction = 0.7
                java_ram = math.floor(
                    psutil.virtual_memory().available / 1024**2 * java_ram_fraction
                )
                java_options = f"-Xmx{java_ram}m"
            scyjava.config.add_option(java_options)
            print('Java option:', java_options)
            IJ = imagej.init(_imagej_version)
        print('ImageJ Version:', IJ.getVersion())
        self.background_subtracter = jpype.JClass(
            'ij.plugin.filter.BackgroundSubtracter'
        )()
    
    def rolling_ball_background(
        self,
        img,
        radius: float,
        create_background: bool = False,
        light_background: bool = False,
        use_paraboloid: bool = False,
        do_presmooth: bool = False,
        correct_corners: bool = True,
        inplace = False,
    ):
        assert img.ndim == 2
        if not inplace:
            img = np.array(img)
        imp = IJ.py.to_imageplus(img)
        self.background_subtracter.rollingBallBackground(
            imp.getProcessor(),
            radius,
            create_background,
            light_background,
            use_paraboloid,
            do_presmooth,
            correct_corners
        )
        IJ.py.sync_image(imp)
        imp.close()
        imp = None
        return img

    def rolling_ball_background_chunked(
        self, img, radius, chunk_size, compute=False, **kwargs
    ):
        assert img.ndim == 2
        import dask.array as da
        import zarr
        h, w = img.shape
        overlap_depth = radius * get_shrink_factor(radius)    
        chunk_h, overlap_h = compute_chunk_size_and_overlap(chunk_size, overlap_depth, h)
        chunk_w, overlap_w = compute_chunk_size_and_overlap(chunk_size, overlap_depth, w)

        if issubclass(type(img), np.ndarray):
            zimg = zarr.create(
                img.shape,
                chunks=(chunk_h, chunk_w),
                dtype=img.dtype
            )
            zimg[:] = img
            img = None
            img = da.from_zarr(zimg)
        
        if not np.all(img.chunksize == (chunk_h, chunk_w)):
            img = img.rechunk((chunk_h, chunk_w))
        processed = da.map_overlap(
            self.rolling_ball_background, img, dtype=img.dtype, 
            depth={0: overlap_h, 1: overlap_w}, boundary='none', radius=radius,
            **kwargs
        )
        if compute:
            return da_to_zarr(processed)
        return processed


def compute_chunk_size_and_overlap(chunk_size, overlap_depth, img_size):
    # small image
    if (img_size <= chunk_size) or (img_size <= overlap_depth):
        return img_size, 0
    # small chunk
    if chunk_size <= overlap_depth:
        chunk_size = overlap_depth
    chunk_size = math.ceil(chunk_size / 8) * 8
    return chunk_size, overlap_depth


# https://github.com/imagej/imagej1/blob/master/ij/plugin/filter/BackgroundSubtracter.java#L779-L795
def get_shrink_factor(radius):
    if radius <= 10:
        shrinkFactor = 2
    elif radius <= 30:
        shrinkFactor = 2
    elif radius <= 100:
        shrinkFactor = 4
    else:
        shrinkFactor = 8
    return shrinkFactor


def da_to_zarr(da_img, zarr_store=None, num_workers=None, out_shape=None, chunks=None):
    import zarr
    if zarr_store is None:
        if out_shape is None:
            out_shape = da_img.shape
        if chunks is None:
            chunks = da_img.chunksize
        zarr_store = zarr.create(
            out_shape,
            chunks=chunks,
            dtype=da_img.dtype,
            overwrite=True
        )
    da_img.to_zarr(zarr_store, compute=False).compute(
        num_workers=num_workers
    )
    return zarr_store
