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

# down a local imagej (Fiji) for consistent initialization
RUN /opt/conda/bin/wget -P /home/mambauser/ \
    https://downloads.imagej.net/fiji/latest/fiji-nojre.zip &> /dev/null \
    && /opt/conda/bin/unzip /home/mambauser/fiji-nojre.zip -d /home/mambauser/ > /dev/null \
    && rm /home/mambauser/fiji-nojre.zip

# add conda path to PATH to allow entrypoint overwrite
ENV PATH="${PATH}:/opt/conda/bin"
ENV JAVA_HOME="/opt/conda/lib/jvm"