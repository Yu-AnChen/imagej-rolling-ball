# Note for creating/building docker image for imagej-rolling-ball ([reference](https://micromamba-docker.readthedocs.io/en/latest/advanced_usage.html#advanced-usages))

1. Create reference env on micromamba's docker image

    ```bash
    # Run bash in micromamba docker image with bind volume for writing out env
    # lock file
    docker run -it --rm --platform linux/amd64 -v "$(pwd)":/data mambaorg/micromamba:1.4.9 bash
    ```

    ```bash
    # Manually install known deps in `pyimagej` env 
    micromamba create -y -n pyimagej pyimagej openjdk=11 python=3.10 "scikit-image<0.20" scikit-learn "zarr<2.15" tifffile imagecodecs matplotlib tqdm scipy dask numpy loguru=0.5.3 "ome-types>0.3" "pydantic<2" pint napari-lazy-openslide yamale fire termcolor wget unzip procps-ng -c conda-forge


    # Use `pip install --dry-run` to verify, only expecting to see `opencv`,
    # `palom`, and `imagej-rolling-ball`
    micromamba activate pyimagej
    python -m pip install --dry-run imagej-rolling-ball[wsi]
    # output: Would install imagej-rolling-ball-2023.8.6 opencv-python-4.8.0.76
    # palom-2023.8.1


    # if the above checks out, export micromamba env as yaml
    micromamba env export --explicit > /data/docker-env.lock


    # pip install the rest packages, note: use `opencv-python-headless` instead
    # of `opencv-python`
    python -m pip install --no-deps imagej-rolling-ball==2023.8.6 palom==2023.8.1 opencv-python-headless==4.8.0.76


    # Test the environment
    rolling-ball -h
    python -c "import cv2; cv2.blur"
    ```

1. Write the Dockerfile based on micromamba and the env.yaml file

    `Dockerfile`

    ```Dcokerfile
    FROM mambaorg/micromamba:1.4.9

    COPY --chown=$MAMBA_USER:$MAMBA_USER docker-env.lock /tmp/docker-env.lock
    RUN micromamba install --name base --yes --file /tmp/docker-env.lock \
        && micromamba clean --trash -aflp --yes

    # pip install packages that are not available/problematic on conda-forge
    RUN /opt/conda/bin/python -m pip install \
        --no-deps \
        opencv-python-headless==4.8.0.76 \
        palom==2023.8.1 \
        imagej-rolling-ball==2023.8.6 \
        && /opt/conda/bin/python -m pip cache purge
    ```

1. When building the docker image, specify `--platform linux/amd64`

    ```bash
    docker build --platform linux/amd64 --tag test-ijrb .
    ```

1. Test the image

    ```bash
    docker run -it --rm --platform linux/amd64 test-ijrb \
        python -c "import numpy, tifffile, subprocess; \
        tifffile.imwrite('test.tif', numpy.eye(1500, dtype='uint8')); \
        subprocess.run(['rolling-ball', 'test.tif', '20', '--imagej_version', '/tmp/Fiji.app'])"
    ```

    output

    ```log
    2023-08-18 17:12:46.676 | WARNING  | palom.reader:auto_format_pyramid:64 - Unable to detect pyramid levels, it may take a while to compute thumbnails during coarse alignment
    2023-08-18 17:12:46.678 | INFO     | imagej_rolling_ball.cli.rolling_ball:process_ometiff:52 - 

        Processing: test.tif
        Rolling ball radius: 20
        Input shape: (1, 1500, 1500)
        Output path: test-ij_rolling_ball_20.ome.tif

        
    Java option: -Xmx5832m
    ImageJ Version: 2.14.0/1.54f
    Operating in headless mode - the original ImageJ will have limited functionality.
    2023-08-18 17:12:49.841 | WARNING  | palom.reader:pixel_size:173 - Unable to parse pixel size from test.tif; assuming 1 µm. Use `_pixel_size` to set it manually
    2023-08-18 17:12:49.842 | INFO     | palom.pyramid:write_pyramid:167 - Writing to test-ij_rolling_ball_20.ome.tif
    Assembling mosaic  1/ 1 (channel  1/ 1): 100%|##########| 14/14 [00:00<00:00, 15.40it/s]
    2023-08-18 17:12:51.124 | INFO     | palom.pyramid:write_pyramid:186 - Generating pyramid
    2023-08-18 17:12:51.125 | INFO     | palom.pyramid:write_pyramid:191 -     Level 1 (750 x 750)
    Processing channel: 100%|#################################| 1/1 [00:00<00:00, 94.81it/s]
    0
    ```
