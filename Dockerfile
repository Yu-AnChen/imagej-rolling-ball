FROM mambaorg/micromamba:1.4.9

COPY --chown=$MAMBA_USER:$MAMBA_USER docker-env.yaml /tmp/docker-env.yaml
RUN micromamba install -y -n base -f /tmp/docker-env.yaml && \
    micromamba clean --trash -aflp --yes

RUN /opt/conda/bin/python -m pip install \
    --no-deps \
    opencv-python-headless==4.8.0.76 \
    palom==2023.8.1 \
    imagej-rolling-ball==2023.8.1

RUN /opt/conda/bin/python -m pip cache purge