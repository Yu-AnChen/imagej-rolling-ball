# imagej-rolling-ball

Python wrapper for [ImageJ's rolling ball background
subtraction](https://imagej.net/ij/developer/api/ij/ij/plugin/filter/BackgroundSubtracter.html#rollingBallBackground(ij.process.ImageProcessor,double,boolean,boolean,boolean,boolean,boolean))
using [pyimagej](https://github.com/imagej/pyimagej).

## Install

1. Follow [pyimagej's installation
   instruction](https://py.imagej.net/en/latest/Install.html)

1. Install `imagej-rolling-ball` from pypi

    ```bash
    python -m pip install imagej-rolling-ball
    ```

1. To work with large images, `dask` and `zarr` were used in the package. You
   can install them yourself or specify the `[large]` install

    ```bash
    python -m pip install imagej-rolling-ball[large]
    ```

1. To work with pyramidal ome-tiff images, `palom` was used. Install the `[wsi]`
   extras

    ```bash
    python -m pip install imagej-rolling-ball[wsi]
    ```

## Usage

The key parameter is the rolling ball radius, according to the
[doc](https://imagej.nih.gov/ij/docs/menus/process.html#background), the radius

> should be at least as large as the radius of the largest object in the image
> that is not part of the background

**NOTE:** While the java class `BackgroundSubtracter` handles RGB image, the
current wrapper methods only accepts 2D arrays. One can process each channel
separately and combine all the processed channels using `numpy.array` or
`numpy.dstack`


### Basic usage

```python
import imagej_rolling_ball
import numpy

bg_subtracter = imagej_rolling_ball.BackgroundSubtracter(java_options='-Xmx1g')
img = numpy.eye(5) + 1

print('img\n', img, '\n')
print('radius=1')
print(bg_subtracter.rolling_ball_background(img, 1), '\n')
print('radius=2.5')
print(bg_subtracter.rolling_ball_background(img, 2.5), '\n')
```

And the output of the above script should be

```python
img
 [[2. 1. 1. 1. 1.]
 [1. 2. 1. 1. 1.]
 [1. 1. 2. 1. 1.]
 [1. 1. 1. 2. 1.]
 [1. 1. 1. 1. 2.]] 

radius=1
[[0. 0. 0. 0. 0.]
 [0. 0. 0. 0. 0.]
 [0. 0. 0. 0. 0.]
 [0. 0. 0. 0. 0.]
 [0. 0. 0. 0. 0.]] 

radius=2
[[0.        0.        0.        0.        0.       ]
 [0.        0.7912879 0.        0.        0.       ]
 [0.        0.        0.7912879 0.        0.       ]
 [0.        0.        0.        0.7912879 0.       ]
 [0.        0.        0.        0.        0.       ]] 
```

### Process large image

For large array (e.g. array that contains more than 2,147,483,647 elements), the
`BackgroundSubtracter.rolling_ball_background_chunked` method is for such use
case. It returns a `dask.array` by default or a `zarr.core.Array` if
`compute=True` is set.


```python
In [1]: import imagej_rolling_ball
   ...: import numpy
   ...: 
   ...: bg_subtracter = imagej_rolling_ball.BackgroundSubtracter(java_options='-Xmx4g')
   ...: img = numpy.eye(10_000, dtype='uint8') + 1
ImageJ Version: 2.14.0/1.54f

In [2]: bg_subtracter.rolling_ball_background_chunked(img, 50, 1024*5)
Operating in headless mode - the original ImageJ will have limited functionality.
Out[2]: dask.array<_trim, shape=(10000, 10000), dtype=uint8, chunksize=(5120, 5120), chunktype=numpy.ndarray>

In [3]: bg_subtracter.rolling_ball_background_chunked(img, 50, 1024*5).compute()
Out[3]: 
array([[1, 0, 0, ..., 0, 0, 0],
       [0, 1, 0, ..., 0, 0, 0],
       [0, 0, 1, ..., 0, 0, 0],
       ...,
       [0, 0, 0, ..., 1, 0, 0],
       [0, 0, 0, ..., 0, 1, 0],
       [0, 0, 0, ..., 0, 0, 1]], dtype=uint8)

In [4]: bg_subtracter.rolling_ball_background_chunked(img, 50, 1024*5, compute=True)
Out[4]: <zarr.core.Array (10000, 10000) uint8>
```

### Process chunked ome-tiff in command line interface

Use `rolling-ball` command to process multi-channel tiff file and write the
processed image to disk as a pyramidal ome-tiff. `python -m pip install
imagej-rolling-ball[wsi]` is required.

```bash
NAME
    rolling-ball

SYNOPSIS
    rolling-ball IMG_PATH RADIUS <flags>

POSITIONAL ARGUMENTS
    IMG_PATH
    RADIUS

FLAGS
    --out_path=OUT_PATH
        Type: Optional[str]
        Default: None
    -t, --target_chunk_size=TARGET_CHUNK_SIZE
        Type: int
        Default: 5120
    --overwrite=OVERWRITE
        Type: bool
        Default: False
    -j, --java_options=JAVA_OPTIONS
        Type: Optional[str]
        Default: None
    -i, --imagej_version=IMAGEJ_VERSION
        Type: Optional[str]
        Default: None
    -p, --pyramid_config=PYRAMID_CONFIG
        Type: Optional[dict]
        Default: None
    --rolling_ball_kwargs=ROLLING_BALL_KWARGS
        Type: Optional[dict]
        Default: None
    -n, --num_workers=NUM_WORKERS
        Type: int
        Default: 4
```

**NOTES:**

- To pass in JVM options, e.g. set max heap size (`-Xmx4g`), use the syntax of
   `-j="-Xmx4g"`
- The defaut Java heap size is 70% of the available memory
- Increase `--num_workers` may speed up processing time, default is `4`
- The default output file will be generated next to the input file, the file
  name ends with `-ij_rolling_ball_{radius}.ome.tif`

**Example commands:**

- Minimal command, process file using rolling ball radius of `100` and
  writebackground-subtracted image to disk

    ```bash
    rolling-ball path/to/input/file.ome.tif 100
    ```

- Write background image instead of subtracted image (`--rolling_ball_kwargs
  "{'create_background': True}"`) to file; set JVM max heap size to 4 GB
  (`-j="-Xmx4g"`) and use 8 threads (`-n=8`)

    ```bash
    rolling-ball path/to/input/file.ome.tif 100 \
        --out_path path/to/input/file-background_100.ome.tif \
        --rolling_ball_kwargs "{'create_background': True}" \
        -j="-Xmx4g" \ 
        --overwrite \
        -n=8
    ```

### Docker usage

The docker image can be build from the github repo or be pulled from the docker
hub.

To process an image file (`input.ome.tif`) with rolling ball radius `50` in the
current directory:

```bash
 docker run -it --rm -v "$(pwd)":/data \
    yuanchen12/imagej-rolling-ball \
    rolling-ball /data/input.ome.tif 50
```

When the process is completed, output file `input-ij_rolling_ball_50.ome.tif`
will be generated.
