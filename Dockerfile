FROM mambaorg/micromamba:1.4.9

COPY --chown=$MAMBA_USER:$MAMBA_USER docker-env.yaml /tmp/docker-env.yaml
RUN micromamba install -y -n base -f /tmp/docker-env.yaml && \
    micromamba clean --all --yes
RUN micromamba remove -y -n base opencv-python-headless
RUN /opt/conda/bin/python -m pip cache purge