FROM mambaorg/micromamba:1.4.9

COPY --chown=$MAMBA_USER:$MAMBA_USER docker-env.yaml /tmp/docker-env.yaml
RUN micromamba install -y -n base -f /tmp/docker-env.yaml && \
    micromamba clean --trash -aflp --yes

# pip install packages that are not available/problematic on conda-forge
RUN /opt/conda/bin/python -m pip install \
    --no-deps \
    opencv-python-headless==4.8.0.76 \
    palom==2023.8.1 \
    imagej-rolling-ball==2023.8.3
RUN /opt/conda/bin/python -m pip cache purge

# add conda path to PATH to allow entrypoint overwrite
ENV PATH="${PATH}:/opt/conda/bin"
ENV JAVA_HOME="/opt/conda/lib/jvm"