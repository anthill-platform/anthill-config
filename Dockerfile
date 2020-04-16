FROM anthill-common
COPY . /config
WORKDIR /config
RUN mkdir -p /config/runtime
RUN python3 setup.py install
CMD ["python3", "-m", "anthill.config.server"]